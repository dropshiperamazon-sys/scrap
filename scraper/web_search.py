"""Public web-search enrichment: used only when a business's own website
doesn't publish an email or Pinterest link. Drives a real browser to
Google Search with queries like '"Company Name" "email"' and reads the
visible results-page text.

No CAPTCHA solving, no anti-bot evasion, no stealth/fingerprint spoofing.
If a search page shows a CAPTCHA or "unusual traffic" notice, that single
search is abandoned and logged -- never retried or bypassed.
"""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

from playwright.sync_api import Page

from scraper.validation import extract_emails, extract_pinterest_links

GOOGLE_SEARCH_URL = "https://www.google.com/search?q={query}"

# NOTE: plain "captcha"/"recaptcha" are deliberately NOT here -- Google's
# results pages carry a standard "This site is protected by reCAPTCHA"
# footer disclaimer on essentially every normal search now, blocked or
# not, so matching those words alone is a guaranteed false positive. Only
# phrasing that is distinctive to Google's actual block/interstitial page
# belongs in this list.
_BLOCK_INDICATORS = (
    "unusual traffic from your computer network",
    "our systems have detected unusual traffic",
    "sending automated queries",
    "verify you're not a robot",
)

# A genuine Google interstitial replaces the entire results page with just
# that notice, so its visible text is short. A normal results page can be
# thousands of characters; checking length alongside the phrase avoids
# treating an incidental mention as a block.
_BLOCK_PAGE_MAX_CHARS = 1500


def _looks_blocked(text: str) -> bool:
    if len(text) > _BLOCK_PAGE_MAX_CHARS:
        return False
    lowered = text.lower()
    return any(indicator in lowered for indicator in _BLOCK_INDICATORS)


def _visible_text(page: Page) -> str:
    try:
        return page.inner_text("body")
    except Exception:
        return ""


def run_search(page: Page, query: str, logger: logging.Logger, pause_ms: int = 1500) -> tuple[str, bool]:
    """Run one Google Search query. Returns (visible_text, blocked)."""
    try:
        page.goto(GOOGLE_SEARCH_URL.format(query=quote_plus(query)), timeout=30000)
        page.wait_for_timeout(pause_ms)
    except Exception as exc:
        logger.warning(f"Search request failed for {query!r}: {exc}")
        return "", False

    # Google redirects to a distinct /sorry/ URL when it genuinely blocks a
    # request -- this is the most reliable signal, independent of page text.
    if "/sorry/" in page.url:
        logger.warning(f"Search blocked (Google's /sorry/ interstitial) for {query!r}; skipping this search.")
        return "", True

    text = _visible_text(page)
    if _looks_blocked(text):
        logger.warning(f"Search appears blocked (CAPTCHA/rate limit) for {query!r}; skipping this search.")
        return "", True
    return text, False


def find_email_via_search(page: Page, company_name: str, domain: str, logger: logging.Logger) -> list[str]:
    """Try a few reasonable public-search variations for a company's email."""
    queries = [f'"{company_name}" "email"', f'"{company_name}" "contact"']
    if domain:
        queries.append(f'"{company_name}" "{domain}"')
        queries.append(f'"email" "{domain}"')

    found: list[str] = []
    for query in queries:
        text, blocked = run_search(page, query, logger)
        if blocked:
            break  # stop enrichment for this business rather than trying to work around the block
        found.extend(extract_emails(text))
        if found:
            break
    return list(dict.fromkeys(found))


def find_pinterest_via_search(page: Page, company_name: str, logger: logging.Logger) -> list[str]:
    queries = [f'"{company_name}" Pinterest', f'"{company_name}" site:pinterest.com']

    found: list[str] = []
    for query in queries:
        text, blocked = run_search(page, query, logger)
        if blocked:
            break
        found.extend(extract_pinterest_links(text))
        if found:
            break
    return list(dict.fromkeys(found))
