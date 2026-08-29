"""Enrichment pipeline for a single discovered business: try the company's
own website first, then fall back to public web search only for whatever
is still missing. Never invents a value -- returns blanks when nothing
publicly available is found.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from scraper.browser import BrowserManager
from scraper.discovery import RawBusiness
from scraper.validation import clean_company_name, domain_of, pick_best_email, pick_best_pinterest
from scraper.web_search import find_email_via_search, find_pinterest_via_search
from scraper.website import enrich_from_website


@dataclass
class EnrichedLead:
    company_name: str
    website: str
    phone: str
    email: str
    pinterest: str
    website_reachable: bool
    status: str  # COMPLETE or PARTIAL


def enrich_business(
    browser: BrowserManager,
    raw: RawBusiness,
    logger: logging.Logger,
    find_email: bool = True,
    find_pinterest: bool = True,
) -> EnrichedLead:
    company_name = clean_company_name(raw.company_name)
    website_result = enrich_from_website(raw.website, logger)

    emails = list(website_result["emails"])
    pinterest_links = list(website_result["pinterest_links"])
    phones = list(website_result["phones"])

    needs_search = (find_email and not emails) or (find_pinterest and not pinterest_links)
    if needs_search:
        search_page = browser.safe_new_page()
        try:
            if find_email and not emails:
                emails.extend(find_email_via_search(search_page, company_name, domain_of(raw.website), logger))
            if find_pinterest and not pinterest_links:
                pinterest_links.extend(find_pinterest_via_search(search_page, company_name, logger))
        finally:
            browser.close_page(search_page)

    best_email = pick_best_email(emails, raw.website)
    best_pinterest = pick_best_pinterest(pinterest_links, company_name)
    best_phone = raw.phone or (phones[0] if phones else "")

    status = "COMPLETE" if (not raw.website or website_result["reachable"]) else "PARTIAL"

    return EnrichedLead(
        company_name=company_name,
        website=raw.website,
        phone=best_phone,
        email=best_email,
        pinterest=best_pinterest,
        website_reachable=website_result["reachable"],
        status=status,
    )
