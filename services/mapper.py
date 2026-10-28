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
    """Download a .torrent and return base64, or '' on failure."""

    try:
        r = requests.get(
            url,
            headers={"User-Agent": UA, "Referer": referer},
            timeout=30,
        )
        r.raise_for_status()
    except Exception as e:
        print("  [torrent] download failed:", repr(e))
        return ""

    data = r.content

    # bencode dict: starts with 'd' and contains an info section
    if not data.startswith(b"d") or b"4:info" not in data:
        print("  [torrent] response is not a .torrent, skipping")
        return ""

    if len(data) > ApiConfig.MAX_TORRENT_BYTES:
        print("  [torrent] file too large, skipping")
        return ""

    return base64.b64encode(data).decode("ascii")


def has_source(body: dict) -> bool:
    """True if the body carries at least one way to obtain the download."""

    return bool(
        body.get("magnetUri")
        or body.get("torrentUrl")
        or body.get("torrentBase64")
        or body.get("downloadLinks")
    )


def make_fingerprint(version: str, links) -> str:
    """Fingerprint of a release: version + its download links, sorted."""

    return "|".join([version or ""] + sorted(set(links or [])))


def pick_torrent_links(links, source_url: str) -> list:
    """magnet / .torrent / links hosted on the source site itself."""

    return [
        l
        for l in (links or [])
        if l.startswith("magnet:")
        or urlparse(l).path.lower().endswith(".torrent")
        or _same_host(l, source_url)
    ]


def build_game_body(payload: GamePayload, force_version: bool = False) -> dict:
    """
    GamePayload -> JSON body for POST /games.

    force_version=True adds "force": true so the server applies the update
    without comparing versions (an intentional rollback).
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

    # By default we send the server the .torrent URL (torrentUrl) and let it
    # fetch, validate and store the file. TORRENT_MODE=base64 is the older
    # behaviour (download the .torrent ourselves and send it inline), needed
    # only when the server cannot fetch the link itself.
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

    # Could not hand over a .torrent (base64 mode: too large or failed to
    # download) - fall back to passing the direct .torrent link as a plain
    # download link instead of losing the release.
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
