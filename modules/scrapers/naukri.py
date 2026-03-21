"""
Naukri Stealth Scraper — No Login Required
==========================================
Navigates to Naukri.com's **public** job search pages, scrapes job cards,
and extracts full details without any account authentication.

Follows the same pattern as the LinkedIn scraper:
  1. Navigate to public search URL
  2. Scroll to load cards + dismiss overlays
  3. Extract card-level metadata (title, company, location, link)
  4. Open each job in a new tab for full description
  5. Paginate via scroll + "show more" / next-page buttons
"""

from __future__ import annotations

import re

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from modules.browser import (
    create_stealth_driver,
    dismiss_overlays,
    force_quit_driver,
    human_delay,
    scroll_into_view,
    scroll_page,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SEARCH_URL = "https://www.naukri.com/{slug}-jobs-in-{location}"

# ---------------------------------------------------------------------------
# URL builder
# ---------------------------------------------------------------------------


def _build_search_url(job_title: str, location: str) -> str:
    """
    Naukri uses slug-style URLs:
        naukri.com/data-scientist-jobs-in-bangalore
    """
    slug = re.sub(r"[^a-z0-9]+", "-", job_title.lower()).strip("-")
    loc_slug = re.sub(r"[^a-z0-9]+", "-", location.lower()).strip("-")
    return SEARCH_URL.format(slug=slug, location=loc_slug)


# ---------------------------------------------------------------------------
# Search & collect  (mirrors LinkedIn's scroll-based approach)
# ---------------------------------------------------------------------------


def _search_jobs(driver, job_title: str, location: str, max_jobs: int) -> list[dict]:
    """Navigate to Naukri public search and collect listings."""
    url = _build_search_url(job_title, location)
    driver.get(url)
    human_delay(3, 5)

    # Dismiss any popups / chatbot overlays / cookie banners
    dismiss_overlays(driver)

    jobs: list[dict] = []
    seen_links: set[str] = set()
    scroll_attempts = 0
    max_scroll_attempts = 20  # safety limit

    while len(jobs) < max_jobs and scroll_attempts < max_scroll_attempts:
        # Grab all visible job cards
        cards = driver.find_elements(
            By.CSS_SELECTOR,
            "article.jobTuple, "
            "div.srp-jobtuple-wrapper, "
            "div.cust-job-tuple, "
            "div.list > div.jobTuple"
        )

        if not cards and scroll_attempts == 0:
            print("  [Naukri] No job cards found on page.")
            break

        for card in cards:
            if len(jobs) >= max_jobs:
                break

            try:
                job_data = _extract_card(driver, card, seen_links)
                if job_data:
                    jobs.append(job_data)
                    print(
                        f"  [{len(jobs)}/{max_jobs}] "
                        f"{job_data['job_title']} @ {job_data['company']}"
                    )
            except Exception as exc:  # noqa: BLE001
                print(f"  ⚠️  Skipping card — {exc}")

        # Scroll down to load more cards (same as LinkedIn pattern)
        scroll_page(driver, pixels=800)
        scroll_attempts += 1
        human_delay(1.5, 2.5)

        # Dismiss overlays that may appear after scroll
        dismiss_overlays(driver)

        # Try "Show more" or next-page button
        _click_show_more_or_next(driver)

    return jobs


# ---------------------------------------------------------------------------
# Card extraction  (mirrors LinkedIn's pattern)
# ---------------------------------------------------------------------------


def _extract_card(driver, card, seen_links: set) -> dict | None:
    """
    Extract job data from a single Naukri job card.

    Step 1: Read card-level metadata (fast, no navigation)
    Step 2: Open the detail page in a new tab for full description
    """

    # ── Step 1: Job link from the card ──
    try:
        link_el = card.find_element(By.CSS_SELECTOR, "a.title, a[class*='title']")
        job_link = link_el.get_attribute("href")
    except NoSuchElementException:
        try:
            link_el = card.find_element(By.TAG_NAME, "a")
            job_link = link_el.get_attribute("href")
        except NoSuchElementException:
            return None

    if not job_link:
        return None

    # Normalise — strip tracking params
    job_link = job_link.split("?")[0]

    if job_link in seen_links:
        return None
    seen_links.add(job_link)

    # ── Step 1: Card-level metadata ──
    job_title = _text_from(card, "a.title, .row1 a, .desig")
    company = _text_from(card, ".comp-name, .subTitle a, .companyInfo a")
    location = _text_from(card, ".loc, .locWdth, .location span, .loc-wrap span")

    # ── Step 2: Full description (open in new tab) ──
    job_description = _get_full_description(driver, job_link)

    return {
        "job_title": _clean(job_title),
        "company": _clean(company),
        "location": _clean(location),
        "job_link": job_link,
        "job_description": _clean(job_description),
    }


def _get_full_description(driver, job_link: str) -> str:
    """
    Open the job detail page in a new tab and extract the full description.
    Falls back to 'No description available.' on failure.
    (Same pattern as LinkedIn scraper.)
    """
    main_window = driver.current_window_handle
    try:
        driver.execute_script("window.open(arguments[0], '_blank');", job_link)
        human_delay(2, 4)
        driver.switch_to.window(driver.window_handles[-1])

        dismiss_overlays(driver)

        # Naukri job description containers
        desc = _text_or_default(
            driver,
            "div.job-desc, "
            "section.job-desc, "
            "div.styles_JDC__dang-inner-html, "
            "div[class*='dang-inner-html'], "
            "div.jd-desc",
            default="No description available.",
        )
        return desc

    except Exception:
        return "No description available."

    finally:
        # Close the detail tab and switch back
        if len(driver.window_handles) > 1:
            driver.close()
        driver.switch_to.window(main_window)
        human_delay(0.5, 1.0)


# ---------------------------------------------------------------------------
# "Show more" / pagination  (combined approach)
# ---------------------------------------------------------------------------


def _click_show_more_or_next(driver) -> None:
    """
    Try clicking "show more" style buttons first, then fall back
    to next-page pagination links.
    """
    selectors = [
        # "Show more" / load-more style buttons
        "button[class*='show-more']",
        "button[class*='load-more']",
        # Next-page pagination links
        "a.fright.fs14.btn-secondary.br2",
        "a[class*='btn-secondary'][href]",
        "a.styles_btn-secondary",
    ]
    for sel in selectors:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            scroll_into_view(driver, btn)
            btn.click()
            human_delay(1.5, 3.0)
            dismiss_overlays(driver)
            return
        except (NoSuchElementException, Exception):
            continue


# ---------------------------------------------------------------------------
# Helpers  (identical to LinkedIn scraper)
# ---------------------------------------------------------------------------


def _text_from(parent, css: str) -> str:
    """First matching child's text, or 'N/A'."""
    for sel in css.split(","):
        try:
            el = parent.find_element(By.CSS_SELECTOR, sel.strip())
            text = el.text.strip()
            if text:
                return text
        except NoSuchElementException:
            continue
    return "N/A"


def _text_or_default(driver, css: str, default: str = "N/A") -> str:
    """First matching element's text across the driver, or *default*."""
    for sel in css.split(","):
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel.strip())
            text = el.text.strip()
            if text:
                return text
        except NoSuchElementException:
            continue
    return default


def _clean(text: str) -> str:
    """Collapse whitespace and strip."""
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def scrape_naukri(
    job_title: str,
    location: str,
    max_jobs: int = 25,
    headless: bool = True,
    driver=None,
) -> tuple[list[dict], object]:
    """
    Scrape Naukri public job search — **no login required**.

    Returns
    -------
    tuple[list[dict], driver]
        The scraped jobs and the WebDriver instance (caller should quit it).
    """
    own_driver = driver is None
    if own_driver:
        driver = create_stealth_driver(headless=headless)

    print(f"\n🔍 [Naukri] Searching for '{job_title}' in '{location}' "
          f"(max {max_jobs}, headless={headless})…")

    try:
        jobs = _search_jobs(driver, job_title, location, max_jobs)
    except Exception:
        if own_driver:
            force_quit_driver(driver)
        raise

    print(f"✅ [Naukri] Scraped {len(jobs)} job(s).")
    return jobs, driver
