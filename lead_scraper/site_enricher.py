"""Advanced path: crawl each scraped company's own website directly for a
published owner name, email, and Pinterest link -- skips Google Search
entirely. Used by `scrape --full`.
"""

from __future__ import annotations

from urllib.parse import urljoin, urlparse

import requests

from .contact_finder import Contact, extract_contact

CANDIDATE_PATHS = ("", "about", "about-us", "team", "our-team", "contact", "contact-us")
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; LeadResearchBot/1.0; +outbound B2B research)"}
REQUEST_TIMEOUT_SECONDS = 8.0


def _fetch(url: str) -> str:
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.text
    except requests.RequestException:
        return ""


def enrich_from_website(website: str) -> Contact:
    if not website:
        return Contact()

    parsed = urlparse(website if website.startswith("http") else f"https://{website}")
    base_url = f"{parsed.scheme}://{parsed.netloc}/"

    contact = Contact()
    for path in CANDIDATE_PATHS:
        html = _fetch(urljoin(base_url, path))
        if not html:
            continue
        contact.merge(extract_contact(html))
        if contact.complete:
            break
    return contact
