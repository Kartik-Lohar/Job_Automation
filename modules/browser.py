"""
Browser Utilities — Stealth Edition
====================================
Chrome WebDriver setup using ``undetected-chromedriver`` for anti-detection,
plus shared helper functions for safe, human-like interactions.
"""

from __future__ import annotations

import random
import time

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)

# ---------------------------------------------------------------------------
# User-Agent rotation pool  (UC patches the UA automatically, but these
# are used as additional randomisation when needed)
# ---------------------------------------------------------------------------

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
    "Gecko/20100101 Firefox/125.0",
]

# ---------------------------------------------------------------------------
# Driver factory
# ---------------------------------------------------------------------------


def create_stealth_driver(
    headless: bool = True,
    use_subprocess: bool = False,
    no_sandbox: bool = True,
    suppress_del: bool = True,
) -> uc.Chrome:
    """
    Create an **undetected** Chrome WebDriver.

    Parameters
    ----------
    headless : bool
        Run in headless mode.
    use_subprocess : bool
        Use subprocess to launch Chrome. Often False is more stable on Windows.
    no_sandbox : bool
        Disable sandbox (often required in Docker/Linux, but helps stability).
    suppress_del : bool
        Neutralize the driver's __del__ method after creation to prevent
        WinError 6 "Handle is invalid" during garbage collection.
    """
    options = uc.ChromeOptions()

    if headless:
        options.add_argument("--headless=new")

    if no_sandbox:
        options.add_argument("--no-sandbox")
    
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")

    # Retry initialization once if it fails immediately (fixes "no such window" blips)
    for attempt in range(2):
        try:
            driver = uc.Chrome(options=options, use_subprocess=use_subprocess)
            
            # Neutralize __del__ to prevent annoying WinError 6 on Windows
            if suppress_del:
                try:
                    driver.__del__ = lambda: None
                except Exception:
                    pass
            
            driver.maximize_window()
            driver.implicitly_wait(5)
            return driver
        except Exception as e:
            if attempt == 1:
                raise e
            time.sleep(1)

    raise RuntimeError("Failed to initialize stealth driver")


def force_quit_driver(driver: uc.Chrome | None) -> None:
    """Safely quit a driver with error suppression and __del__ neutralizing."""
    if not driver:
        return
    try:
        # Neutralize __del__ again just in case
        driver.__del__ = lambda: None
    except Exception:
        pass
        
    try:
        driver.quit()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Safe interaction helpers
# ---------------------------------------------------------------------------


def safe_click(
    driver: uc.Chrome,
    locator: tuple[str, str],
    timeout: int = 10,
    retries: int = 2,
) -> WebElement:
    """Wait for an element to be clickable, then click it (with retry)."""
    for attempt in range(retries + 1):
        try:
            el = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable(locator)
            )
            el.click()
            return el
        except (ElementClickInterceptedException, StaleElementReferenceException):
            if attempt == retries:
                raise
            human_delay(0.5, 1.0)
    raise TimeoutException(f"Could not click {locator} after {retries} retries")


def safe_send_keys(
    driver: uc.Chrome,
    locator: tuple[str, str],
    text: str,
    timeout: int = 10,
    clear_first: bool = True,
) -> WebElement:
    """Wait for an input element, optionally clear it, then type text."""
    el = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located(locator)
    )
    if clear_first:
        el.clear()
    el.send_keys(text)
    return el


def wait_for(
    driver: uc.Chrome,
    locator: tuple[str, str],
    timeout: int = 15,
    condition: str = "presence",
) -> WebElement:
    """
    Generic wait wrapper.

    Parameters
    ----------
    condition : str
        One of ``"presence"``, ``"visible"``, ``"clickable"``.
    """
    cond_map = {
        "presence": EC.presence_of_element_located,
        "visible": EC.visibility_of_element_located,
        "clickable": EC.element_to_be_clickable,
    }
    return WebDriverWait(driver, timeout).until(cond_map[condition](locator))


def human_delay(low: float = 1.0, high: float = 3.0) -> None:
    """Sleep for a random duration to mimic human behaviour."""
    time.sleep(random.uniform(low, high))


def scroll_into_view(driver: uc.Chrome, element: WebElement) -> None:
    """Scroll an element into the viewport with smooth behaviour."""
    driver.execute_script(
        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
        element,
    )
    human_delay(0.3, 0.8)


def scroll_page(driver: uc.Chrome, pixels: int = 600) -> None:
    """Scroll the page down by a given number of pixels."""
    driver.execute_script(f"window.scrollBy(0, {pixels});")
    human_delay(0.8, 1.5)


def dismiss_overlays(driver: uc.Chrome) -> None:
    """
    Attempt to close common modal/overlay elements that block interaction.
    Silently ignores if none are found.
    """
    overlay_selectors = [
        # LinkedIn sign-in prompts & modals
        'button[data-tracking-control-name="public_jobs_contextual-sign-in-modal_modal_dismiss"]',
        'button.modal__dismiss',
        'button[aria-label="Dismiss"]',
        'button[aria-label="Close"]',
        'icon.modal__dismiss',
        # Naukri popups
        'button.crossIcon',
        'button[title="Close"]',
        '.chatbot_closeButton',
        # Generic cookie / GDPR banners
        'button#onetrust-accept-btn-handler',
        'button.cookie-policy__accept',
    ]
    for sel in overlay_selectors:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            btn.click()
            human_delay(0.3, 0.6)
        except Exception:
            pass
