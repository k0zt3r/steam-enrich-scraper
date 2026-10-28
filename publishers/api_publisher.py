import time

import requests

from config import ApiConfig


class PublishError(Exception):
    """Ошибка API. status — HTTP-код, code — код из тела ответа."""

    def __init__(self, status, code="", message="", details=None):
        super().__init__(f"{status} {code} {message}".strip())
        self.status = status
        self.code = code
        self.message = message
        self.details = details


class DuplicateError(PublishError):
    """409 — запись уже есть на сервере."""


class AuthError(PublishError):
    """401/403 — ключ неверный или отозван; повторять бессмысленно."""


class ApiPublisher:
    """
    REST-клиент к целевому API.

    Показывает то, что полезно в любом реальном API-клиенте: ключ из конфига
    (не хардкод), ретраи с ограниченным экспоненциальным backoff на сетевые
    ошибки / 429 / 5xx, учёт Retry-After и типизированную иерархию ошибок —
    чтобы вызывающий код различал auth / duplicate / общую ошибку.
    """

    def __init__(self, api_key=None, base_url=None, max_retries=3):
        self.api_key = api_key or ApiConfig.API_KEY
        self.base_url = (base_url or ApiConfig.API_URL).rstrip("/")
        self.max_retries = max_retries

        if not self.api_key:
            raise RuntimeError(
                "PUBLISH_API_KEY не задан (положи его в окружение / .env)"
            )

        self.session = requests.Session()
        self.session.headers.update(
            {"x-api-key": self.api_key, "Content-Type": "application/json"}
        )

    # ------------------------------------------------------------------

    def ping(self):
        return self._request("GET", "/ping")

    def create_game(self, body: dict):
        return self._request("POST", "/games", body)

    # ------------------------------------------------------------------

    def _request(self, method, path, body=None):
        url = self.base_url + path

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(
                    method, url, json=body, timeout=60
                )
            except (requests.ConnectionError, requests.Timeout) as e:
                if attempt < self.max_retries:
                    wait = 2 ** (attempt + 1)
                    print(f"  [API] сеть: {e!r}, повтор через {wait}s")
                    time.sleep(wait)
                    continue
                raise

            if response.status_code == 429 and attempt < self.max_retries:
                wait = self._retry_after(response)
                print(f"  [API] 429, жду {wait}s")
                time.sleep(wait)
                continue

            if response.status_code >= 500 and attempt < self.max_retries:
                wait = 2 ** (attempt + 1)
                print(f"  [API] {response.status_code}, повтор через {wait}s")
                time.sleep(wait)
                continue

            return self._handle(response)

        raise PublishError(0, "RETRIES_EXHAUSTED")

    @staticmethod
    def _retry_after(response):
        try:
            return max(1, min(int(response.headers.get("Retry-After", "")), 120))
        except ValueError:
            return 30

    @staticmethod
    def _handle(response):
        try:
            data = response.json()
        except ValueError:
            data = {}

        if response.ok:
            return data

        if not isinstance(data, dict):
            data = {"message": str(data)}

        err = data.get("error", "")
        if isinstance(err, dict):
            code = err.get("code", "")
            message = err.get("message", "")
        else:
            code = data.get("code") or err or ""
            message = data.get("message", "") or response.text[:300]

        details = (
            data.get("fieldErrors")
            or data.get("details")
            or data.get("errors")
        )

        if response.status_code == 409:
            cls = DuplicateError
        elif response.status_code in (401, 403):
            cls = AuthError
        else:
            cls = PublishError

        raise cls(response.status_code, code, message, details)
