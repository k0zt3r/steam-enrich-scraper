"""
Офлайн-тест GamePageParser на сохранённых фикстурах примера-магазина.
Без сети: requests.post подменяется и отдаёт AJAX-фикстуру.
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
    assert game.size == "8.3 ГБ"

    # блок с <br> превратился в чистый многострочный текст
    assert "Запустите Game.exe" in game.release_notes
    assert game.release_notes.splitlines()[0] == "Издание: Portable"

    # статичная ссылка со страницы + две, добранные через AJAX
    assert "https://files.example.com/d/abc123" in game.download_links
    assert "https://cdn.example.com/f/xyz789" in game.download_links
    assert "https://files.example.com/d/def456" in game.download_links

    # сам якорь ajax-trigger не должен просочиться как ссылка
    assert all("#" not in l for l in game.download_links)

    # свободный текст требований разобран на поля
    assert game.requirements.gpu.startswith("Видеокарта")
    assert "8 ГБ" in game.requirements.ram
