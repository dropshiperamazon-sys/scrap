"""Command-line entry point with two subcommands: `scrape` and `search`.

Examples:
    # Step 1: scrape Google Maps, export Website(domain) + Company Name
    python -m lead_scraper.cli scrape --out leads_domain_company.csv

    # Step 1 (advanced): skip Google Search entirely, enrich straight from each site
    python -m lead_scraper.cli scrape --full --out leads_full.xlsx

    # Step 2: reupload the Step-1 file, search Google per row for an email
    python -m lead_scraper.cli search --in leads_domain_company.csv \
        --query-template "{company} {domain} owner email contact" \
        --out leads_final.xlsx

Run `python -m lead_scraper.check_setup` first to confirm your environment
is ready (Python version, dependencies, Playwright's Chromium browser).
"""

from __future__ import annotations

import argparse

from .config import build_queries
from .export import export_basic, export_full
from .importer import load_domain_company_table
from .maps_scraper import search_listings
from .pipeline import dedupe_listings
from .search_enricher import run_search_enrich
from .site_enricher import enrich_from_website


def _cmd_scrape(args: argparse.Namespace) -> None:
    queries = build_queries(cities=args.city, categories=args.category)
    print(f"Running {len(queries)} Maps search queries...")

    all_listings = []
    for index, query in enumerate(queries):
        listings, diagnostics = search_listings(query, max_results=args.max_per_query, headless=not args.headed)
        print(
            f"  [{index + 1}/{len(queries)}] {query!r}: {len(listings)} listings "
            f"(feed found: {diagnostics.feed_found}, cards on page: {diagnostics.card_count})"
        )
        all_listings.extend(listings)

    deduped = list(dedupe_listings(all_listings))
    print(f"{len(deduped)} deduped listings.")

    if args.full:
        rows = []
        for listing in deduped:
            contact = enrich_from_website(listing.website)
            rows.append(
                {
                    "email": contact.email,
                    "owner_name": contact.owner_name,
                    "company_name": listing.name,
                    "website": listing.website,
                    "pinterest": contact.pinterest,
                    "phone": listing.phone,
                }
            )
        export_full(rows, args.out)
    else:
        export_basic(deduped, args.out)

    print(f"Saved to {args.out}")


def _cmd_search(args: argparse.Namespace) -> None:
    rows = load_domain_company_table(args.in_path)
    print(f"Loaded {len(rows)} rows from {args.in_path}")

    leads = []
    for index, lead in enumerate(
        run_search_enrich(
            rows,
            query_template=args.query_template,
            results_per_query=args.results_per_query,
            pause_seconds=args.pause,
            headless=not args.headed,
        )
    ):
        status = "found email" if lead.email else "no email found"
        print(f"  [{index + 1}/{len(rows)}] {lead.company_name!r}: {status}")
        leads.append(lead)

    export_full(
        [
            {
                "email": lead.email,
                "owner_name": lead.owner_name,
                "company_name": lead.company_name,
                "website": lead.domain,
                "pinterest": lead.pinterest,
                "phone": "",
            }
            for lead in leads
        ],
        args.out,
    )
    print(f"Saved to {args.out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Furniture-store lead scraper (Google Maps + Google Search), no paid APIs.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scrape_parser = subparsers.add_parser("scrape", help="Step 1: scrape Google Maps listings.")
    scrape_parser.add_argument("--city", action="append", help="City to search (repeatable). Defaults to the 5 built-in cities.")
    scrape_parser.add_argument("--category", action="append", help="Search category (repeatable). Defaults to the 5 built-in categories.")
    scrape_parser.add_argument("--max-per-query", type=int, default=30, help="Max Maps listings to pull per city/category query.")
    scrape_parser.add_argument("--full", action="store_true", help="Enrich directly from each company's own site instead of exporting the basic Website+Company file.")
    scrape_parser.add_argument("--out", default="leads_domain_company.csv", help="Output path (.csv or .xlsx).")
    scrape_parser.add_argument("--headed", action="store_true", help="Run the browser with a visible window (useful for debugging/CAPTCHAs).")
    scrape_parser.set_defaults(func=_cmd_scrape)

    search_parser = subparsers.add_parser("search", help="Step 2: Google-search each reuploaded row for a published email.")
    search_parser.add_argument("--in", dest="in_path", required=True, help="File from `scrape` (needs Website + Company Name columns; .csv or .xlsx).")
    search_parser.add_argument("--query-template", required=True, help='Query with {domain}/{company} placeholders, e.g. "{company} {domain} owner email contact".')
    search_parser.add_argument("--results-per-query", type=int, default=3, help="How many organic result pages to visit per row.")
    search_parser.add_argument("--pause", type=float, default=2.5, help="Seconds to wait between searches.")
    search_parser.add_argument("--out", default="leads_final.xlsx", help="Output path (.csv or .xlsx).")
    search_parser.add_argument("--headed", action="store_true", help="Run the browser with a visible window.")
    search_parser.set_defaults(func=_cmd_search)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
