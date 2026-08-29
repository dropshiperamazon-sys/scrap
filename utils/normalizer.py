"""General-purpose value normalization: website URLs, phone numbers, and
company names for weak-match deduplication.

The human-readable, junk-stripped company name shown in Excel lives in
scraper.validation.clean_company_name -- normalize_name_for_matching here
is only for comparing two names for dedup purposes.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "gclid", "fbclid", "mc_cid", "mc_eid",
}


def normalize_domain(website: str) -> str:
    """Domain only, lowercase, no scheme/www -- the strongest dedup key."""
    if not website:
        return ""
    netloc = urlparse(website if website.startswith("http") else f"https://{website}").netloc
    return netloc.lower().removeprefix("www.")


def normalize_website(website: str) -> str:
    """Clean, canonical URL: strips tracking query params and a bare
    trailing slash, keeps the rest as-is (never swaps in a directory
    listing URL in place of the real site)."""
    if not website:
        return ""
    url = website if website.startswith("http") else f"https://{website}"
    parsed = urlparse(url)

    query_pairs = [(key, value) for key, value in parse_qsl(parsed.query) if key.lower() not in _TRACKING_PARAMS]
    path = "" if parsed.path == "/" else parsed.path

    cleaned = parsed._replace(path=path, query=urlencode(query_pairs), fragment="")
    return urlunparse(cleaned)


def normalize_phone_for_matching(phone: str) -> str:
    """Digits-only (with a leading US country code assumed for 10-digit
    numbers) form used only for deduplication -- never for display."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 10:
        digits = "1" + digits
    return digits


def clean_phone_display(phone: str) -> str:
    """Light cleanup for the human-readable phone number shown in Excel."""
    if not phone:
        return ""
    return re.sub(r"\s{2,}", " ", phone.strip())


def normalize_name_for_matching(name: str) -> str:
    if not name:
        return ""
    return re.sub(r"[^a-z0-9]", "", name.lower())
