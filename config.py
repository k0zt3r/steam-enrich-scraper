import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    DATABASE = os.getenv("DB_PATH", "pipeline.db")


class ApiConfig:
    """Settings for the REST publisher (publishers/api_publisher.py)."""

    # Base URL of the destination REST API. Point this at your own
    # service; the default is a placeholder that does not exist.
    API_URL = os.getenv("PUBLISH_API_URL", "https://api.example.com/v1")

    # API key is read from the environment only — never hard-code it.
    API_KEY = os.getenv("PUBLISH_API_KEY", "")

    # Largest .torrent we will download and base64-encode before sending.
    MAX_TORRENT_BYTES = int(os.getenv("MAX_TORRENT_BYTES", str(2 * 1024 * 1024)))

    # "url"    - send the .torrent URL, let the server fetch it
    # "base64" - download the .torrent ourselves and send it inline
    TORRENT_MODE = os.getenv("TORRENT_MODE", "url").lower()

    DEFAULT_VERSION = "v1.0.0"
    FALLBACK_INSTRUCTIONS = "1. Download\n2. Extract\n3. Run"


class BrowserConfig:
    """Settings for the Selenium form publisher (publishers/browser_publisher.py)."""

    # URL of the web form the browser publisher fills in.
    FORM_URL = os.getenv("FORM_URL", "https://demo.example.com/submit")

    # Optional path to a Chrome user-data dir with an existing logged-in
    # session, so the publisher does not have to log in every run.
    PROFILE_DIR = os.getenv("BROWSER_PROFILE", "")
