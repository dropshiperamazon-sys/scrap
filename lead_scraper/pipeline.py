"""Dedupe scraped Maps listings by website domain (falling back to phone)."""

from __future__ import annotations

from typing import Iterable, Iterator
from urllib.parse import urlparse

from .maps_scraper import MapsListing


def domain_of(website: str) -> str:
    if not website:
        return ""
    netloc = urlparse(website if website.startswith("http") else f"https://{website}").netloc
    return netloc.lower().removeprefix("www.")


def dedupe_listings(listings: Iterable[MapsListing]) -> Iterator[MapsListing]:
    seen_domains: set[str] = set()
    seen_phones: set[str] = set()

    for listing in listings:
        domain = domain_of(listing.website)
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
        yield listing
