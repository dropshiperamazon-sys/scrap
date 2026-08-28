"""Google Maps listing scraper driven by a real browser (Playwright) — no Places API key.

Google's markup and rate limits change without notice, and automated Maps
scraping sits outside Google's Terms of Service, so treat this as a
best-effort research tool: keep result counts modest, add delays, and run
headed (--headed) if you hit a CAPTCHA wall you need to solve by hand.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterator

from playwright.sync_api import Page, sync_playwright

GOOGLE_MAPS_SEARCH_URL = "https://www.google.com/maps/search/{query}"
RESULTS_FEED_SELECTOR = 'div[role="feed"]'
RESULT_CARD_SELECTOR = f'{RESULTS_FEED_SELECTOR} > div > div[role="article"]'


@dataclass
class MapsListing:
    name: str
    category: str = ""
    address: str = ""
    phone: str = ""
    website: str = ""


def _scroll_results_feed(page: Page, target_count: int, scroll_pause: float = 1.5, max_stagnant_rounds: int = 3) -> None:
    """Scroll the results feed until it has `target_count` cards or stops growing."""
    page.wait_for_selector(RESULTS_FEED_SELECTOR, timeout=15000)
    last_count = 0
    stagnant_rounds = 0
    while True:
        current_count = len(page.query_selector_all(RESULT_CARD_SELECTOR))
        if current_count >= target_count:
            return
        page.eval_on_selector(RESULTS_FEED_SELECTOR, "el => el.scrollBy(0, el.scrollHeight)")
        time.sleep(scroll_pause)
        current_count = len(page.query_selector_all(RESULT_CARD_SELECTOR))
        if current_count == last_count:
            stagnant_rounds += 1
            if stagnant_rounds >= max_stagnant_rounds:
                return
        else:
            stagnant_rounds = 0
        last_count = current_count


def _text_or_empty(page: Page, selector: str) -> str:
    element = page.query_selector(selector)
    return element.inner_text().strip() if element else ""


def _extract_open_detail_panel(page: Page) -> MapsListing | None:
    name_element = page.query_selector('h1.DUwDvf, h1[class*="fontHeadline"]')
    if not name_element:
        return None

    website = ""
    website_element = page.query_selector('a[data-item-id="authority"]')
    if website_element:
        website = website_element.get_attribute("href") or ""

    phone = ""
    phone_element = page.query_selector('button[data-item-id^="phone:tel:"]')
    if phone_element:
        phone = (phone_element.get_attribute("aria-label") or "").replace("Phone: ", "").strip()

    return MapsListing(
        name=name_element.inner_text().strip(),
        category=_text_or_empty(page, 'button[jsaction*="category"]'),
        address=_text_or_empty(page, 'button[data-item-id="address"]'),
        phone=phone,
        website=website,
    )


def search_listings(query: str, max_results: int = 60, headless: bool = True, detail_pause_ms: int = 1200) -> Iterator[MapsListing]:
    """Search Google Maps for `query` and yield up to `max_results` listings.

    Selectors here match Google's Maps UI as of writing; if Google changes
    its markup this will need updated selectors (inspect the results panel
    in devtools and adjust the constants at the top of this module).
    """
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        page = browser.new_page()
        try:
            page.goto(GOOGLE_MAPS_SEARCH_URL.format(query=query.replace(" ", "+")), timeout=30000)
            _scroll_results_feed(page, max_results)

            cards = page.query_selector_all(RESULT_CARD_SELECTOR)[:max_results]
            for card in cards:
                card.click()
                page.wait_for_timeout(detail_pause_ms)
                listing = _extract_open_detail_panel(page)
                if listing:
                    yield listing
        finally:
            browser.close()
