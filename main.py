import argparse
import json
from pathlib import Path

import requests

from parsers.game_page import GamePageParser
from enrich.steam import SteamClient
from services.builder import GameBuilder
from services.validator import validate
from services.mapper import build_game_body, has_source


UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "Chrome/139 Safari/537.36"
)

DEMO_FIXTURE = Path(__file__).parent / "fixtures" / "example_store" / "game.html"
DEMO_URL = "https://store.example.com/game/nebula-drift"


def load_page(url: str) -> str:
    session = requests.Session()
    session.headers.update({"User-Agent": UA})
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def run(url, html=None, publisher="dry-run", submit=False):
    print("[1] парсинг страницы-источника")
    if html is None:
        html = load_page(url)
    source = GamePageParser().parse(html, url)
    print("    найдено:", source.title)

    print("[2] обогащение данными Steam")
    steam_client = SteamClient()
    if not source.steam_url:
        results = steam_client.search(source.title)
        if not results:
            print("    игра в Steam не найдена — останавливаюсь")
            return
        source.steam_url = results[0]["url"]

    steam = steam_client.get_game(source.steam_url)
    if not steam.name:
        print("    не удалось получить данные Steam (нет названия) — останавливаюсь")
        return
    print("    steam:", steam.name)

    print("[3] сборка и валидация записи")
    payload = GameBuilder().build(source, steam)
    errors = validate(payload)
    if errors:
        print("    невалидно:", ", ".join(errors))
        return
    print("    ок")

    body = build_game_body(payload)

    if publisher == "api":
        if not has_source(body):
            print("    нет пригодного источника раздачи — пропускаю")
            return
        if not submit:
            print("[4] DRY-RUN (api). Тело запроса:")
            print(json.dumps(body, ensure_ascii=False, indent=2))
            return
        from publishers.api_publisher import ApiPublisher

        print("[4] POST /games")
        print(ApiPublisher().create_game(body))

    elif publisher == "browser":
        if not submit:
            print("[4] DRY-RUN (browser). Открыл бы форму и заполнил:", payload.title)
            return
        from publishers.browser_publisher import BrowserPublisher

        BrowserPublisher().open_and_fill(payload)

    else:  # dry-run
        print("[4] DRY-RUN. Нормализованное тело публикации:")
        print(json.dumps(body, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser(
        description="Спарсить страницу игры, обогатить её данными Steam API и "
        "опубликовать через REST API или Selenium-автозаполнение веб-формы."
    )
    ap.add_argument("url", nargs="?", help="URL страницы игры для обработки")
    ap.add_argument(
        "--demo",
        action="store_true",
        help="прогон офлайн на вложенной фикстуре (шаг Steam всё равно ходит в сеть)",
    )
    ap.add_argument(
        "--publisher",
        choices=["dry-run", "api", "browser"],
        default="dry-run",
        help="куда публиковать (по умолчанию dry-run — печатает тело)",
    )
    ap.add_argument(
        "--submit",
        action="store_true",
        help="реально опубликовать; без флага всё это dry-run",
    )
    args = ap.parse_args()

    if args.demo:
        run(
            DEMO_URL,
            html=DEMO_FIXTURE.read_text(encoding="utf-8"),
            publisher=args.publisher,
            submit=False,
        )
        return

    if not args.url:
        ap.error("укажи URL страницы игры или используй --demo")

    run(args.url, publisher=args.publisher, submit=args.submit)


if __name__ == "__main__":
    main()
