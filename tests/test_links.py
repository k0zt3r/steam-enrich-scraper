from services.links import filter_archive_links


def test_filter_keeps_allowed_source_and_torrent_drops_rest():
    links = [
        "https://files.example.com/d/a",           # разрешённый хост
        "https://store.example.com/dl/b",          # тот же домен, что у источника
        "magnet:?xt=urn:btih:deadbeef",            # magnet
        "https://store.example.com/game.torrent",  # прямой .torrent
        "https://random.test/c",                   # неизвестный -> выкидываем
    ]

    out = filter_archive_links(links, source_domain="store.example.com")

    assert "https://files.example.com/d/a" in out
    assert "https://store.example.com/dl/b" in out
    assert "magnet:?xt=urn:btih:deadbeef" in out
    assert "https://store.example.com/game.torrent" in out
    assert "https://random.test/c" not in out
