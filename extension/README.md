# Furniture Lead Scraper — Chrome Extension

Same idea as the Python CLI in the repo root, packaged as a Chrome extension
you load in Developer mode instead of running from a terminal. It scrapes
whatever Google Maps search you already have open, then checks each
company's own website for a published owner name, email, and Pinterest
link. No paid APIs, nothing installed from the Chrome Web Store.

## Install (Load unpacked)

1. Open `chrome://extensions` in Chrome.
2. Turn on **Developer mode** (top-right toggle).
3. Click **Load unpacked** and select this `extension/` folder.
4. The extension will appear in your toolbar (pin it via the puzzle-piece
   icon for easy access).

Chrome will show a permission warning for "Read and change your data on
all sites" — that's expected. It comes from the `<all_urls>` host
permission, which is what lets step 2 below fetch each company's own
website in the background to look for a published email/owner name
without hitting page-level CORS blocks. It's only used for that.

## Use it

1. Go to Google Maps and run a search, e.g.
   `https://www.google.com/maps/search/Furniture+Store+in+Phoenix,+AZ`
2. Click the extension icon.
3. **1. Scrape this Maps search** — scrolls the results list and pulls
   name/category/address/phone/website from each listing.
4. **2. Enrich websites** — visits each company's own homepage/About/Team/
   Contact pages looking for a published owner name, email, and Pinterest
   link. Fields stay blank when nothing is publicly published — this step
   never guesses or fabricates a contact detail.
5. **3. Export CSV** — downloads `leads.csv` with columns in order:
   `Email | Owner/Founder/CEO Name | Company Name | Website | Pinterest Link | Phone Number`.
   Open it in Excel/Sheets and save as `.xlsx` if you need that format.

Repeat per city/category search (e.g. once for "Furniture Store in
New York City, NY", once for "Modern Furniture in Los Angeles, CA", etc.)
and append each CSV's rows into one sheet to build up the full dataset.

## Limitations (same caveats as the Python version)

- Google's Maps markup changes periodically; if a scrape comes back with 0
  listings, the selectors in `content.js` (`FEED_SELECTOR`, `CARD_SELECTOR`,
  and the detail-panel selectors) likely need updating — inspect the page
  in DevTools to find the current ones.
- Automated Maps scraping isn't covered by Google's Terms of Service. Keep
  result counts modest and expect occasional CAPTCHAs.
- Most independent stores don't publish an owner's name or personal email
  anywhere on their site, so those columns will often be blank — that's
  the tool being honest rather than guessing.
- Use scraped emails for outbound B2B research, not bulk campaigns, without
  checking CAN-SPAM/anti-spam obligations first.
