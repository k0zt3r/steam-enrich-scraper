import re

import requests
from rapidfuzz import fuzz
from bs4 import BeautifulSoup

from models.game import SteamData, Requirements


STEAM_API = "https://store.steampowered.com/api/appdetails"
STEAM_SEARCH = "https://store.steampowered.com/search/"


class SteamClient:
    """Тонкий клиент к публичным эндпоинтам магазина Steam."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})

    def extract_appid(self, url: str) -> int:
        match = re.search(r"/app/(\d+)", url)
        return int(match.group(1)) if match else 0

    def get_game(self, steam_url: str) -> SteamData:
        appid = self.extract_appid(steam_url)
        if not appid:
            return SteamData()

        try:
            response = self.session.get(
                STEAM_API,
                params={"appids": appid, "l": "russian", "cc": "ru"},
                timeout=20,
            )
            data = response.json()
        except Exception:
            return SteamData(appid=appid)

        game = data.get(str(appid), {}).get("data", {})
        if not game:
            return SteamData(appid=appid)

        return SteamData(
            appid=appid,
            name=game.get("name", ""),
            description=game.get("about_the_game", ""),
            developer=", ".join(game.get("developers", [])),
            publisher=", ".join(game.get("publishers", [])),
            release_date=game.get("release_date", {}).get("date", ""),
            poster=game.get("header_image", ""),
            trailer=self.get_trailer(game),
            genres=game.get("genres", []),
            screenshots=self.get_screenshots(game),
            requirements=self.parse_requirements(game.get("pc_requirements", {})),
        )

    def parse_requirements(self, data) -> Requirements:
        if not isinstance(data, dict):
            return Requirements()

        minimum = BeautifulSoup(
            data.get("minimum", ""), "html.parser"
        ).get_text("\n")

        req = Requirements()
        # Ключевые слова и на русском, и на английском — Steam отдаёт метки
        # в зависимости от локали.
        for raw in minimum.split("\n"):
            line = raw.strip()
            if not line:
                continue
            low = line.lower()
            if "ос" in low or "os" in low or "операцион" in low or "windows" in low:
                req.os += line + "\n"
            elif "процессор" in low or "processor" in low or "cpu" in low:
                req.cpu += line + "\n"
            elif "память" in low or "озу" in low or "memory" in low or "ram" in low:
                req.ram += line + "\n"
            elif "видео" in low or "graphics" in low:
                req.gpu += line + "\n"
            elif "накопит" in low or "место" in low or "диск" in low or "storage" in low or "disk" in low:
                req.storage += line + "\n"

        return req

    def get_screenshots(self, game, limit: int = 6) -> list[str]:
        urls = []
        for shot in game.get("screenshots", []):
            url = shot.get("path_full") or shot.get("path_thumbnail") or ""
            if url:
                urls.append(url)
            if len(urls) >= limit:
                break
        return urls

    def get_trailer(self, game):
        movies = game.get("movies", [])
        if not movies:
            return ""
        return movies[0].get("mp4", {}).get("max", "")

    # ------------------------------------------------------------------
    # Нечёткое сопоставление названий: поиск Steam возвращает смесь
    # релевантности, популярности и цены, так что верхняя строка не всегда
    # нужная игра. Переупорядочиваем кандидатов по похожести на искомое.
    # ------------------------------------------------------------------

    _STOPWORDS = {
        "the", "a", "an", "of", "in", "on", "at", "to",
        "from", "and", "or", "for", "with", "s",
    }

    _EXTRA_WORD_PENALTY = 8
    SEARCH_MATCH_THRESHOLD = 58

    @classmethod
    def _significant_words(cls, title: str) -> set:
        words = re.findall(r"[a-zа-я0-9]+", title.lower())
        return {w for w in words if w not in cls._STOPWORDS}

    @classmethod
    def _match_score(cls, source_title: str, candidate_title: str) -> float:
        base = fuzz.ratio(
            source_title.lower().strip(),
            candidate_title.lower().strip(),
        )
        source_words = cls._significant_words(source_title)
        candidate_words = cls._significant_words(candidate_title)
        extra = (source_words | candidate_words) - (source_words & candidate_words)
        penalty = len(extra) * cls._EXTRA_WORD_PENALTY
        return max(0.0, base - penalty)

    @classmethod
    def _required_threshold(cls, source_title: str) -> float:
        """Чем короче/типовее название, тем выше планка — иначе ложные совпадения."""
        n = len(cls._significant_words(source_title))
        if n <= 2:
            return 90
        if n == 3:
            return 78
        return cls.SEARCH_MATCH_THRESHOLD

    def search(self, title: str):
        response = self.session.get(
            STEAM_SEARCH,
            params={"term": title, "category1": 998},
            timeout=20,
        )
        soup = BeautifulSoup(response.text, "lxml")

        results = []
        for item in soup.select(".search_result_row"):
            name = item.select_one(".title")
            if not name:
                continue
            result_title = name.text.strip()
            score = self._match_score(title, result_title)
            print(f"  [Steam search] {result_title!r} -> {score:.1f}%")
            results.append(
                {"title": result_title, "url": item.get("href", ""), "score": score}
            )

        results.sort(key=lambda r: r["score"], reverse=True)
        threshold = self._required_threshold(title)
        matched = [r for r in results if r["score"] >= threshold]

        if not matched and results:
            print(
                f"  [Steam search] лучший кандидат {results[0]['title']!r} "
                f"({results[0]['score']:.1f}%) ниже порога ({threshold}%), "
                f"считаю, что не найдено"
            )

        return matched
