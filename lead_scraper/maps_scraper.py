"""Google Maps listing scraper driven by a real browser (Playwright) -- no
Places API key.

Google's Maps markup shifts periodically, so extraction here tries several
selector fallbacks and returns diagnostics (feed found / card count)
instead of silently returning nothing on a stale selector. Automated Maps
scraping isn't covered by Google's Terms of Service -- keep result counts
modest, add delays, and run with --headed if you hit a CAPTCHA wall you
need to solve by hand.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from playwright.sync_api import Page, sync_playwright

GOOGLE_MAPS_SEARCH_URL = "https://www.google.com/maps/search/{query}"
FEED_SELECTOR = 'div[role="feed"]'
CARD_SELECTOR = f'{FEED_SELECTOR} div[role="article"]'
NAME_SELECTORS = ['h1.DUwDvf', 'h1[class*="fontHeadline"]', '[role="main"] h1']
WEBSITE_SELECTOR = 'a[data-item-id="authority"]'
PHONE_SELECTOR = 'button[data-item-id^="phone:tel:"]'
ADDRESS_SELECTOR = 'button[data-item-id="address"]'
CATEGORY_SELECTOR = 'button[jsaction*="category"]'


@dataclass
class MapsListing:
    name: str
    category: str = ""
    address: str = ""
    phone: str = ""
    website: str = ""


@dataclass
class ScrapeDiagnostics:
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


def _extract_open_detail_panel(page: Page, fallback_name: str) -> MapsListing | None:
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

    return MapsListing(
        name=name,
        category=_text_or_empty(page, CATEGORY_SELECTOR),
        address=_text_or_empty(page, ADDRESS_SELECTOR),
        phone=phone,
        website=website,
    )


def search_listings(
    query: str,
    max_results: int = 30,
    headless: bool = True,
    detail_pause_ms: int = 1200,
) -> tuple[list[MapsListing], ScrapeDiagnostics]:
    """Search Google Maps for `query`; return listings plus diagnostics.

    Diagnostics make a 0-result run debuggable: if `feed_found` is False the
    results-panel selector itself is stale; if `card_count` is 0 the
    results-card selector is stale; if `card_count` > 0 but no listings come
    back, the detail-panel selectors (name/website/phone/address) need
    updating -- inspect the page in devtools and adjust the constants above.
    """
    listings: list[MapsListing] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        page = browser.new_page()
        try:
            page.goto(GOOGLE_MAPS_SEARCH_URL.format(query=query.replace(" ", "+")), timeout=30000)
            page.wait_for_timeout(2000)
            _scroll_feed_until(page, max_results)

            feed_found = page.query_selector(FEED_SELECTOR) is not None
            cards = page.query_selector_all(CARD_SELECTOR)[:max_results]

            for card in cards:
                try:
                    fallback_name = (card.get_attribute("aria-label") or "").strip()
                    card.click()
                    page.wait_for_timeout(detail_pause_ms)
                    listing = _extract_open_detail_panel(page, fallback_name)
                    if listing:
                        listings.append(listing)
                except Exception:
                    continue  # skip a card that fails to open/parse rather than aborting the run

            diagnostics = ScrapeDiagnostics(feed_found=feed_found, card_count=len(cards))
        finally:
            browser.close()

    return listings, diagnostics
