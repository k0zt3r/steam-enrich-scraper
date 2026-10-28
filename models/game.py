from dataclasses import dataclass, field
from typing import Any


@dataclass
class Requirements:
    os: str = ""
    cpu: str = ""
    ram: str = ""
    gpu: str = ""
    storage: str = ""


@dataclass
class SteamData:
    """Метаданные, полученные из публичного API магазина Steam."""

    appid: int = 0
    name: str = ""
    description: str = ""
    developer: str = ""
    publisher: str = ""
    release_date: str = ""
    poster: str = ""
    trailer: str = ""
    genres: list[Any] = field(default_factory=list)
    screenshots: list[str] = field(default_factory=list)
    requirements: Requirements = field(default_factory=Requirements)


@dataclass
class SourceGame:
    """То, что парсер извлекает со страницы одной игры в каталоге."""

    title: str
    url: str
    steam_url: str = ""
    poster: str = ""
    description: str = ""
    release_notes: str = ""
    version: str = ""
    size: str = ""
    is_adult: bool = False
    download_links: list[str] = field(default_factory=list)
    requirements: Requirements = field(default_factory=Requirements)


@dataclass
class GamePayload:
    """Нормализованная запись, готовая к публикации (через API или веб-форму)."""

    title: str
    steam_url: str
    steam_appid: int
    source_url: str
    download_links: list[str]
    archive_size: str
    description: str = ""
    release_notes: str = ""
    version: str = ""
    developer: str = ""
    publisher: str = ""
    poster: str = ""
    trailer: str = ""
    screenshots: list[str] = field(default_factory=list)
    requirements: Requirements = field(default_factory=Requirements)
    tags: list[str] = field(default_factory=list)
    is_adult: bool = False
