# Furniture Lead Scraper — Chrome Extension

Load-unpacked Chrome extension, no paid APIs, no terminal. Two steps:

**Step 1 — Scrape Maps.** Scrapes whatever Google Maps search you already
have open and exports a simple 2-column CSV: `Website` (domain only) and
`Company Name`. Edit that CSV by hand if you want (drop rows, fix a domain,
whatever) before moving to Step 2.

**Step 2 — Find emails via Google Search.** Reupload that CSV. For each
row, the extension opens a background Google Search tab using a query
template you control (e.g. `{company} {domain} owner email contact`),
reads the organic result links off the real rendered results page, then
visits a few of those pages looking for a published email, owner name, and
Pinterest link. Exports a final 6-column CSV.

An "Advanced" section under Step 1 keeps the original one-click flow
(enrich straight from each company's own site, skipping Google Search) if
you don't need Step 2 at all.

## Install (Load unpacked)

1. Open `chrome://extensions` in Chrome.
2. Turn on **Developer mode** (top-right toggle).
3. Click **Load unpacked** and select this `extension/` folder.
4. Pin the icon via the puzzle-piece button in the toolbar.

Chrome will show a permission warning for "Read and change your data on
all sites" plus tab access — expected. `<all_urls>` is what lets the
background script fetch arbitrary company websites and Google Search
result pages without hitting page-level CORS blocks; `tabs` is what lets
it open/close the background search tabs in Step 2.

## Use it

### Step 1
1. Go to Google Maps and run a search, e.g.
   `https://www.google.com/maps/search/Furniture+Store+in+Phoenix,+AZ`
2. Click the extension icon.
3. **Scrape this Maps search.** The status line shows a diagnostic —
   `(feed found: true/false, cards on page: N)` — so if it comes back with
   0 listings you can tell whether the results panel wasn't found at all
   or was found but every card failed to parse. If either looks wrong,
   Google likely changed its markup; open devtools on the Maps page,
   inspect the results list, and update the selectors at the top of
   `content.js` (`FEED_SELECTOR`, `CARD_SELECTOR`, `NAME_SELECTORS`, etc).
4. **Export Website + Company CSV** — downloads `leads_domain_company.csv`.

Repeat per city/category search and combine the CSVs into one sheet to
build up the full dataset.

### Step 2
1. Under "Step 2", **Reupload CSV** and pick the file from Step 1 (or your
   edited version of it — it just needs "Website" and "Company Name"
   columns, matched case-insensitively).
2. Set your **search query template**. `{domain}` and `{company}` get
   substituted per row — write whatever query you'd normally type into
   Google, e.g.:
   - `"{company}" owner OR founder OR CEO`
   - `site:{domain} "email" OR "contact"`
   - `{company} {domain} email`
3. Set **pages to visit per search** (default 3 — how many of the top
   result links to open and scan per row).
4. **Run Google Search + Visit Pages.** This takes a while for large
   lists (each row opens a real background tab, waits for it to load,
   reads the results, closes it, then fetches a few pages) — the status
   line shows live progress. Results are saved as they come in
   (`chrome.storage.local`), so if the popup closes or Chrome's background
   service worker restarts mid-run, whatever was completed so far is not
   lost — reopen the popup to see it and continue with the export.
5. **Export Final CSV** — `leads_final.csv` with columns:
   `Email | Owner/Founder/CEO Name | Company Name | Website | Pinterest Link | Phone Number`
   (Phone Number is blank in this path, since the reuploaded CSV only
   carries Website + Company Name.)

## Limitations

- Google's Maps and Search markup change periodically; selector fixes for
  `content.js` and `search_content.js` may be needed over time — see the
  diagnostic note above for Maps specifically.
- Automated Maps/Search scraping isn't covered by Google's Terms of
  Service. Keep volumes modest and expect occasional CAPTCHAs — if Google
  shows one in a background search tab, that row will just come back with
  no links found.
- Most independent stores don't publish an owner's name or personal email
  anywhere findable, so blank fields are expected, not a bug — this tool
  never guesses or fabricates a contact detail.
- Use scraped emails for outbound B2B research, not bulk campaigns,
  without checking CAN-SPAM/anti-spam obligations first.
