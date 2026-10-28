import platform
import subprocess

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


class DynamicBrowser:
    """
    Одноразовый headless-Chrome для страниц, где нужные данные подгружаются
    по клику через JS/AJAX и в статичном HTML (который отдаёт requests) их
    попросту нет.

    В отличие от браузерного паблишера, тут нет постоянного профиля: логин не
    нужен, каждый вызов поднимает и гасит свой процесс Chrome. Фильтрация
    ссылок здесь НЕ делается — она в одном месте (services/links.py) и
    вызывается в GameBuilder.build(); здесь только собираем то, что страница
    показала после клика.
    """

    # Видимая подпись сворачиваемого блока с дополнительными ссылками.
    TRIGGER_LABEL = "Показать ещё зеркала"

    def get_dynamic_links(self, url: str, timeout: int = 20) -> list[str]:
        driver = self._start()
        result = []

        try:
            driver.get(url)

            triggers = self._find_triggers(driver)
            if not triggers:
                print("  ! сворачиваемых блоков со ссылками на странице нет")

            for trigger in triggers:
                for link in self._open_and_collect(driver, trigger, timeout):
                    if link not in result:
                        result.append(link)
        finally:
            try:
                driver.quit()
            except Exception:
                pass

        return result

    def _start(self):
        options = Options()

        # Headless, без постоянного профиля — это разовый «разведчик» страницы.
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1280,1600")

        # Глушим шумные фоновые логи Chrome (GCM/sync/USB...), не связанные со
        # скрапингом, чтобы они не путались с реальными ошибками.
        options.add_argument("--log-level=3")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-sync")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-client-side-phishing-detection")
        options.add_argument("--disable-component-update")
        options.add_argument("--disable-domain-reliability")
        options.add_argument("--disable-notifications")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

        if platform.system() == "Windows":
            service = Service(log_output=subprocess.DEVNULL)
            return webdriver.Chrome(service=service, options=options)

        options.binary_location = "/usr/bin/chromium"
        service = Service("/usr/bin/chromedriver", log_output=subprocess.DEVNULL)
        return webdriver.Chrome(service=service, options=options)

    def _find_triggers(self, driver):
        # У игры может быть несколько вариантов раздачи, у каждого — свой
        # сворачиваемый блок. Собираем все, а не только первый.
        candidates = driver.find_elements(
            By.CSS_SELECTOR, ".variants .list_item.ajax-trigger"
        )

        matched = []
        for el in candidates:
            try:
                text = el.text
            except Exception:
                continue
            if self.TRIGGER_LABEL in text:
                matched.append(el)
        return matched

    def _open_and_collect(self, driver, trigger, timeout):
        try:
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", trigger
            )
            driver.execute_script("arguments[0].click();", trigger)
        except Exception:
            return []

        # .ajax-content — соседний элемент, куда сайт дозагружает ссылки после
        # клика по .list_item.ajax-trigger, внутри того же .ajax-block.
        try:
            content = trigger.find_element(
                By.XPATH,
                "./ancestor::*[contains(@class,'ajax-block')]"
                "//*[contains(@class,'ajax-content')]",
            )
        except Exception:
            return []

        try:
            WebDriverWait(driver, timeout).until(
                lambda d: len(content.find_elements(By.TAG_NAME, "a")) > 0
            )
        except Exception:
            # Ссылки у этого варианта так и не появились — не фатально, пропускаем.
            return []

        links = []
        for a in content.find_elements(By.TAG_NAME, "a"):
            href = a.get_attribute("href")
            if href and href not in links:
                links.append(href)
        return links
