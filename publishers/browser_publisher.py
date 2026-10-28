import os
import platform
import re
import tempfile
import mimetypes

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from config import BrowserConfig
from models.game import GamePayload


FALLBACK_NOTES = "1. Скачать\n2. Распаковать\n3. Запустить"
DEFAULT_VERSION = "v1.0.0"


class BrowserPublisher:
    """
    Заполняет веб-форму через Selenium — для площадок без API. Использует
    постоянный профиль Chrome, чтобы переиспользовать уже залогиненную сессию,
    заполняет поля по атрибутам `data-field="..."`, загружает скриншоты и —
    намеренно — никогда не отправляет форму: карточку проверяет человек и
    жмёт «отправить» сам. Этот шаг «человек в контуре» — так задумано, а не
    ограничение.
    """

    def __init__(self):
        self.driver = None

    # ------------------------------------------------------------------
    # Жизненный цикл браузера
    # ------------------------------------------------------------------

    def _profile_dir(self) -> str:
        return BrowserConfig.PROFILE_DIR or os.path.join(
            os.path.expanduser("~"), "browser-profile"
        )

    def start(self):
        options = Options()
        profile_dir = self._profile_dir()

        if platform.system() == "Windows":
            binary = self._find_chrome_windows()
            if binary:
                options.binary_location = binary
            options.add_argument(f"--user-data-dir={profile_dir}")
            options.add_argument(r"--profile-directory=Default")
            self.driver = webdriver.Chrome(options=options)
        else:
            options.binary_location = "/usr/bin/chromium"
            options.add_argument(f"--user-data-dir={profile_dir}")
            options.add_argument(r"--profile-directory=Default")
            service = Service("/usr/bin/chromedriver")
            self.driver = webdriver.Chrome(service=service, options=options)

    @staticmethod
    def _find_chrome_windows():
        import shutil

        candidates = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ]
        for path in candidates:
            if os.path.isfile(path):
                return path

        found = shutil.which("chrome") or shutil.which("chrome.exe")
        if found:
            return found

        print("  ! chrome.exe не найден, пусть Selenium Manager ищет сам")
        return None

    def setup_profile(self):
        """Разовая настройка: открыть страницу входа, чтобы залогиниться руками
        один раз; дальше сессия берётся из профиля."""
        self.start()
        print("[Browser] Открываю сайт. Залогинься руками и закрой Chrome.")
        origin = re.match(r"https?://[^/]+", BrowserConfig.FORM_URL)
        self.driver.get(origin.group(0) if origin else BrowserConfig.FORM_URL)
        try:
            input("Нажми Enter здесь после того, как залогинишься...")
        except (EOFError, KeyboardInterrupt):
            pass
        self.close()

    def open(self):
        if self.driver is None:
            self.start()

        print("[Browser] Открываю форму...")
        self.driver.get(BrowserConfig.FORM_URL)

        try:
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[data-field="title"]')
                )
            )
        except Exception:
            print("[Browser] ФОРМА НЕ НАЙДЕНА на", self.driver.current_url)
            raise

        print("[Browser] Форма загружена")

    # ------------------------------------------------------------------
    # Поля
    # ------------------------------------------------------------------

    # ChromeDriver не умеет send_keys() символы вне Basic Multilingual Plane
    # (эмодзи и т.п.) и падает; вырезаем их, чтобы из-за одного символа не
    # потерять всё поле.
    _NON_BMP = re.compile("[\U00010000-\U0010FFFF]", flags=re.UNICODE)

    @classmethod
    def strip_non_bmp(cls, text: str) -> str:
        return cls._NON_BMP.sub("", text) if text else text

    def get_field(self, name: str, timeout: int = 15):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, f'[data-field="{name}"]')
            )
        )

    def fill_field(self, name: str, value: str) -> bool:
        # Сбой в одном поле не должен обрывать остальные — человек всё равно
        # проверяет карточку перед отправкой.
        try:
            field = self.get_field(name)
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", field
            )
            try:
                field.click()
            except Exception:
                pass
            try:
                field.clear()
            except Exception:
                pass

            field.send_keys(self.strip_non_bmp(value or ""))
            self.driver.execute_script(
                "arguments[0].dispatchEvent(new Event('input', {bubbles:true}));"
                "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));",
                field,
            )
            return True
        except Exception as e:
            print(f"  ! не удалось заполнить '{name}': {e!r}")
            return False

    def fill_category(self, category_id: int):
        field = self.get_field("category")
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", field
        )
        if field.tag_name.lower() == "select":
            Select(field).select_by_value(str(category_id))
        else:
            self.driver.execute_script(
                "arguments[0].value = arguments[1];"
                "arguments[0].dispatchEvent(new Event('input', {bubbles:true}));"
                "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));",
                field,
                str(category_id),
            )

    def fill_download_links(self, links) -> bool:
        if not links:
            print("  ! нет ссылок на скачивание")
            return False
        value = "\n".join(l.strip() for l in links if l and l.strip())
        ok = self.fill_field("downloads", value)
        print("  ✓ ссылки на скачивание" if ok else "  ! поле ссылок не найдено")
        return ok

    # ------------------------------------------------------------------
    # Скриншоты: каждый URL скачиваем во временный файл и прикрепляем к
    # соответствующему <input type=file data-screenshot="i">.
    # ------------------------------------------------------------------

    def get_shot_input(self, index: int, timeout: int = 15):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, f'input[data-screenshot="{index}"]')
            )
        )

    @staticmethod
    def download_screenshot(url: str, dest_dir: str, index: int) -> str:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "image/jpeg")
        ext = mimetypes.guess_extension(content_type.split(";")[0].strip()) or ".jpg"
        if ext == ".jpe":
            ext = ".jpg"
        path = os.path.join(dest_dir, f"shot_{index}{ext}")
        with open(path, "wb") as f:
            f.write(response.content)
        return path

    def fill_screenshots(self, urls):
        urls = [u for u in (urls or []) if u][:6]
        if not urls:
            print("  ! скриншотов для загрузки нет")
            return

        tmp_dir = tempfile.mkdtemp(prefix="shots_")
        for i, url in enumerate(urls, start=1):
            try:
                path = self.download_screenshot(url, tmp_dir, i)
            except Exception as e:
                print(f"  ! скриншот {i} не скачался:", repr(e))
                continue
            try:
                self.get_shot_input(i).send_keys(path)
                print(f"  ✓ скриншот {i} загружен")
            except Exception as e:
                print(f"  ! скриншот {i} не загрузился:", repr(e))

    # ------------------------------------------------------------------

    @staticmethod
    def normalize_notes(text: str) -> str:
        text = (text or "").strip()
        if not text:
            return FALLBACK_NOTES
        if len(text) <= 1500:
            return text
        return text[:1500].rsplit(" ", 1)[0] + "…"

    def fill(self, game: GamePayload, category_id: int | None = None):
        print("\n[Browser] Заполняю форму...")

        self.fill_field("title", game.title)
        self.fill_field("steam_url", game.steam_url)

        if category_id is not None:
            self.fill_category(category_id)
        else:
            print("  i категорию оставляю на ручной выбор")

        self.fill_field("version", getattr(game, "version", "") or DEFAULT_VERSION)
        self.fill_field("source_url", game.source_url)
        self.fill_field("release_notes", self.normalize_notes(game.release_notes))
        self.fill_download_links(game.download_links)
        if game.archive_size:
            self.fill_field("size", game.archive_size)
        self.fill_screenshots(getattr(game, "screenshots", []))

        self.driver.execute_script("window.scrollTo({top: 0});")
        print("\n" + "=" * 60)
        print("ФОРМА ГОТОВА (заполнена, НЕ отправлена — проверь и отправь руками)")
        print("=" * 60 + "\n")

    # ------------------------------------------------------------------

    def open_and_fill(self, game: GamePayload, category_id: int | None = None):
        self.start()
        self.open()
        self.fill(game, category_id)

    def is_alive(self) -> bool:
        if self.driver is None:
            return False
        try:
            self.driver.current_url
            return True
        except Exception:
            return False

    def close(self):
        if self.driver is None:
            return
        if not self.is_alive():
            self.driver = None
            return
        try:
            self.driver.quit()
        except (Exception, KeyboardInterrupt) as e:
            print("[Browser] ошибка при закрытии (игнорирую):", repr(e))
        self.driver = None
