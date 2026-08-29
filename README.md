# Universal Business Lead Scraper

A generic business lead generation and enrichment tool. Enter **any**
keyword and **any** location — `furniture store` / `Chicago, IL`,
`dentist` / `Houston, TX`, `law firm` / `New York, NY`, `restaurant` /
`Los Angeles, CA`, anything — and it discovers matching businesses on
Google Maps, enriches each with a publicly available email, phone, and
Pinterest link, and keeps `output/leads.xlsx` up to date as it goes.

No industry is hard-coded anywhere in the code. No paid scraping APIs
(Apollo, Hunter, Clearbit, Outscraper, Phantombuster, etc.) are used or
required — everything runs locally via Playwright (Chromium) and
`requests`.

## What it does and doesn't do

- Discovers businesses via Google Maps search (browser automation, no
  Places API key).
- For each business, checks its own public website (homepage,
  contact/about/team pages) for a published email, phone, and Pinterest
  link.
- If the website doesn't have an email or Pinterest link, falls back to a
  public Google Search (e.g. `"Company Name" "email"`) — never anything
  requiring login, payment, or bypassing a restriction.
- **Never invents or guesses a contact detail.** No `info@domain.com`
  assumptions — if nothing is publicly found, the field is left blank.
- **Never bypasses CAPTCHA, anti-bot protection, rate limits, or
  authentication.** If a page shows a CAPTCHA or "unusual traffic"
  notice, that one search/page is skipped and logged; the run continues
  with everything else.
- Saves every successful lead immediately (SQLite + Excel), so a crash or
  VPS restart never loses completed work.
- Deduplicates and merges: the same business found under a different
  keyword or in a later run updates the existing record instead of
  creating a duplicate row.

## Final Excel output

`output/leads.xlsx`, exactly these five columns in this order:

```
Email | Company Name | Website | Phone | Pinterest
```

No address, city, state, or ZIP in the Excel file (SQLite keeps that
internally for dedup context only). Blank cells mean "not publicly
found" — never `N/A` or `Unknown`.

## Project structure

```
main.py                  entry point: CLI, config resolution, the run loop
config.yaml               all user-tunable settings (no code changes needed)
requirements.txt
.env.example               no secrets required by default; placeholder only

scraper/
  browser.py              Playwright lifecycle: startup, page creation, crash recovery, shutdown
  discovery.py            Google Maps search -> raw business listings (generic to any keyword)
  website.py              crawls a business's own site for email/phone/Pinterest
  web_search.py           Google Search fallback when the site doesn't have it; CAPTCHA-aware
  enrichment.py           combines website + web_search into one enriched lead
  validation.py           email/phone/Pinterest extraction & validation, company-name cleanup

database/
  db.py                   SQLite: searches (resume), businesses (dedup/merge), processing_errors

export/
  excel.py                writes output/leads.xlsx from the current database state

utils/
  config_loader.py        loads config.yaml, applies CLI overrides
  logger.py               logs/app.log + console
  normalizer.py           domain/phone/name normalization for deduplication
  delays.py               randomized pacing between batches

data/leads.db             SQLite database (created automatically)
output/leads.xlsx         final spreadsheet (created/updated automatically)
logs/app.log              full run log (created automatically)
tests/                    unit + integration tests (offline, no network/browser)
```

## Configuration (`config.yaml`)

```yaml
keywords:
  - furniture store
  - furniture manufacturer

locations:
  - Chicago, IL
  - Houston, TX

batch_size: 5
min_delay_seconds: 120
max_delay_seconds: 300
require_website: true
find_email: true
find_phone: true
find_pinterest: true
headless: false
max_results_per_query: 40
output_file: output/leads.xlsx
database_file: data/leads.db
log_file: logs/app.log
```

Every keyword is crossed with every location:
`keyword1+location1, keyword2+location1, ..., keyword1+location2, ...`
Change keywords, locations, batch size, delay, or headless mode by editing
this file only — never Python code.

## CLI

```bash
python main.py                                          # normal run using config.yaml
python main.py --test                                   # 2-5 businesses only, verifies the whole pipeline
python main.py --resume                                 # skip already-completed keyword/location searches
python main.py --headless                                # force headless (overrides config.yaml's headless: false)
python main.py --limit 50                                # stop after 50 NEW leads (duplicates don't count)
python main.py --keyword "dentist" --location "Houston, TX"   # one-off run, overrides config.yaml for this run
```

If no keyword/location is available from config.yaml or `--keyword`/
`--location`, you'll be prompted interactively:
```
Enter keyword:
> furniture store
Enter location:
> Chicago, IL
```

`--headless` on the command line always forces headless mode; without it,
`config.yaml`'s `headless:` setting is used as-is.

## How discovery, enrichment, dedup, and resume actually work

- **Discovery** (`scraper/discovery.py`) drives a real Chromium browser to
  `https://www.google.com/maps/search/<keyword>+in+<location>`, scrolls
  the results feed, and opens each listing's detail panel for its name,
  website, phone, and category. Google's Maps markup changes periodically
  — if a run reports 0 businesses discovered, the console line shows
  `(feed found: True/False, cards on page: N)`:
  - `feed found: False` → the results-panel selector is stale.
  - `cards on page: 0` → the results-card selector is stale.
  - cards found but 0 listings → the detail-panel selectors (name/
    website/phone) are stale.
  All of these selectors are constants at the top of `discovery.py` —
  inspect the live page in DevTools and update them there.
- **Enrichment** (`scraper/enrichment.py`) checks the business's own site
  first (cheap, direct HTTP); only if that doesn't find an email/Pinterest
  link does it fall back to a Google Search (`scraper/web_search.py`),
  which is a real browser page so it sees exactly what a person would see.
- **Deduplication** (`database/db.py`) matches a newly discovered business
  against existing records by normalized website domain first, then
  normalized phone, then normalized name. A match that's already fully
  enriched (has both an email and a Pinterest link) is skipped entirely
  — no wasted requests. A match missing either field gets re-enriched and
  merged: any field the existing record was missing gets filled in;
  nothing that's already there gets overwritten.
- **Resume** (`--resume`) skips any keyword/location combination already
  marked `COMPLETE` in the `searches` table. A combination interrupted
  mid-way (crash, Ctrl+C, VPS restart) stays `IN_PROGRESS` and will be
  fully re-discovered on the next run — deduplication means businesses
  already saved won't be re-added, just re-checked and possibly merged.
- **Every lead is saved immediately**: SQLite insert/update, then
  `output/leads.xlsx` is fully regenerated from the database (atomic
  write — a crash mid-write never corrupts the file). If the VPS dies
  after 200 leads, those 200 leads are already on disk.

## Setup (any platform)

```bash
python -m venv venv

# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium
```

Run a small test first:
```bash
python main.py --test --headless
```
This processes only a handful of businesses and exercises the entire
pipeline (discovery, website extraction, email/phone/Pinterest
extraction, validation, deduplication, SQLite, Excel, logging). Only
after this succeeds should you run a full job.

## Windows VPS installation (step by step)

**Step 1 — Install Python 3.11+**
Download from https://www.python.org/downloads/windows/ and run the
installer. Check "Add python.exe to PATH" during install.

**Step 2 — Create the project directory**
Copy/clone this project to a folder on the VPS, e.g. `C:\lead-scraper`.
Open PowerShell or Command Prompt in that folder.

**Step 3 — Create and activate a virtual environment**
```powershell
python -m venv venv
venv\Scripts\activate
```
You should see `(venv)` at the start of your prompt.

**Step 4 — Install dependencies**
```powershell
pip install -r requirements.txt
```

**Step 5 — Install the Playwright browser**
```powershell
playwright install chromium
```
This downloads Chromium into Playwright's own browser cache — no manual
Chrome install needed.

**Step 6 — Run the test mode**
```powershell
python main.py --test
```
Watch the console output. If it reports found businesses/emails/phones
and finishes with a `RUN COMPLETE` summary, everything is wired up
correctly. If it fails at the browser-launch step, re-run Step 5.

**Step 7 — Run a normal job**
```powershell
python main.py
```
Edit `config.yaml` first to set your real keywords/locations/batch size.

**Step 8 — Run headless (for unattended VPS operation)**
```powershell
python main.py --headless
```

**Step 9 — Resume after an interruption**
```powershell
python main.py --resume
```

## Running for long periods on a Windows VPS

- **Task Scheduler**: create a Basic Task that runs
  `venv\Scripts\python.exe C:\lead-scraper\main.py --headless --resume`
  on a schedule (e.g. daily) or at startup, with "Start in" set to the
  project folder. Using `--resume` every time means a scheduled restart
  never redoes finished work.
- **Keeping the VPS awake**: in Windows Power Options, set "Put the
  computer to sleep" to Never for the relevant power plan — a VPS
  normally stays awake by default, but check this if it doesn't.
- **Log monitoring**: `logs/app.log` has one line per business processed
  (keyword, location, company, what was found, status) plus warnings for
  blocked searches or stale selectors. Tail it with:
  ```powershell
  Get-Content logs\app.log -Wait -Tail 50
  ```
- **Restarting after a failure**: just run `python main.py --resume`
  again. Completed keyword/location searches are skipped; businesses
  already saved are matched by domain/phone and merged, not duplicated.
- **Checking the Excel output**: `output/leads.xlsx` is rewritten after
  every single lead, so it always reflects the latest data — safe to open
  and read at any time, even mid-run (Excel will show the last fully
  written version; the writer uses an atomic replace so you'll never see
  a half-written file).
- **Checking the database**: `data/leads.db` is a normal SQLite file —
  inspect it with any SQLite browser (e.g. DB Browser for SQLite) or the
  `sqlite3` CLI: `sqlite3 data/leads.db "SELECT COUNT(*) FROM businesses;"`

No personal computer needs to stay on — this all runs on the VPS itself.

## Security

No passwords, API keys, or credentials are hard-coded or required. `.env`
is provided only as a placeholder for optional future configuration (e.g.
a proxy you control) — nothing in this app reads it by default. Only
publicly accessible business information is ever collected; no private
accounts, authenticated areas, or leaked data are accessed.

## Tests

```bash
pytest
```

Covers: email/phone/Pinterest extraction and validation, URL/phone/name
normalization, config loading and CLI-override merging, SQLite dedup and
merge logic, the Excel writer, and a full `main.run()` integration test
(batching, resume, `--limit`, `require_website`, immediate Excel writes)
with discovery/enrichment/the browser mocked out — all offline, no
network or real browser required. The live Google Maps/Search selectors
in `discovery.py` and `web_search.py` can only be verified by actually
running the tool against the real sites (see the diagnostics note above
if a live run comes back with 0 results).
