"""Step 2: search Google for each imported row using a user-supplied query
template, then visit a handful of the organic result links looking for a
published email/owner name/Pinterest link.

This drives a real browser for the search itself (so it sees what a normal
user would see, cookies and all) but fetches the result pages directly via
`requests` for speed. Google Search scraping isn't covered by Google's
Terms of Service -- keep volumes modest and expect occasional CAPTCHAs,
which will simply show up as a row with no links found.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Iterator
from urllib.parse import quote_plus

import requests
from playwright.sync_api import Page, sync_playwright

from .contact_finder import Contact, extract_contact
from .importer import ImportedRow

GOOGLE_SEARCH_URL = "https://www.google.com/search?q={query}"
_EXCLUDED_HOST_RE = re.compile(r"google\.com|googleusercontent\.com|gstatic\.com", re.IGNORECASE)
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; LeadResearchBot/1.0; +outbound B2B research)"}
REQUEST_TIMEOUT_SECONDS = 8.0


@dataclass
class SearchLead:
    domain: str
    company_name: str
    email: str = ""
    owner_name: str = ""
    pinterest: str = ""


def build_query(template: str, domain: str, company_name: str) -> str:
    return template.replace("{domain}", domain).replace("{company}", company_name)


def _filter_result_links(hrefs: list[str]) -> list[str]:
    """Drop Google's own domains and de-duplicate while preserving order."""
    seen: set[str] = set()
    links: list[str] = []
    for href in hrefs:
        if _EXCLUDED_HOST_RE.search(href):
            continue
        if href not in seen:
            seen.add(href)
            links.append(href)
    return links


def _extract_result_links(page: Page) -> list[str]:
    hrefs = page.eval_on_selector_all('a[href^="http"]', "els => els.map(el => el.href)")
    return _filter_result_links(hrefs)


def _fetch(url: str) -> str:
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.text
    except requests.RequestException:
        return ""


def run_search_enrich(
    rows: list[ImportedRow],
    query_template: str,
    results_per_query: int = 3,
    pause_seconds: float = 2.5,
    headless: bool = True,
) -> Iterator[SearchLead]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        page = browser.new_page()
        try:
            for index, row in enumerate(rows):
                if index > 0 and pause_seconds > 0:
                    time.sleep(pause_seconds)

                query = build_query(query_template, row.domain, row.company_name)
                page.goto(GOOGLE_SEARCH_URL.format(query=quote_plus(query)), timeout=30000)
                page.wait_for_timeout(1500)
                links = _extract_result_links(page)[:results_per_query]

                contact = Contact()
                for link in links:
                    html = _fetch(link)
                    if not html:
                        continue
                    contact.merge(extract_contact(html))
                    if contact.complete:
                        break

                yield SearchLead(
                    domain=row.domain,
                    company_name=row.company_name,
                    email=contact.email,
                    owner_name=contact.owner_name,
                    pinterest=contact.pinterest,
                )
        finally:
            browser.close()
