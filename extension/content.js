// Scrapes the results feed of the Google Maps search tab this content script
// is injected into. Selectors mirror Google's Maps UI as of writing -- if
// Google changes its markup, these will need updating (inspect the results
// panel in devtools and adjust the constants below). Because this sandbox
// can't reach google.com to verify live selectors, extraction is written to
// degrade gracefully (fall back to a card's own aria-label for the name,
// skip a card that fails to parse) and to report diagnostics back to the
// popup so a bad selector is easy to spot instead of silently returning 0.

const FEED_SELECTOR = 'div[role="feed"]';
const CARD_SELECTOR = `${FEED_SELECTOR} div[role="article"]`;
const NAME_SELECTORS = ['h1.DUwDvf', 'h1[class*="fontHeadline"]', '[role="main"] h1'];
const WEBSITE_SELECTOR = 'a[data-item-id="authority"]';
const PHONE_SELECTOR = 'button[data-item-id^="phone:tel:"]';
const ADDRESS_SELECTOR = 'button[data-item-id="address"]';
const CATEGORY_SELECTOR = 'button[jsaction*="category"]';

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function scrollFeedUntil(targetCount, maxRounds = 40, pauseMs = 1200) {
  const feed = document.querySelector(FEED_SELECTOR);
  if (!feed) return;

  let lastCount = 0;
  let stagnantRounds = 0;
  for (let round = 0; round < maxRounds; round++) {
    if (document.querySelectorAll(CARD_SELECTOR).length >= targetCount) return;
    feed.scrollBy(0, feed.scrollHeight);
    await sleep(pauseMs);
    const newCount = document.querySelectorAll(CARD_SELECTOR).length;
    if (newCount === lastCount) {
      stagnantRounds += 1;
      if (stagnantRounds >= 3) return;
    } else {
      stagnantRounds = 0;
    }
    lastCount = newCount;
  }
}

function firstMatch(selectors) {
  for (const selector of selectors) {
    const el = document.querySelector(selector);
    if (el) return el;
  }
  return null;
}

function textOrEmpty(selector) {
  const el = document.querySelector(selector);
  return el ? el.innerText.trim() : "";
}

function extractOpenDetailPanel(fallbackName) {
  const nameEl = firstMatch(NAME_SELECTORS);
  const name = nameEl ? nameEl.innerText.trim() : fallbackName;
  if (!name) return null;

  let website = "";
  const websiteEl = document.querySelector(WEBSITE_SELECTOR);
  if (websiteEl) website = websiteEl.href || "";

  let phone = "";
  const phoneEl = document.querySelector(PHONE_SELECTOR);
  if (phoneEl) {
    phone = (phoneEl.getAttribute("aria-label") || "").replace("Phone: ", "").trim();
  }

  return {
    name,
    category: textOrEmpty(CATEGORY_SELECTOR),
    address: textOrEmpty(ADDRESS_SELECTOR),
    phone,
    website,
  };
}

async function scrapeListings(maxResults, detailPauseMs) {
  await scrollFeedUntil(maxResults);
  const feedFound = !!document.querySelector(FEED_SELECTOR);
  const cards = Array.from(document.querySelectorAll(CARD_SELECTOR)).slice(0, maxResults);

  const listings = [];
  for (const card of cards) {
    try {
      const fallbackName = (card.getAttribute("aria-label") || "").trim();
      card.click();
      await sleep(detailPauseMs);
      const listing = extractOpenDetailPanel(fallbackName);
      if (listing) listings.push(listing);
    } catch {
      // Skip a card that fails to open/parse rather than aborting the whole scrape.
    }
  }
  return { listings, feedFound, cardCount: cards.length };
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type !== "SCRAPE") return false;

  scrapeListings(message.maxResults ?? 30, message.detailPauseMs ?? 1200)
    .then(({ listings, feedFound, cardCount }) => sendResponse({ ok: true, listings, feedFound, cardCount }))
    .catch((error) => sendResponse({ ok: false, error: String(error) }));

  return true; // keep the message channel open for the async response
});
