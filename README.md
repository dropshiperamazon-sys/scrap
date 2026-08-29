# Furniture Lead Scraper

Python CLI, no paid APIs (no Apollo, Hunter, Clearbit, Outscraper,
Phantombuster, etc.) — everything runs locally via Playwright (Google Maps
+ Google Search) and `requests` (page fetching).

Two-step workflow:

1. **`scrape`** — scrapes a Google Maps search and exports a simple file
   with `Website` (domain only) and `Company Name`. Edit that file by hand
   if you want before moving on.
2. **`search`** — reuploads that file. For each row, opens a real (headless
   by default) browser to Google Search using a query template you write
   yourself (e.g. `{company} {domain} owner email contact`), reads the
   organic result links, then visits a few of those pages looking for a
   published email, owner name, and Pinterest link. Exports the final file
   in the requested column order:

   ```
   Email | Owner/Founder/CEO Name | Company Name | Website | Pinterest Link | Phone Number
   ```

An `--full` flag on `scrape` skips Google Search entirely and enriches
straight from each company's own site instead — useful if you don't need
step 2 at all.

## Important: what this can and can't get you

- **Company name, address, category, phone, website** come straight off
  the Google Maps listing — reliable for most results.
- **Email, Owner/Founder/CEO name, Pinterest link** are only filled in when
  a page actually publishes them. This tool never fabricates or guesses an
  executive's name or an email pattern (e.g. no `first.last@domain.com`
  guessing) — for most small/independent stores these will come back
  blank, because that information simply isn't public.
- **Google's Terms of Service** don't cover automated Maps or Search
  scraping. This is a research tool: keep result counts modest, add
  delays, and expect to update the CSS selectors in
  `lead_scraper/maps_scraper.py` / `lead_scraper/search_enricher.py` when
  Google changes its markup.
- Use scraped emails for B2B outreach research, not bulk campaigns, without
  checking CAN-SPAM / anti-spam obligations first.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python -m lead_scraper.check_setup   # confirms Python version, deps, and Chromium all work
```

## Usage

### Step 1 — scrape Google Maps

```bash
# Default: the 5 built-in cities x 5 categories
python -m lead_scraper.cli scrape --out leads_domain_company.csv

# Narrow it down
python -m lead_scraper.cli scrape --city "Austin, TX" --category "Office Furniture" --max-per-query 15 --out austin.csv

# Watch the browser (useful if Maps shows a CAPTCHA, or a run comes back with 0 listings)
python -m lead_scraper.cli scrape --headed --max-per-query 10
```

Each query's console line shows diagnostics —
`(feed found: True/False, cards on page: N)` — so a 0-result run is
debuggable: `feed found: False` means the results-panel selector is stale;
`cards on page: 0` means the results-card selector is stale; cards found
but 0 listings means the detail-panel selectors need updating. All three
live at the top of `lead_scraper/maps_scraper.py`.

**Advanced — skip Step 2 entirely:**
```bash
python -m lead_scraper.cli scrape --full --out leads_full.xlsx
```
Enriches directly from each company's own site (About/Team/Contact pages)
instead of exporting the basic Website+Company file.

### Step 2 — find emails via Google Search

```bash
python -m lead_scraper.cli search \
  --in leads_domain_company.csv \
  --query-template "{company} {domain} owner email contact" \
  --results-per-query 3 \
  --out leads_final.xlsx
```

- `--query-template` — write whatever Google query you'd normally type.
  `{domain}` and `{company}` get substituted per row. Examples:
  - `"{company}" owner OR founder OR CEO`
  - `site:{domain} "email" OR "contact"`
- `--results-per-query` — how many of the top result links to visit per row.
- `--pause` — seconds between searches (default 2.5).
- `--headed` — watch the browser (useful for CAPTCHA debugging).

## Project layout

```
lead_scraper/
  config.py           search targets + query builder
  maps_scraper.py     Playwright-driven Google Maps listing scraper
  contact_finder.py   shared regex extraction of email/owner name/Pinterest link
  site_enricher.py    advanced path: crawl each company's own site directly
  search_enricher.py  Step 2: Google-search each row, visit result pages
  pipeline.py         dedupe scraped listings by domain/phone
  importer.py         reads back a reuploaded Website+Company file
  export.py           writes .csv/.xlsx in either output shape
  check_setup.py      pre-flight environment check
  cli.py              `scrape` and `search` subcommands
tests/                 offline unit tests (no network/browser)
```

## Tests

```bash
pytest
```

Tests only exercise pure parsing/logic (regex extraction, deduping, CSV
import, query templating) with in-memory fixtures — no network or browser
involved.
