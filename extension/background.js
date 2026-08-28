// Enriches scraped listings by crawling each company's own website for a
// published owner name, email, and Pinterest link. Never guesses or
// fabricates a contact detail -- fields stay blank when nothing is
// publicly published on the site.
//
// Cross-origin fetches to arbitrary company domains only work from here
// (the extension's background service worker) because the "<all_urls>"
// host permission in manifest.json exempts extension fetches from the
// page-level CORS restrictions a content script would otherwise hit.

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

async function enrichWebsite(website) {
  const result = { email: "", ownerName: "", pinterest: "" };
  const base = toBaseUrl(website);
  if (!base) return result;

  for (const path of CANDIDATE_PATHS) {
    const html = await fetchText(new URL(path, base).toString());
    if (!html) continue;

    if (!result.email) {
      const match = EMAIL_RE.exec(html);
      if (match) result.email = match[0];
    }
    if (!result.pinterest) {
      const match = PINTEREST_RE.exec(html);
      if (match) result.pinterest = match[0];
    }
    if (!result.ownerName) {
      result.ownerName = findOwnerName(html);
    }
    if (result.email && result.pinterest && result.ownerName) break;
  }
  return result;
}

function domainOf(website) {
  if (!website) return "";
  try {
    return new URL(website.startsWith("http") ? website : `https://${website}`).host.replace(/^www\./, "").toLowerCase();
  } catch {
    return "";
  }
}

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
