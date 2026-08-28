// Two things happen here, both driven by messages from popup.js:
//
// 1. ENRICH: crawl each scraped company's own website (About/Team/Contact
//    pages) for a published owner name, email, and Pinterest link.
// 2. SEARCH_ENRICH: given a reuploaded list of {domain, companyName} rows
//    and a query template, open a real (background) Google Search tab per
//    row, read the organic result links off the live rendered page, then
//    fetch a few of those pages looking for the same contact details.
//
// Neither path guesses or fabricates a contact detail -- fields stay blank
// when nothing is publicly found. Cross-origin fetches to arbitrary company
// domains only work from here (the extension's background service worker)
// because the "<all_urls>" host permission in manifest.json exempts
// extension fetches from the page-level CORS restrictions a content script
// would otherwise hit.

const TITLE_KEYWORDS = ["founder", "owner", "ceo", "president", "managing director"];
const EMAIL_RE = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/;
const PINTEREST_RE = /https?:\/\/(?:www\.)?pinterest\.[a-z.]+\/[A-Za-z0-9_./-]+/i;
const CANDIDATE_PATHS = ["", "about", "about-us", "team", "our-team", "contact", "contact-us"];

function findOwnerName(html) {
  const titlePattern = TITLE_KEYWORDS.join("|");
  const nameBeforeTitle = new RegExp(`([A-Z][a-z]+(?:\\s[A-Z][a-z]+){1,2})\\s*[,\\-|]\\s*(?:${titlePattern})`, "i");
  const titleBeforeName = new RegExp(`(?:${titlePattern})\\s*[:\\-]\\s*([A-Z][a-z]+(?:\\s[A-Z][a-z]+){1,2})`, "i");

  const flatText = html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");
  const candidateLines = flatText.match(new RegExp(`.{0,60}(?:${titlePattern}).{0,60}`, "gi")) || [];
  for (const line of candidateLines) {
    const match = nameBeforeTitle.exec(line) || titleBeforeName.exec(line);
    if (match) return match[1].trim();
  }
  return "";
}

function extractContactFromHtml(html) {
  const emailMatch = EMAIL_RE.exec(html);
  const pinterestMatch = PINTEREST_RE.exec(html);
  return {
    email: emailMatch ? emailMatch[0] : "",
    pinterest: pinterestMatch ? pinterestMatch[0] : "",
    ownerName: findOwnerName(html),
  };
}

function mergeContact(target, addition) {
  target.email = target.email || addition.email;
  target.pinterest = target.pinterest || addition.pinterest;
  target.ownerName = target.ownerName || addition.ownerName;
  return target;
}

function isContactComplete(contact) {
  return !!(contact.email && contact.pinterest && contact.ownerName);
}

async function fetchText(url) {
  try {
    const response = await fetch(url, { credentials: "omit" });
    if (!response.ok) return "";
    return await response.text();
  } catch {
    return "";
  }
}

function toBaseUrl(website) {
  try {
    const url = new URL(website.startsWith("http") ? website : `https://${website}`);
    return `${url.protocol}//${url.host}/`;
  } catch {
    return "";
  }
}

function domainOf(website) {
  if (!website) return "";
  try {
    return new URL(website.startsWith("http") ? website : `https://${website}`).host.replace(/^www\./, "").toLowerCase();
  } catch {
    return "";
  }
}

async function enrichWebsite(website) {
  const result = { email: "", ownerName: "", pinterest: "" };
  const base = toBaseUrl(website);
  if (!base) return result;

  for (const path of CANDIDATE_PATHS) {
    const html = await fetchText(new URL(path, base).toString());
    if (!html) continue;
    mergeContact(result, extractContactFromHtml(html));
    if (isContactComplete(result)) break;
  }
  return result;
}

// ---- ENRICH: crawl each scraped listing's own website ----

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type !== "ENRICH") return false;

  (async () => {
    const leads = [];
    const seenDomains = new Set();
    const seenPhones = new Set();

    for (const listing of message.listings) {
      const domain = domainOf(listing.website);
      if (!domain && !listing.phone) continue;
      if (domain && seenDomains.has(domain)) continue;
      if (listing.phone && seenPhones.has(listing.phone)) continue;
      if (domain) seenDomains.add(domain);
      if (listing.phone) seenPhones.add(listing.phone);

      const contact = await enrichWebsite(listing.website);
      leads.push({
        email: contact.email,
        ownerName: contact.ownerName,
        companyName: listing.name,
        website: listing.website,
        pinterest: contact.pinterest,
        phone: listing.phone,
      });

      await new Promise((resolve) => setTimeout(resolve, message.pauseMs ?? 300));
    }

    sendResponse({ ok: true, leads });
  })();

  return true;
});

// ---- SEARCH_ENRICH: Google Search each reuploaded row, visit result pages ----

function googleSearchUrl(query) {
  return `https://www.google.com/search?q=${encodeURIComponent(query)}`;
}

function waitForTabComplete(tabId, timeoutMs = 20000) {
  return new Promise((resolve) => {
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      chrome.tabs.onUpdated.removeListener(listener);
      resolve();
    };
    const listener = (updatedTabId, changeInfo) => {
      if (updatedTabId === tabId && changeInfo.status === "complete") finish();
    };
    chrome.tabs.onUpdated.addListener(listener);
    setTimeout(finish, timeoutMs);
  });
}

function extractResultLinksFromTab(tabId) {
  return new Promise((resolve) => {
    chrome.tabs.sendMessage(tabId, { type: "EXTRACT_RESULTS" }, (response) => {
      if (chrome.runtime.lastError || !response || !response.ok) {
        resolve([]);
      } else {
        resolve(response.links);
      }
    });
  });
}

async function searchAndVisit(query, resultsToVisit) {
  let tab;
  try {
    tab = await chrome.tabs.create({ url: googleSearchUrl(query), active: false });
    await waitForTabComplete(tab.id);
    const links = await extractResultLinksFromTab(tab.id);
    return links.slice(0, resultsToVisit);
  } catch {
    return [];
  } finally {
    if (tab) {
      try {
        await chrome.tabs.remove(tab.id);
      } catch {
        // tab may have already closed
      }
    }
  }
}

async function runSearchEnrich(rows, queryTemplate, resultsToVisit, pauseMs, onProgress) {
  const output = [];

  for (let index = 0; index < rows.length; index++) {
    const { domain, companyName } = rows[index];
    const query = queryTemplate.replaceAll("{domain}", domain || "").replaceAll("{company}", companyName || "");
    onProgress(index, rows.length, `Searching: ${query}`);

    const links = await searchAndVisit(query, resultsToVisit);
    const contact = { email: "", ownerName: "", pinterest: "" };

    for (const link of links) {
      onProgress(index, rows.length, `Visiting: ${link}`);
      const html = await fetchText(link);
      if (!html) continue;
      mergeContact(contact, extractContactFromHtml(html));
      if (isContactComplete(contact)) break;
    }

    output.push({ domain, companyName, ...contact });
    await chrome.storage.local.set({ searchResults: output });
    await new Promise((resolve) => setTimeout(resolve, pauseMs));
  }

  return output;
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type !== "SEARCH_ENRICH") return false;

  (async () => {
    const rows = message.rows || [];
    const queryTemplate = message.queryTemplate || "{company} {domain} owner email contact";
    const resultsToVisit = message.resultsToVisit ?? 3;
    const pauseMs = message.pauseMs ?? 2500;

    const results = await runSearchEnrich(rows, queryTemplate, resultsToVisit, pauseMs, (index, total, note) => {
      chrome.storage.local.set({ searchProgress: { index, total, note } });
      chrome.runtime.sendMessage({ type: "SEARCH_PROGRESS", index, total, note }).catch(() => {});
    });

    sendResponse({ ok: true, results });
  })();

  return true;
});
