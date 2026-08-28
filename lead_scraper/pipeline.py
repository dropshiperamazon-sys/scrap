"""End-to-end pipeline: Maps search -> dedupe -> website enrichment -> lead rows."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable, Iterator
from urllib.parse import urlparse

from .maps_scraper import search_listings
from .site_enricher import enrich_from_website


@dataclass
class Lead:
    email: str
    owner_name: str
    company_name: str
    website: str
    pinterest: str
    phone: str


def _domain(website: str) -> str:
    if not website:
        return ""
    netloc = urlparse(website if website.startswith("http") else f"https://{website}").netloc
    return netloc.lower().removeprefix("www.")


def run_pipeline(
    queries: Iterable[str],
    max_results_per_query: int = 60,
    headless: bool = True,
    inter_query_pause_seconds: float = 0.0,
) -> Iterator[Lead]:
    """Run Maps searches for each query, dedupe by domain/phone, then enrich each site.

    `inter_query_pause_seconds` waits between queries (not between results within
    one query) to keep request bursts against Google Maps modest.
    """
    seen_domains: set[str] = set()
    seen_phones: set[str] = set()

    for query_index, query in enumerate(queries):
        if query_index > 0 and inter_query_pause_seconds > 0:
            time.sleep(inter_query_pause_seconds)

        for listing in search_listings(query, max_results=max_results_per_query, headless=headless):
            domain = _domain(listing.website)
            if not domain and not listing.phone:
                continue
            if domain and domain in seen_domains:
                continue
            if listing.phone and listing.phone in seen_phones:
                continue
            if domain:
                seen_domains.add(domain)
            if listing.phone:
                seen_phones.add(listing.phone)

            contact = enrich_from_website(listing.website)
            yield Lead(
                email=contact.email,
                owner_name=contact.owner_name,
                company_name=listing.name,
                website=listing.website,
                pinterest=contact.pinterest,
                phone=listing.phone,
            )
