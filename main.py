"""Universal Business Lead Scraper -- entry point.

Enter any KEYWORD + LOCATION (via config.yaml, --keyword/--location, or an
interactive prompt) and this discovers matching businesses on Google Maps,
enriches each with a publicly found email/phone/Pinterest link, dedupes
and merges across searches, and keeps output/leads.xlsx up to date after
every single lead -- nothing is held back until the run finishes.

Usage:
    python main.py
    python main.py --test
    python main.py --resume
    python main.py --headless
    python main.py --limit 50
    python main.py --keyword "dentist" --location "Houston, TX"

See README.md for full setup and Windows VPS operation instructions.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

from database.db import Database
from export.excel import write_excel
from scraper.browser import BrowserManager
from scraper.discovery import RawBusiness, discover_businesses
from scraper.enrichment import enrich_business
from utils.config_loader import AppConfig, build_app_config, load_config
from utils.delays import wait_between_batches
from utils.logger import log_business_result, setup_logging
from utils.normalizer import (
    clean_phone_display,
    normalize_domain,
    normalize_name_for_matching,
    normalize_phone_for_matching,
    normalize_website,
)

BANNER = "=" * 40


@dataclass
class RunStats:
    keywords_processed: int = 0
    locations_processed: int = 0
    businesses_discovered: int = 0
    new_leads: int = 0
    duplicates_skipped: int = 0
    websites_found: int = 0
    emails_found: int = 0
    phones_found: int = 0
    pinterest_found: int = 0
    partial_leads: int = 0
    failed: int = 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Universal Business Lead Scraper")
    parser.add_argument("--test", action="store_true", help="Process only a handful of businesses to verify the pipeline works.")
    parser.add_argument("--resume", action="store_true", help="Resume a previous run, skipping already-completed searches.")
    parser.add_argument("--headless", action="store_true", help="Force headless browser mode (overrides config.yaml's headless: false).")
    parser.add_argument("--limit", type=int, default=None, help="Stop after this many NEW leads (duplicates don't count).")
    parser.add_argument("--keyword", type=str, default=None, help="Single keyword; overrides config.yaml keywords (requires --location too).")
    parser.add_argument("--location", type=str, default=None, help="Single location; overrides config.yaml locations (requires --keyword too).")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to the YAML config file.")
    return parser.parse_args(argv)


def prompt_for_keyword_and_location() -> tuple[str, str]:
    print("No keyword/location configured.")
    keyword = input("Enter keyword:\n> ").strip()
    location = input("Enter location:\n> ").strip()
    return keyword, location


def resolve_config(args: argparse.Namespace) -> AppConfig:
    raw = load_config(args.config)

    overrides: dict = {}
    if args.headless:
        overrides["headless"] = True
    if args.keyword and args.location:
        overrides["keywords"] = [args.keyword]
        overrides["locations"] = [args.location]

    config = build_app_config(raw, overrides)

    if not config.keywords or not config.locations:
        keyword, location = prompt_for_keyword_and_location()
        config.keywords = [keyword]
        config.locations = [location]

    if args.test:
        config.max_results_per_query = min(config.max_results_per_query, 5)
        config.batch_size = min(config.batch_size, 5)
        config.min_delay_seconds = 5
        config.max_delay_seconds = 10
        if args.limit is None:
            args.limit = 5

    return config


def process_business(raw: RawBusiness, keyword: str, location: str, db: Database, browser: BrowserManager, logger, config: AppConfig, stats: RunStats) -> bool:
    """Returns True if this was a brand-new lead (counts toward --limit)."""
    normalized_domain = normalize_domain(raw.website)
    normalized_phone = normalize_phone_for_matching(raw.phone)
    normalized_name = normalize_name_for_matching(raw.company_name)

    existing = db.find_matching_business(normalized_domain, normalized_phone, normalized_name)

    if existing and existing["email"] and existing["pinterest"]:
        stats.duplicates_skipped += 1
        logger.info(f"Duplicate (already complete), skipping re-enrichment: {raw.company_name}")
        return False

    try:
        enriched = enrich_business(browser, raw, logger, find_email=config.find_email, find_pinterest=config.find_pinterest)
    except Exception as exc:
        logger.error(f"Enrichment failed for {raw.company_name}: {exc}")
        db.log_error("ENRICHMENT", str(exc), keyword, location)
        stats.failed += 1
        return False

    website_norm = normalize_website(enriched.website)
    phone_display = clean_phone_display(enriched.phone) if config.find_phone else ""

    is_new = existing is None

    if existing:
        merged_fields = {}
        if not existing["website"] and website_norm:
            merged_fields["website"] = website_norm
            merged_fields["normalized_domain"] = normalized_domain
        if not existing["phone"] and phone_display:
            merged_fields["phone"] = phone_display
            merged_fields["normalized_phone"] = normalized_phone
        if not existing["email"] and enriched.email:
            merged_fields["email"] = enriched.email
        if not existing["pinterest"] and enriched.pinterest:
            merged_fields["pinterest"] = enriched.pinterest
        if merged_fields:
            db.update_business(existing["id"], merged_fields)
        stats.duplicates_skipped += 1
        final_website = merged_fields.get("website") or existing["website"]
        final_email = merged_fields.get("email") or existing["email"]
        final_phone = merged_fields.get("phone") or existing["phone"]
        final_pinterest = merged_fields.get("pinterest") or existing["pinterest"]
    else:
        db.insert_business(
            {
                "company_name": enriched.company_name,
                "normalized_name": normalized_name,
                "website": website_norm,
                "normalized_domain": normalized_domain,
                "phone": phone_display,
                "normalized_phone": normalized_phone,
                "email": enriched.email,
                "pinterest": enriched.pinterest,
                "address": raw.address,
                "keyword": keyword,
                "location": location,
                "status": enriched.status,
            }
        )
        stats.new_leads += 1
        if enriched.status == "PARTIAL":
            stats.partial_leads += 1
        final_website, final_email, final_phone, final_pinterest = website_norm, enriched.email, phone_display, enriched.pinterest

    if final_website:
        stats.websites_found += 1
    if final_email:
        stats.emails_found += 1
    if final_phone:
        stats.phones_found += 1
    if final_pinterest:
        stats.pinterest_found += 1

    log_business_result(
        logger, keyword, location, enriched.company_name,
        website_found=bool(final_website), email_found=bool(final_email),
        phone_found=bool(final_phone), pinterest_found=bool(final_pinterest),
        status=enriched.status,
    )

    print(f"Company: {enriched.company_name}")
    print(f"Website: {'FOUND' if final_website else 'NOT FOUND'}")
    print(f"Email: {'FOUND' if final_email else 'NOT FOUND'}")
    print(f"Phone: {'FOUND' if final_phone else 'NOT FOUND'}")
    print(f"Pinterest: {'FOUND' if final_pinterest else 'NOT FOUND'}")

    # Save immediately -- never wait until the whole run finishes.
    write_excel(db.get_export_rows(), config.output_file)
    print("Saved to Excel.")

    return is_new


def _run_batch(batch: list[RawBusiness], keyword: str, location: str, db: Database, browser: BrowserManager, logger, config: AppConfig, stats: RunStats, args: argparse.Namespace, new_leads_so_far: int) -> int:
    new_in_batch = 0
    for index, raw in enumerate(batch, start=1):
        print(f"Current batch: {index}/{len(batch)}")
        if args.limit is not None and (new_leads_so_far + new_in_batch) >= args.limit:
            break
        try:
            if process_business(raw, keyword, location, db, browser, logger, config, stats):
                new_in_batch += 1
        except Exception as exc:
            logger.error(f"Unexpected error processing {raw.company_name}: {exc}")
            db.log_error("PROCESSING", str(exc), keyword, location)
            stats.failed += 1
    print(f"Batch complete: {len(batch)}/{len(batch)}")
    return new_in_batch


def run(config: AppConfig, args: argparse.Namespace, stats: RunStats) -> None:
    logger = setup_logging(config.log_file)
    db = Database(config.database_file)
    new_leads_this_run = 0
    limit_reached = False

    combinations = config.combinations()
    completed_keywords: set[str] = set()
    completed_locations: set[str] = set()
    print(BANNER)
    print(" UNIVERSAL BUSINESS LEAD SCRAPER")
    print(BANNER)

    with BrowserManager(headless=config.headless, logger=logger) as browser:
        for keyword, location in combinations:
            if limit_reached:
                break

            if args.resume and db.get_search_status(keyword, location) == "COMPLETE":
                logger.info(f"Skipping already-completed search: {keyword!r} / {location!r}")
                continue

            print(BANNER)
            print(f"Keyword: {keyword}")
            print(f"Location: {location}")
            db.start_search(keyword, location)

            try:
                raw_businesses, diagnostics = discover_businesses(browser, keyword, location, config.max_results_per_query, logger)
            except Exception as exc:
                logger.error(f"Discovery failed for {keyword!r}/{location!r}: {exc}")
                db.log_error("DISCOVERY", str(exc), keyword, location)
                continue

            if config.require_website:
                raw_businesses = [business for business in raw_businesses if business.website]

            stats.businesses_discovered += len(raw_businesses)
            print(f"Businesses discovered: {len(raw_businesses)}")
            print(f"(feed found: {diagnostics.feed_found}, cards on page: {diagnostics.card_count})")

            fully_processed = True
            batch: list[RawBusiness] = []
            for raw in raw_businesses:
                batch.append(raw)
                if len(batch) >= config.batch_size:
                    new_leads_this_run += _run_batch(batch, keyword, location, db, browser, logger, config, stats, args, new_leads_this_run)
                    batch = []
                    if args.limit is not None and new_leads_this_run >= args.limit:
                        limit_reached = True
                        fully_processed = False
                        break
                    wait_between_batches(config.min_delay_seconds, config.max_delay_seconds, logger)

            if not limit_reached and batch:
                new_leads_this_run += _run_batch(batch, keyword, location, db, browser, logger, config, stats, args, new_leads_this_run)
                if args.limit is not None and new_leads_this_run >= args.limit:
                    limit_reached = True

            if fully_processed:
                db.complete_search(keyword, location)
                completed_keywords.add(keyword)
                completed_locations.add(location)

    stats.keywords_processed = len(completed_keywords)
    stats.locations_processed = len(completed_locations)
    _print_final_summary(stats, config)
    db.close()


def _print_final_summary(stats: RunStats, config: AppConfig) -> None:
    print(BANNER)
    print("RUN COMPLETE")
    print(BANNER)
    print(f"Keywords processed: {stats.keywords_processed}")
    print(f"Locations processed: {stats.locations_processed}")
    print(f"Businesses discovered: {stats.businesses_discovered}")
    print(f"New leads: {stats.new_leads}")
    print(f"Duplicates skipped: {stats.duplicates_skipped}")
    print(f"Websites found: {stats.websites_found}")
    print(f"Emails found: {stats.emails_found}")
    print(f"Phones found: {stats.phones_found}")
    print(f"Pinterest profiles found: {stats.pinterest_found}")
    print(f"Partial leads: {stats.partial_leads}")
    print(f"Failed: {stats.failed}")
    print("Excel:")
    print(f"  {config.output_file}")
    print("Database:")
    print(f"  {config.database_file}")
    print("Log:")
    print(f"  {config.log_file}")
    print(BANNER)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    config = resolve_config(args)
    stats = RunStats()
    try:
        run(config, args, stats)
    except KeyboardInterrupt:
        print("\nInterrupted by user. Progress up to this point has been saved.")
        print("Run again with --resume to continue.")
        sys.exit(0)
    except Exception as exc:
        print(f"\nFatal error: {exc}")
        print("Any leads processed before this point were already saved to Excel and SQLite.")
        print("Check logs/app.log for details. If this is a browser error, try: playwright install chromium")
        print("Then run again with --resume to continue where this run left off.")
        sys.exit(1)


if __name__ == "__main__":
    main()
