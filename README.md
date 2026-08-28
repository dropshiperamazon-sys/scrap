# Furniture Lead Scraper

Scrapes furniture-retailer leads from Google Maps using browser automation
(Playwright) — **no paid enrichment APIs** (no Apollo, Hunter, Clearbit,
Outscraper, Phantombuster, etc.). Everything runs locally and for free.

Output columns match the requested order:

```
Email | Owner/Founder/CEO Name | Company Name | Website | Pinterest Link | Phone Number
```

## Important: what this can and can't get you

- **Company name, address, category, phone, website** come straight off the
  Google Maps listing — reliable for most results.
- **Email, Owner/Founder/CEO name, Pinterest link** are only filled in when
  the company has actually published them on its own website (homepage,
  About/Team/Contact pages). This tool never fabricates or guesses an
  executive's name or an email pattern (e.g. no `first.last@domain.com`
  guessing) — for most small/independent stores these fields will come back
  blank, because that information simply isn't public. If you need
  verified personal emails for every row, that requires a paid data
  provider, which was explicitly out of scope here.
- **Google Maps' Terms of Service** don't permit automated scraping. This
  tool is provided for research/educational purposes; use reasonable
  delays, keep result counts modest, and expect to update the CSS
  selectors in `lead_scraper/maps_scraper.py` when Google changes its
  markup.
- Scraped emails are for **B2B outreach research**, not bulk email
  campaigns — check CAN-SPAM / anti-spam law obligations before emailing
  anyone on the resulting list.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Usage

```bash
# Default: the 5 built-in cities x 5 categories from the brief
python -m lead_scraper.cli --out leads.xlsx

# Narrow it down
python -m lead_scraper.cli --city "Austin, TX" --category "Office Furniture" --out austin.xlsx

# Run with a visible browser window (useful if Maps shows a CAPTCHA)
python -m lead_scraper.cli --headed --max-per-query 20
```

Default search targets (edit `lead_scraper/config.py` to change them):

- Cities: New York City NY, Los Angeles CA, Chicago IL, Houston TX, Phoenix AZ
- Categories: Furniture Store, Modern Furniture, Luxury Furniture,
  Commercial Furniture, Home Furniture

Results are deduped by website domain (falling back to phone number).

## Project layout

```
lead_scraper/
  config.py         search targets + query builder
  maps_scraper.py   Playwright-driven Google Maps listing scraper
  site_enricher.py  crawls each company's own site for published contact info
  pipeline.py       orchestrates search -> dedupe -> enrichment
  export.py         writes the deduped leads to .xlsx
  cli.py            command-line entry point
tests/              offline unit tests for the parsing logic (no network/browser)
```

## Tests

```bash
pytest
```

The tests only exercise the regex/HTML-parsing helpers with inline HTML
fixtures — they don't launch a browser or hit the network.

## Scaling to thousands of rows

Each Maps `search_listings()` call already paginates by scrolling the
results feed, so raising `--max-per-query` and adding more
`--city`/`--category` combinations is the way to grow the dataset — there's
no bulk-import step needed since everything is scraped directly.
