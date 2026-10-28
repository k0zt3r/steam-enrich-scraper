from services.builder import GameBuilder
from models.game import SourceGame, SteamData


def test_builder_prefers_steam_title_and_filters_links():
    source = SourceGame(
        title="сырое название со страницы",
        url="https://store.example.com/game/nebula-drift",
        steam_url="https://store.steampowered.com/app/440/",
        release_notes="1. Распаковать\n2. Запустить",
        size="10 ГБ",
        download_links=[
            "https://files.example.com/d/ok",   # разрешённый хост -> оставляем
            "https://unknown.test/bad",          # чужой хост -> выкидываем
        ],
    )
    steam = SteamData(appid=440, name="Nebula Drift", developer="Acme Studio")

    payload = GameBuilder().build(source, steam)

    assert payload.title == "Nebula Drift"          # каноническое название из Steam
    assert payload.steam_appid == 440
    assert payload.developer == "Acme Studio"
    assert "https://files.example.com/d/ok" in payload.download_links
    assert "https://unknown.test/bad" not in payload.download_links
