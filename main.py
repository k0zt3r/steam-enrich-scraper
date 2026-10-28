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
    print("[1] parse source page")
    if html is None:
        html = load_page(url)
    source = GamePageParser().parse(html, url)
    print("    found:", source.title)

    print("[2] enrich with Steam")
    steam_client = SteamClient()
    if not source.steam_url:
        results = steam_client.search(source.title)
        if not results:
            print("    Steam game not found - stopping")
            return
        source.steam_url = results[0]["url"]

    steam = steam_client.get_game(source.steam_url)
    if not steam.name:
        print("    Steam lookup failed (no name) - stopping")
        return
    print("    steam:", steam.name)

    print("[3] build + validate payload")
    payload = GameBuilder().build(source, steam)
    errors = validate(payload)
    if errors:
        print("    invalid:", ", ".join(errors))
        return
    print("    ok")

    body = build_game_body(payload)

    if publisher == "api":
        if not has_source(body):
            print("    no usable download source - skipping")
            return
        if not submit:
            print("[4] DRY-RUN (api). Request body:")
            print(json.dumps(body, ensure_ascii=False, indent=2))
            return
        from publishers.api_publisher import ApiPublisher

        print("[4] POST /games")
        print(ApiPublisher().create_game(body))

    elif publisher == "browser":
        if not submit:
            print("[4] DRY-RUN (browser). Would open the form and fill:", payload.title)
            return
        from publishers.browser_publisher import BrowserPublisher

        BrowserPublisher().open_and_fill(payload)

    else:  # dry-run
        print("[4] DRY-RUN. Normalized publish body:")
        print(json.dumps(body, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser(
        description="Scrape a game page, enrich it via the Steam API, "
        "and publish it through a REST API or a Selenium-automated web form."
    )
    ap.add_argument("url", nargs="?", help="game page URL to process")
    ap.add_argument(
        "--demo",
        action="store_true",
        help="run offline on the bundled example fixture (Steam step still needs network)",
    )
    ap.add_argument(
        "--publisher",
        choices=["dry-run", "api", "browser"],
        default="dry-run",
        help="where to publish (default: dry-run, prints the payload)",
    )
    ap.add_argument(
        "--submit",
        action="store_true",
        help="actually publish; without it everything is a dry run",
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
        ap.error("provide a game page URL, or use --demo")

    run(args.url, publisher=args.publisher, submit=args.submit)


if __name__ == "__main__":
    main()
