import platform
import subprocess

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


class DynamicBrowser:
    """
    A throwaway headless Chrome for pages whose data is loaded with
    JS/AJAX on click and is therefore absent from the static HTML you
    get with `requests`.

    Unlike the browser publisher, this one keeps no persistent profile:
    no login is needed, each call spins up and tears down its own
    Chrome process. Link filtering is intentionally NOT done here - that
    lives in one place (services/links.py) and runs in GameBuilder.build();
    here we just collect whatever the page reveals after the click.
    """

    # Visible label of the collapsible block that holds the extra links.
    TRIGGER_LABEL = "More mirrors"

    def get_dynamic_links(self, url: str, timeout: int = 20) -> list[str]:
        driver = self._start()
        result = []

        try:
            driver.get(url)

            triggers = self._find_triggers(driver)
            if not triggers:
                print("  ! no collapsible link blocks found on the page")

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

        # Headless, no persistent profile - this is a one-shot page scout.
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1280,1600")

        # Quiet Chrome's noisy background-service logs (GCM/sync/USB...),
        # which are unrelated to scraping and only confuse real errors.
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
        # A game may have several download variants, each with its own
        # collapsible block - collect them all, not just the first.
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

        # .ajax-content is the sibling the site fills with links after the
        # click on .list_item.ajax-trigger, inside the same .ajax-block.
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
            # Links never showed up for this variant - not fatal, skip it.
            return []

        links = []
        for a in content.find_elements(By.TAG_NAME, "a"):
            href = a.get_attribute("href")
            if href and href not in links:
                links.append(href)
        return links
