# steam-enrich-scraper

A small, well-factored **scrape → enrich → publish** pipeline for game data.

It parses a game page from an example catalog, enriches it with canonical
metadata from the **public Steam store API**, normalizes everything into one
record, and publishes that record through **either a REST API client or a
Selenium-automated web form** — whichever the destination offers.

The project is a techniques demo built around neutral, synthetic fixtures
(an "Example Store"); it does not target or include any real third-party
site. Point the publishers and the source at your own endpoints via `.env`.

## Why it exists / what it shows

- **Hand-written HTML parsers** (BeautifulSoup + CSS selectors): extracting
  fields, reading values from attributes, turning `<br>` blocks into clean
  text, and fetching a block that is loaded lazily over **AJAX** and is not
  in the static HTML.
- **Working with a REST API**: a Steam metadata client, plus a publisher with
  capped exponential-backoff retries, `Retry-After` handling, and a typed
  error hierarchy (auth / duplicate / generic).
- **Browser automation with Selenium** in two different roles:
  - *scraping* dynamic content that only appears after a click
    (`scrapers/dynamic_browser.py`),
  - *publishing* by filling a web form on a persistent logged-in profile,
    with a deliberate human-in-the-loop review before submit
    (`publishers/browser_publisher.py`).
- **Clean separation of concerns**: parsers → enrich → services
  (build/validate/map) → publishers, a tiny SQLite dedup store, and offline
  tests driven by fixtures.

## Architecture

```
  catalog page ──▶ parsers/ ──▶ SourceGame
                                   │
            Steam API ──▶ enrich/ ─┤
                                   ▼
                      services/builder + validator ──▶ GamePayload
                                   │
                 services/mapper (build request body)
                                   ▼
              publishers/  ──  ApiPublisher (REST)  │  BrowserPublisher (Selenium)
```

`scrapers/dynamic_browser.py` is an optional headless step for sources whose
download links appear only after a click.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# run the offline unit tests (no network, uses fixtures)
python -m pytest -q

# dry-run the full pipeline on the bundled example fixture
# (the Steam enrichment step reaches out to the public Steam API)
python main.py --demo
```

Process a real page and preview the REST body without sending anything:

```bash
python main.py "https://store.example.com/game/some-game" --publisher api
# add --submit to actually publish (requires PUBLISH_API_KEY in .env)
```

## Layout

```
parsers/        hand-written catalog + game-page parsers
enrich/         Steam store API client
scrapers/       Selenium headless scraper for dynamic content
publishers/     ApiPublisher (REST) and BrowserPublisher (Selenium form)
services/       builder, validator, link filter, request-body mapper
storage/        sqlite dedup store
models/         dataclasses (SourceGame, SteamData, GamePayload)
fixtures/       synthetic example-store HTML used by tests and --demo
tests/          offline tests
```

## Configuration

Copy `.env.example` to `.env`. Secrets (API keys) are read from the
environment only and are never hard-coded. See `config.py`.

## License

MIT — see [LICENSE](LICENSE).
