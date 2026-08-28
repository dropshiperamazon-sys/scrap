"""Command-line entry point.

Examples:
    python -m lead_scraper.cli --out leads.xlsx
    python -m lead_scraper.cli --city "Austin, TX" --category "Office Furniture" --out austin.xlsx
    python -m lead_scraper.cli --headed --max-per-query 20   # debug a CAPTCHA / selector issue
"""

from __future__ import annotations

import argparse

from .config import build_queries
from .export import export_xlsx
from .pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape furniture-store leads from Google Maps (no paid APIs).")
    parser.add_argument("--city", action="append", help="City to search (repeatable). Defaults to the 5 built-in cities.")
    parser.add_argument("--category", action="append", help="Search category (repeatable). Defaults to the 5 built-in categories.")
    parser.add_argument("--max-per-query", type=int, default=60, help="Max Maps listings to pull per city/category query.")
    parser.add_argument("--out", default="leads.xlsx", help="Output .xlsx path.")
    parser.add_argument("--headed", action="store_true", help="Run the browser with a visible window (useful for debugging/CAPTCHAs).")
    args = parser.parse_args()

    queries = build_queries(cities=args.city, categories=args.category)
    print(f"Running {len(queries)} search queries...")

    leads = list(run_pipeline(queries, max_results_per_query=args.max_per_query, headless=not args.headed))
    export_xlsx(leads, args.out)
    print(f"Saved {len(leads)} deduped leads to {args.out}")


if __name__ == "__main__":
    main()
