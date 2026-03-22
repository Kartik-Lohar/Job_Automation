"""
LinkedIn Stealth Scraper — No Login Required
=============================================
Navigates to LinkedIn's **public guest** job search, scrapes job cards,
and extracts full details without any account authentication.

LinkedIn shows a limited number of results to unauthenticated users;
the scraper maximises yield by scrolling the page and dismissing
sign-in prompts.
"""

from __future__ import annotations

import re
from urllib.parse import quote

from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
)

from modules.browser import (
    create_stealth_driver,
    dismiss_overlays,
    force_quit_driver,
    human_delay,
    scroll_into_view,
    scroll_page,
    wait_for,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# LinkedIn guest/public job search — no auth needed
GUEST_SEARCH_URL = (
    "https://www.linkedin.com/jobs/search/"
    "?keywords={keywords}&location={location}"
)

# ---------------------------------------------------------------------------
# Search & collect job cards
# ---------------------------------------------------------------------------


def _search_jobs(driver, job_title: str, location: str, max_jobs: int, past_24_hours: bool = True) -> list[dict]:
    """Navigate to LinkedIn public job search and collect listings."""
    url = GUEST_SEARCH_URL.format(
        keywords=quote(job_title),
        location=quote(location),
    )
    if past_24_hours:
        url += "&f_TPR=r86400"
        
    driver.get(url)
    human_delay(3, 5)

    # Dismiss any sign-in modals / cookie banners
    dismiss_overlays(driver)

    jobs: list[dict] = []
    seen_links: set[str] = set()
    scroll_attempts = 0
    max_scroll_attempts = 15  # safety limit
    no_new_jobs_streak = 0

    while len(jobs) < max_jobs and scroll_attempts < max_scroll_attempts:
        previous_job_count = len(jobs)
        
        # Grab all visible job cards
        cards = driver.find_elements(
            By.CSS_SELECTOR,
            "ul.jobs-search__results-list li, "
            "div.base-card, "
            "div.job-search-card"
        )

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

        if len(jobs) == previous_job_count:
            no_new_jobs_streak += 1
            if no_new_jobs_streak >= 2:
                print(f"  [LinkedIn] On portal there are fewer jobs ({len(jobs)}) than the max jobs ({max_jobs}) given in command. Moving to next pipeline.")
                break
        else:
            no_new_jobs_streak = 0

        # Scroll down to load more cards
        scroll_page(driver, pixels=800)
        scroll_attempts += 1
        human_delay(1.5, 2.5)

        # Dismiss overlays that may appear after scroll
        dismiss_overlays(driver)

        # Try clicking "See more jobs" button if present
        _click_show_more(driver)

    return jobs


# ---------------------------------------------------------------------------
# Card extraction
# ---------------------------------------------------------------------------


def _extract_card(driver, card, seen_links: set) -> dict | None:
    """Extract job data from a single LinkedIn public job card."""

    # ── Job link ──
    try:
        link_el = card.find_element(By.CSS_SELECTOR, "a.base-card__full-link")
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

    # ── Metadata from the card itself ──
    job_title = _text_from(
        card,
        "h3.base-search-card__title, "
        "span.sr-only, "
        "h3.job-search-card__title",
    )
    company = _text_from(
        card,
        "h4.base-search-card__subtitle, "
        "a.hidden-nested-link, "
        "h4.job-search-card__company-name",
    )
    location = _text_from(
        card,
        "span.job-search-card__location, "
        "span.base-search-card__metadata",
    )

    # ── Full job description (open the detail page in a new tab) ──
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
    Clicks the "Show more" button to expand truncated content.
    Falls back to 'No description available.' on failure.
    """
    main_window = driver.current_window_handle
    try:
        driver.execute_script("window.open(arguments[0], '_blank');", job_link)
        human_delay(2, 4)
        driver.switch_to.window(driver.window_handles[-1])

        dismiss_overlays(driver)

        # Click "Show more" to expand the full job description
        _click_show_more_description(driver)

        # Extract the fully expanded description using innerText
        desc = _get_expanded_description_text(driver)
        return desc

    except Exception:
        return "No description available."

    finally:
        # Close the detail tab and switch back
        if len(driver.window_handles) > 1:
            driver.close()
        driver.switch_to.window(main_window)
        human_delay(0.5, 1.0)


def _click_show_more_description(driver) -> None:
    """
    Click the 'Show more' button on a LinkedIn job detail page
    to expand the truncated job description.
    """
    show_more_selectors = [
        "button.show-more-less-html__button--more",
        "button[aria-label='Show more']",
        "button.show-more-less-html__button",
    ]
    for sel in show_more_selectors:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            scroll_into_view(driver, btn)
            driver.execute_script("arguments[0].click();", btn)
            human_delay(1.0, 2.0)
            return
        except (NoSuchElementException, Exception):
            continue


def _get_expanded_description_text(driver) -> str:
    """
    Extract the full job description text after the 'Show more' button
    has been clicked. Uses innerText to capture all expanded content.
    """
    desc_selectors = [
        "div.show-more-less-html__markup",
        "div.description__text",
        "section.show-more-less-html",
        "div.jobs-description__content",
    ]
    for sel in desc_selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            # Use innerText instead of .text to capture fully expanded content
            text = el.get_attribute("innerText") or ""
            text = text.strip()
            if text:
                return text
        except NoSuchElementException:
            continue
    return "No description available."


# ---------------------------------------------------------------------------
# "Show more jobs" button
# ---------------------------------------------------------------------------


def _click_show_more(driver) -> None:
    """Click the 'See more jobs' / 'Show more' button if present."""
    selectors = [
        "button.infinite-scroller__show-more-button",
        "button[aria-label='See more jobs']",
        "button.see-more-jobs",
    ]
    for sel in selectors:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            scroll_into_view(driver, btn)
            btn.click()
            human_delay(1.5, 3.0)
            return
        except (NoSuchElementException, Exception):
            continue


# ---------------------------------------------------------------------------
# Helpers
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


def scrape_linkedin(
    job_title: str,
    location: str,
    max_jobs: int = 25,
    headless: bool = True,
    past_24_hours: bool = True,
    driver=None,
) -> tuple[list[dict], object]:
    """
    Scrape LinkedIn public job search — **no login required**.

    Returns
    -------
    tuple[list[dict], driver]
        The scraped jobs and the WebDriver instance (caller should quit it).
    """
    own_driver = driver is None
    if own_driver:
        driver = create_stealth_driver(headless=headless)

    print(f"\n🔍 [LinkedIn] Searching for '{job_title}' in '{location}' "
          f"(max {max_jobs}, headless={headless})…")

    try:
        jobs = _search_jobs(driver, job_title, location, max_jobs, past_24_hours)
    except Exception:
        if own_driver:
            force_quit_driver(driver)
        raise

    print(f"✅ [LinkedIn] Scraped {len(jobs)} job(s).")
    return jobs, driver
