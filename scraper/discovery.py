"""Business discovery via Google Maps search -- completely generic to any
keyword/location combination (no industry-specific logic anywhere here).

No Places API key: this drives a real Chromium browser via Playwright.
Google's Maps markup changes periodically, so selectors here may need
updating over time; diagnostics (feed_found/card_count) are returned
alongside results so a 0-result run is debuggable instead of silent --
see README.md for how to fix a stale selector.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from playwright.sync_api import Page

from scraper.browser import BrowserManager

MAPS_SEARCH_URL = "https://www.google.com/maps/search/{query}"
FEED_SELECTOR = 'div[role="feed"]'
CARD_SELECTOR = f'{FEED_SELECTOR} div[role="article"]'
NAME_SELECTORS = ['h1.DUwDvf', 'h1[class*="fontHeadline"]', '[role="main"] h1']
WEBSITE_SELECTOR = 'a[data-item-id="authority"]'
PHONE_SELECTOR = 'button[data-item-id^="phone:tel:"]'
ADDRESS_SELECTOR = 'button[data-item-id="address"]'
CATEGORY_SELECTOR = 'button[jsaction*="category"]'


@dataclass
class RawBusiness:
    company_name: str
    website: str = ""
    phone: str = ""
    category: str = ""
    address: str = ""  # internal use only (dedup context); never exported to Excel


@dataclass
class DiscoveryDiagnostics:
    feed_found: bool
    card_count: int


def _scroll_feed_until(page: Page, target_count: int, max_rounds: int = 40, pause_seconds: float = 1.2) -> None:
    if page.query_selector(FEED_SELECTOR) is None:
        return
    last_count = 0
    stagnant_rounds = 0
    for _ in range(max_rounds):
        if len(page.query_selector_all(CARD_SELECTOR)) >= target_count:
            return
        page.eval_on_selector(FEED_SELECTOR, "el => el.scrollBy(0, el.scrollHeight)")
        time.sleep(pause_seconds)
        new_count = len(page.query_selector_all(CARD_SELECTOR))
        if new_count == last_count:
            stagnant_rounds += 1
            if stagnant_rounds >= 3:
                return
        else:
            stagnant_rounds = 0
        last_count = new_count


def _first_match_text(page: Page, selectors: list[str]) -> str:
    for selector in selectors:
        element = page.query_selector(selector)
        if element:
            return element.inner_text().strip()
    return ""


def _text_or_empty(page: Page, selector: str) -> str:
    element = page.query_selector(selector)
    return element.inner_text().strip() if element else ""


def _extract_open_detail_panel(page: Page, fallback_name: str) -> RawBusiness | None:
    name = _first_match_text(page, NAME_SELECTORS) or fallback_name
    if not name:
        return None

    website = ""
    website_element = page.query_selector(WEBSITE_SELECTOR)
    if website_element:
        website = website_element.get_attribute("href") or ""

    phone = ""
    phone_element = page.query_selector(PHONE_SELECTOR)
    if phone_element:
        phone = (phone_element.get_attribute("aria-label") or "").replace("Phone: ", "").strip()

    return RawBusiness(
        company_name=name,
        website=website,
        phone=phone,
        category=_text_or_empty(page, CATEGORY_SELECTOR),
        address=_text_or_empty(page, ADDRESS_SELECTOR),
    )


def discover_businesses(
    browser: BrowserManager,
    keyword: str,
    location: str,
    max_results: int,
    logger: logging.Logger,
    detail_pause_ms: int = 1200,
) -> tuple[list[RawBusiness], DiscoveryDiagnostics]:
    """Search Google Maps for `keyword` in `location`; return raw listings
    plus diagnostics. Opens and closes its own page."""
    query = f"{keyword} in {location}"
    page = browser.safe_new_page()
    try:
        page.goto(MAPS_SEARCH_URL.format(query=query.replace(" ", "+")), timeout=30000)
        page.wait_for_timeout(2000)
        _scroll_feed_until(page, max_results)

        feed_found = page.query_selector(FEED_SELECTOR) is not None
        cards = page.query_selector_all(CARD_SELECTOR)[:max_results]

        listings: list[RawBusiness] = []
        for card in cards:
            try:
                fallback_name = (card.get_attribute("aria-label") or "").strip()
                card.click()
                page.wait_for_timeout(detail_pause_ms)
                listing = _extract_open_detail_panel(page, fallback_name)
                if listing:
                    listings.append(listing)
            except Exception as exc:
                logger.warning(f"Failed to parse a Maps card for {query!r}: {exc}")
                continue

        diagnostics = DiscoveryDiagnostics(feed_found=feed_found, card_count=len(cards))
        if not feed_found:
            logger.warning(f"Maps results panel not found for {query!r} -- selectors may be stale.")
        elif diagnostics.card_count == 0:
            logger.warning(f"No result cards found for {query!r} -- selectors may be stale.")
        return listings, diagnostics
    finally:
        browser.close_page(page)
