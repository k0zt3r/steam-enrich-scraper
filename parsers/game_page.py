from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from models.game import SourceGame, Requirements


# Endpoint (relative to the site root) that serves the extra download
# mirrors which the page loads lazily via AJAX.
AJAX_ENDPOINT = "/ajax/downloads"


class GamePageParser:
    """
    Parse an example-store game detail page into a SourceGame.

    Shows a few common scraping techniques on one page:
      * pulling fields out with CSS selectors,
      * reading a value from an attribute (the Steam link),
      * turning a <br>-separated block into clean multi-line text,
      * fetching an extra block that is NOT in the static HTML but is
        loaded on demand through an AJAX call,
      * parsing a free-text system-requirements block into fields.
    """

    def parse(self, html: str, url: str) -> SourceGame:
        soup = BeautifulSoup(html, "lxml")

        title = self._text(soup.select_one(".game-title"))

        steam_url = ""
        link = soup.select_one("a.steam-link")
        if link and link.get("href"):
            steam_url = link["href"].strip()

        version = self._text(soup.select_one(".meta .version"))
        size = self._text(soup.select_one(".meta .size"))
        release_notes = self._block_text(soup.select_one(".release-notes"))

        links = self._static_links(soup, url) + self._ajax_links(soup, url)

        seen, download_links = set(), []
        for l in links:
            if l and l not in seen:
                seen.add(l)
                download_links.append(l)

        return SourceGame(
            title=title,
            url=url,
            steam_url=steam_url,
            version=version,
            size=size,
            release_notes=release_notes,
            download_links=download_links,
            requirements=self._requirements(soup),
        )

    # ---------------------------------------------------------------

    @staticmethod
    def _text(node) -> str:
        return node.get_text(strip=True) if node else ""

    @staticmethod
    def _block_text(node) -> str:
        if not node:
            return ""
        for br in node.find_all("br"):
            br.replace_with("\n")
        return node.get_text().strip()

    def _static_links(self, soup, url) -> list[str]:
        return [
            urljoin(url, a["href"].strip())
            for a in soup.select(".downloads a[href]:not(.ajax-trigger)")
        ]

    def _ajax_links(self, soup, url) -> list[str]:
        trigger = soup.select_one(".downloads a.ajax-trigger[data-block]")
        if not trigger:
            return []

        block = trigger.get("data-block", "")

        try:
            response = requests.post(
                urljoin(url, AJAX_ENDPOINT),
                data={"block": block},
                timeout=15,
            )
            response.raise_for_status()
            text = response.text
        except Exception as e:
            print("  [ajax] fetch failed:", repr(e))
            return []

        fragment = BeautifulSoup(text, "lxml")
        return [
            urljoin(url, a["href"].strip())
            for a in fragment.select("a[href]")
        ]

    def _requirements(self, soup) -> Requirements:
        node = soup.select_one(".requirements .min")
        req = Requirements()
        if not node:
            return req

        for br in node.find_all("br"):
            br.replace_with("\n")

        for raw in node.get_text().split("\n"):
            line = raw.strip()
            low = line.lower()
            if not line:
                continue
            if low.startswith("os"):
                req.os = line
            elif "processor" in low or low.startswith("cpu"):
                req.cpu = line
            elif "memory" in low or "ram" in low:
                req.ram = line
            elif "graphics" in low or "video" in low:
                req.gpu = line
            elif "storage" in low or "disk" in low:
                req.storage = line

        return req
