// Scrapes the results feed of the Google Maps search tab this content script
// is injected into. Selectors mirror Google's Maps UI as of writing -- if
// Google changes its markup, these will need updating (inspect the results
// panel in devtools and adjust the constants below).

const FEED_SELECTOR = 'div[role="feed"]';
const CARD_SELECTOR = `${FEED_SELECTOR} > div > div[role="article"]`;

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

function textOrEmpty(selector) {
  const el = document.querySelector(selector);
  return el ? el.innerText.trim() : "";
}

function extractOpenDetailPanel() {
  const nameEl = document.querySelector('h1.DUwDvf, h1[class*="fontHeadline"]');
  if (!nameEl) return null;

  let website = "";
  const websiteEl = document.querySelector('a[data-item-id="authority"]');
  if (websiteEl) website = websiteEl.href || "";

  let phone = "";
  const phoneEl = document.querySelector('button[data-item-id^="phone:tel:"]');
  if (phoneEl) {
    phone = (phoneEl.getAttribute("aria-label") || "").replace("Phone: ", "").trim();
  }

  return {
    name: nameEl.innerText.trim(),
    category: textOrEmpty('button[jsaction*="category"]'),
    address: textOrEmpty('button[data-item-id="address"]'),
    phone,
    website,
  };
}

async function scrapeListings(maxResults, detailPauseMs) {
  await scrollFeedUntil(maxResults);
  const cards = Array.from(document.querySelectorAll(CARD_SELECTOR)).slice(0, maxResults);

  const listings = [];
  for (const card of cards) {
    card.click();
    await sleep(detailPauseMs);
    const listing = extractOpenDetailPanel();
    if (listing) listings.push(listing);
  }
  return listings;
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type !== "SCRAPE") return false;

  scrapeListings(message.maxResults ?? 30, message.detailPauseMs ?? 1200)
    .then((listings) => sendResponse({ ok: true, listings }))
    .catch((error) => sendResponse({ ok: false, error: String(error) }));

  return true; // keep the message channel open for the async response
});
