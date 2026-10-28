from urllib.parse import urljoin

from bs4 import BeautifulSoup


class CatalogParser:
    """Парсит страницу-список каталога в пары (название, ссылка на страницу игры)."""

    def parse(self, html: str, base_url: str) -> list[tuple[str, str]]:
        soup = BeautifulSoup(html, "lxml")

        items = []
        for card in soup.select(".game-card a.game-link[href]"):
            title = card.get_text(strip=True)
            href = urljoin(base_url, card["href"].strip())
            items.append((title, href))

        return items
