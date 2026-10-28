from pathlib import Path

from parsers.catalog import CatalogParser


FIXTURES = Path(__file__).parent.parent / "fixtures" / "example_store"


def test_catalog_lists_games():
    html = (FIXTURES / "catalog.html").read_text(encoding="utf-8")
    items = CatalogParser().parse(html, "https://store.example.com/")

    titles = [t for t, _ in items]
    urls = [u for _, u in items]

    assert "Nebula Drift" in titles
    assert len(items) == 3
    assert "https://store.example.com/game/stellar-rally" in urls
