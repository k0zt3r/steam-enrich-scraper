"""
Offline test for GamePageParser against saved example-store fixtures.
No network: requests.post is monkeypatched to serve the AJAX fixture.
"""

from pathlib import Path

import parsers.game_page as gp_module
from parsers.game_page import GamePageParser


FIXTURES = Path(__file__).parent.parent / "fixtures" / "example_store"
URL = "https://store.example.com/game/nebula-drift"


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


def fake_post(endpoint, data=None, headers=None, timeout=None):
    block = (data or {}).get("block", "")
    fixture = FIXTURES / f"ajax_{block}.html"
    text = fixture.read_text(encoding="utf-8") if fixture.exists() else ""
    return FakeResponse(text)


def test_game_page_parses_offline(monkeypatch):
    monkeypatch.setattr(gp_module.requests, "post", fake_post)

    html = (FIXTURES / "game.html").read_text(encoding="utf-8")
    game = GamePageParser().parse(html, URL)

    assert game.title == "Nebula Drift"
    assert "app/440" in game.steam_url
    assert game.version == "v1.4.2"
    assert game.size == "8.3 GB"

    # <br>-separated block became clean multi-line text
    assert "Run Game.exe" in game.release_notes
    assert game.release_notes.splitlines()[0] == "Edition: Portable"

    # static link from the page + two more pulled via the AJAX call
    assert "https://files.example.com/d/abc123" in game.download_links
    assert "https://cdn.example.com/f/xyz789" in game.download_links
    assert "https://files.example.com/d/def456" in game.download_links

    # the ajax-trigger anchor itself must not leak in as a link
    assert all("#" not in l for l in game.download_links)

    # free-text requirements block split into fields
    assert game.requirements.gpu.startswith("Graphics")
    assert "8 GB RAM" in game.requirements.ram
