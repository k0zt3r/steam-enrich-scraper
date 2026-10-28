import base64
from urllib.parse import urlparse

import requests

from config import ApiConfig
from models.game import GamePayload


UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "Chrome/139 Safari/537.36"
)


def _same_host(link: str, source_url: str) -> bool:
    a = urlparse(link).netloc.lower().removeprefix("www.")
    b = urlparse(source_url).netloc.lower().removeprefix("www.")
    return bool(a) and a == b


def fetch_torrent_b64(url: str, referer: str = "") -> str:
    """Скачивает .torrent и возвращает base64 или '' при неудаче."""

    try:
        r = requests.get(
            url,
            headers={"User-Agent": UA, "Referer": referer},
            timeout=30,
        )
        r.raise_for_status()
    except Exception as e:
        print("  [torrent] не удалось скачать:", repr(e))
        return ""

    data = r.content

    # bencode-словарь: начинается с 'd' и содержит секцию info
    if not data.startswith(b"d") or b"4:info" not in data:
        print("  [torrent] ответ не похож на .torrent, пропускаю")
        return ""

    if len(data) > ApiConfig.MAX_TORRENT_BYTES:
        print("  [torrent] файл слишком большой, пропускаю")
        return ""

    return base64.b64encode(data).decode("ascii")


def has_source(body: dict) -> bool:
    """True, если в теле есть хотя бы один способ получить раздачу."""

    return bool(
        body.get("magnetUri")
        or body.get("torrentUrl")
        or body.get("torrentBase64")
        or body.get("downloadLinks")
    )


def make_fingerprint(version: str, links) -> str:
    """Отпечаток релиза: версия + его ссылки на скачивание, отсортированные."""

    return "|".join([version or ""] + sorted(set(links or [])))


def pick_torrent_links(links, source_url: str) -> list:
    """magnet / .torrent / ссылки с самого сайта-источника."""

    return [
        l
        for l in (links or [])
        if l.startswith("magnet:")
        or urlparse(l).path.lower().endswith(".torrent")
        or _same_host(l, source_url)
    ]


def build_game_body(payload: GamePayload, force_version: bool = False) -> dict:
    """
    GamePayload -> JSON-тело для POST /games.

    force_version=True добавляет "force": true, и сервер применяет обновление
    без сравнения версий (осознанный откат).
    """

    magnets = [l for l in payload.download_links if l.startswith("magnet:")]
    rest = [l for l in payload.download_links if not l.startswith("magnet:")]

    torrent_links = [
        l
        for l in rest
        if _same_host(l, payload.source_url)
        or urlparse(l).path.lower().endswith(".torrent")
    ]
    host_links = [l for l in rest if l not in torrent_links]

    # По умолчанию отдаём серверу ССЫЛКУ на .torrent (torrentUrl): он сам
    # скачает, проверит и сохранит файл. TORRENT_MODE=base64 — старое
    # поведение (качаем .torrent сами и шлём инлайн), нужно только если
    # сервер не может скачать ссылку самостоятельно.
    torrent_url = ""
    torrent_b64 = ""

    if not magnets and torrent_links:
        if ApiConfig.TORRENT_MODE == "base64":
            for link in torrent_links:
                torrent_b64 = fetch_torrent_b64(link, referer=payload.source_url)
                if torrent_b64:
                    break
        else:
            torrent_url = torrent_links[0]

    # Не удалось отдать .torrent (base64-режим: слишком большой или не
    # скачался) — отдаём прямую ссылку на .torrent как обычную ссылку на
    # скачивание, а не теряем раздачу.
    if not magnets and not torrent_b64 and not torrent_url:
        host_links = host_links + [
            l
            for l in torrent_links
            if urlparse(l).path.lower().endswith(".torrent")
            and l not in host_links
        ]

    body = {
        "title": payload.title,
        "version": payload.version or ApiConfig.DEFAULT_VERSION,
        "installInstructions": (
            payload.release_notes.strip()[:1500]
            or ApiConfig.FALLBACK_INSTRUCTIONS
        ),
        "sourceUrl": payload.source_url,
    }

    if payload.is_adult:
        body["isAdult"] = "on"

    if payload.archive_size:
        body["archiveSize"] = payload.archive_size

    if payload.steam_url:
        body["steamUrl"] = payload.steam_url
    else:
        body["description"] = payload.description

    if magnets:
        body["magnetUri"] = magnets[0]
    elif torrent_url:
        body["torrentUrl"] = torrent_url
    elif torrent_b64:
        body["torrentBase64"] = torrent_b64

    if host_links:
        body["downloadLinks"] = host_links

    if payload.screenshots:
        body["screenshotUrls"] = payload.screenshots

    if force_version:
        body["force"] = True

    return body
