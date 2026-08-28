"""Enriches a Maps listing by crawling its own website for published contact details.

This never guesses or fabricates an email or an owner's name (e.g. no
first-initial@domain pattern guessing). If a company hasn't published a
contact email, a named owner, or a Pinterest link anywhere on its own site,
the corresponding field is left blank.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PINTEREST_RE = re.compile(r"https?://(?:www\.)?pinterest\.[a-z.]+/[A-Za-z0-9_./-]+", re.IGNORECASE)
TITLE_KEYWORDS = ("founder", "owner", "ceo", "president", "managing director")
TITLE_PATTERN = "|".join(TITLE_KEYWORDS)
CANDIDATE_PATHS = ("", "about", "about-us", "team", "our-team", "contact", "contact-us")

REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; LeadResearchBot/1.0; +outbound B2B research)"}
REQUEST_TIMEOUT_SECONDS = 8.0


@dataclass
class EnrichedContact:
    email: str = ""
    owner_name: str = ""
    pinterest: str = ""


def _fetch(url: str) -> str:
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.text
    except requests.RequestException:
        return ""


def _find_owner_name(soup: BeautifulSoup) -> str:
    """Look for a line like 'Jane Smith, Founder & CEO' or 'Founder: Jane Smith'."""
    name_before_title = re.compile(rf"([A-Z][a-z]+(?:\s[A-Z][a-z]+){{1,2}})\s*[,\-|]\s*(?:{TITLE_PATTERN})", re.IGNORECASE)
    title_before_name = re.compile(rf"(?:{TITLE_PATTERN})\s*[:\-]\s*([A-Z][a-z]+(?:\s[A-Z][a-z]+){{1,2}})", re.IGNORECASE)

    for text_node in soup.find_all(string=re.compile(TITLE_PATTERN, re.IGNORECASE)):
        line = " ".join(text_node.split())
        match = name_before_title.search(line) or title_before_name.search(line)
        if match:
            return match.group(1).strip()
    return ""


def enrich_from_website(website: str) -> EnrichedContact:
    """Crawl a handful of likely pages on the company's own site for public contact info."""
    if not website:
        return EnrichedContact()

    parsed = urlparse(website if website.startswith("http") else f"https://{website}")
    base_url = f"{parsed.scheme}://{parsed.netloc}/"

    result = EnrichedContact()
    for path in CANDIDATE_PATHS:
        html = _fetch(urljoin(base_url, path))
        if not html:
            continue

        if not result.email:
            email_match = EMAIL_RE.search(html)
            if email_match:
                result.email = email_match.group(0)

        if not result.pinterest:
            pinterest_match = PINTEREST_RE.search(html)
            if pinterest_match:
                result.pinterest = pinterest_match.group(0)

        if not result.owner_name:
            result.owner_name = _find_owner_name(BeautifulSoup(html, "html.parser"))

        if result.email and result.pinterest and result.owner_name:
            break

    return result
