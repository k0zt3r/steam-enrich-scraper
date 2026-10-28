import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    DATABASE = os.getenv("DB_PATH", "pipeline.db")


class ApiConfig:
    """Настройки REST-паблишера (publishers/api_publisher.py)."""

    # Базовый URL целевого REST API. Укажи свой; по умолчанию стоит
    # заглушка, которой не существует.
    API_URL = os.getenv("PUBLISH_API_URL", "https://api.example.com/v1")

    # Ключ читается только из окружения — никогда не хардкодим его.
    API_KEY = os.getenv("PUBLISH_API_KEY", "")

    # Максимальный размер .torrent, который качаем и кодируем в base64.
    MAX_TORRENT_BYTES = int(os.getenv("MAX_TORRENT_BYTES", str(2 * 1024 * 1024)))

    # "url"    - отдаём серверу ссылку на .torrent, он качает сам
    # "base64" - качаем .torrent сами и отправляем инлайн
    TORRENT_MODE = os.getenv("TORRENT_MODE", "url").lower()

    DEFAULT_VERSION = "v1.0.0"
    FALLBACK_INSTRUCTIONS = "1. Скачать\n2. Распаковать\n3. Запустить"


class BrowserConfig:
    """Настройки Selenium-паблишера (publishers/browser_publisher.py)."""

    # URL веб-формы, которую заполняет браузерный паблишер.
    FORM_URL = os.getenv("FORM_URL", "https://demo.example.com/submit")

    # Необязательный путь к профилю Chrome с уже залогиненной сессией,
    # чтобы не входить на сайт при каждом запуске.
    PROFILE_DIR = os.getenv("BROWSER_PROFILE", "")
