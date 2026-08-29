"""Validation and selection logic: email format checking, business-domain
preference, phone/Pinterest extraction from raw text, and company-name
cleanup.

This never invents or guesses a contact detail -- it only validates and
chooses among values that were actually found in scraped text.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PINTEREST_RE = re.compile(r"https?://(?:www\.)?pinterest\.[a-z.]+/[A-Za-z0-9_./-]+", re.IGNORECASE)
PHONE_RE = re.compile(r"(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")

# Common false positives: filenames that look like emails (logo@2x.png),
# and template/placeholder addresses that show up in raw page source but
# aren't the business's own contact.
_INVALID_EMAIL_TLDS = {"png", "jpg", "jpeg", "gif", "svg", "webp", "css", "js", "ico", "bmp"}
_PLACEHOLDER_DOMAINS = {
    "example.com", "domain.com", "yourdomain.com", "email.com",
    "sentry.io", "wixpress.com", "godaddy.com", "godaddysites.com",
    "schema.org", "w3.org", "squarespace.com",
}
_PLACEHOLDER_LOCAL_PARTS = {"example", "test", "yourname", "username", "youremail"}
_PREFERRED_LOCAL_PART_PREFIXES = ("info", "contact", "hello", "sales", "support", "office", "admin", "enquiries", "inquiries")

_JUNK_NAME_PATTERNS = [
    re.compile(r"★+"),
    re.compile(r"\bsponsored\b", re.IGNORECASE),
    re.compile(r"\bpermanently closed\b", re.IGNORECASE),
    re.compile(r"\bopen now\b", re.IGNORECASE),
    re.compile(r"\bclosed\b", re.IGNORECASE),
    re.compile(r"\(\d[\d,]*(\.\d+)?\)"),          # e.g. "(1,234)" review counts
    re.compile(r"\b\d+(\.\d+)?\s*stars?\b", re.IGNORECASE),
]


def is_valid_email(email: str) -> bool:
    email = email.strip().lower()
    if not EMAIL_RE.fullmatch(email):
        return False
    local_part, _, domain = email.partition("@")
    tld = domain.rsplit(".", 1)[-1]
    if tld in _INVALID_EMAIL_TLDS:
        return False
    if domain in _PLACEHOLDER_DOMAINS:
        return False
    if local_part in _PLACEHOLDER_LOCAL_PARTS:
        return False
    return True


def extract_emails(text: str) -> list[str]:
    candidates = (match.lower().strip() for match in EMAIL_RE.findall(text))
    return [email for email in dict.fromkeys(candidates) if is_valid_email(email)]


def extract_pinterest_links(text: str) -> list[str]:
    return list(dict.fromkeys(PINTEREST_RE.findall(text)))


def extract_phones(text: str) -> list[str]:
    return list(dict.fromkeys(match.strip() for match in PHONE_RE.findall(text)))


def domain_of(website: str) -> str:
    if not website:
        return ""
    netloc = urlparse(website if website.startswith("http") else f"https://{website}").netloc
    return netloc.lower().removeprefix("www.")


def pick_best_email(candidates: list[str], company_website: str = "") -> str:
    """Preference order: business-domain email > general contact email > other."""
    if not candidates:
        return ""

    company_domain = domain_of(company_website)

    def score(email: str) -> int:
        _, _, domain = email.partition("@")
        value = 0
        if company_domain and domain == company_domain:
            value += 100
        local_part = email.split("@", 1)[0]
        if any(local_part.startswith(prefix) for prefix in _PREFERRED_LOCAL_PART_PREFIXES):
            value += 10
        return value

    return max(candidates, key=score)


def pick_best_pinterest(candidates: list[str], company_name: str = "") -> str:
    """Prefer a Pinterest URL whose slug plausibly matches the company name
    over blindly taking the first search result."""
    if not candidates:
        return ""
    if not company_name:
        return candidates[0]

    normalized_name = re.sub(r"[^a-z0-9]", "", company_name.lower())
    for url in candidates:
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        normalized_slug = re.sub(r"[^a-z0-9]", "", slug.lower())
        if normalized_slug and (normalized_slug in normalized_name or normalized_name in normalized_slug):
            return url
    return candidates[0]


def clean_company_name(name: str) -> str:
    cleaned = name
    for pattern in _JUNK_NAME_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -|,")
    return cleaned.strip()
