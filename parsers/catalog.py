from urllib.parse import urljoin

from bs4 import BeautifulSoup


class CatalogParser:
    """Parse a catalog listing page into (title, game_page_url) pairs."""

    def parse(self, html: str, base_url: str) -> list[tuple[str, str]]:
        soup = BeautifulSoup(html, "lxml")

        items = []
        for card in soup.select(".game-card a.game-link[href]"):
            title = card.get_text(strip=True)
            href = urljoin(base_url, card["href"].strip())
            items.append((title, href))

        return items
