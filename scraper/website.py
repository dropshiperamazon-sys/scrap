"""Visits a business's own public website (homepage, contact/about/team
pages -- header/footer content is part of every page's HTML so social
links there are picked up automatically) looking for a published email,
phone, and Pinterest link.

Only reads publicly accessible pages over plain HTTP(S) GET requests --
never attempts to access authentication-protected areas, and never
retries past a normal HTTP error.
"""

from __future__ import annotations

import logging
from urllib.parse import urljoin, urlparse

import requests

from scraper.validation import extract_emails, extract_phones, extract_pinterest_links

CANDIDATE_PATHS = ("", "contact", "contact-us", "about", "about-us", "team", "our-team")
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; LeadResearchBot/1.0; +outbound B2B research)"}
REQUEST_TIMEOUT_SECONDS = 10.0


def _fetch(url: str, logger: logging.Logger) -> str:
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
        if response.status_code >= 400:
            return ""
        return response.text
    except requests.RequestException as exc:
        logger.debug(f"Website fetch failed for {url}: {exc}")
        return ""


def enrich_from_website(website: str, logger: logging.Logger) -> dict:
    """Returns {"emails": [...], "phones": [...], "pinterest_links": [...], "reachable": bool}."""
    result: dict = {"emails": [], "phones": [], "pinterest_links": [], "reachable": False}
    if not website:
        return result

    parsed = urlparse(website if website.startswith("http") else f"https://{website}")
    base_url = f"{parsed.scheme}://{parsed.netloc}/"

    for path in CANDIDATE_PATHS:
        html = _fetch(urljoin(base_url, path), logger)
        if not html:
            continue
        result["reachable"] = True
        result["emails"].extend(extract_emails(html))
        result["phones"].extend(extract_phones(html))
        result["pinterest_links"].extend(extract_pinterest_links(html))

        if result["emails"] and result["pinterest_links"]:
            break  # enough found; no need to keep crawling more pages

    result["emails"] = list(dict.fromkeys(result["emails"]))
    result["phones"] = list(dict.fromkeys(result["phones"]))
    result["pinterest_links"] = list(dict.fromkeys(result["pinterest_links"]))
    return result
