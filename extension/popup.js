let scrapedListings = [];
let enrichedLeads = [];
let importedRows = [];
let searchResults = [];

const statusEl = document.getElementById("status");
const scrapeBtn = document.getElementById("scrapeBtn");
const exportBasicBtn = document.getElementById("exportBasicBtn");
const enrichBtn = document.getElementById("enrichBtn");
const exportFullBtn = document.getElementById("exportFullBtn");

const csvInput = document.getElementById("csvInput");
const loadStatusEl = document.getElementById("loadStatus");
const searchBtn = document.getElementById("searchBtn");
const searchStatusEl = document.getElementById("searchStatus");
const exportSearchBtn = document.getElementById("exportSearchBtn");

function setStatus(text) {
  statusEl.textContent = text;
}

function domainOf(website) {
  if (!website) return "";
  try {
    return new URL(website.startsWith("http") ? website : `https://${website}`).host.replace(/^www\./, "").toLowerCase();
  } catch {
    return website.replace(/^www\./, "").toLowerCase();
  }
}

function csvEscape(value) {
  return `"${String(value ?? "").replace(/"/g, '""')}"`;
}

function downloadCsv(csv, filename) {
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  chrome.downloads.download({ url, filename, saveAs: true });
}

// ---- Step 1: scrape ----

scrapeBtn.addEventListener("click", async () => {
  const maxResults = Number(document.getElementById("maxResults").value) || 30;
  setStatus("Scraping current Maps search...");
  scrapeBtn.disabled = true;

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.url || !tab.url.includes("google.com/maps")) {
    setStatus("Open a Google Maps search tab first, then try again.");
    scrapeBtn.disabled = false;
    return;
  }

  chrome.tabs.sendMessage(tab.id, { type: "SCRAPE", maxResults, detailPauseMs: 1200 }, (response) => {
    scrapeBtn.disabled = false;
    if (chrome.runtime.lastError || !response || !response.ok) {
      const reason = chrome.runtime.lastError?.message || response?.error || "unknown error";
      setStatus(`Scrape failed: ${reason}`);
      return;
    }
    scrapedListings = response.listings;
    setStatus(`Scraped ${scrapedListings.length} listings. (feed found: ${response.feedFound}, cards on page: ${response.cardCount})`);
    const hasResults = scrapedListings.length > 0;
    enrichBtn.disabled = !hasResults;
    exportBasicBtn.disabled = !hasResults;
  });
});

exportBasicBtn.addEventListener("click", () => {
  const header = ["Website", "Company Name"];
  const rows = scrapedListings.map((listing) => [domainOf(listing.website), listing.name].map(csvEscape).join(","));
  downloadCsv([header.join(","), ...rows].join("\r\n"), "leads_domain_company.csv");
});

// ---- Advanced: enrich directly ----

enrichBtn.addEventListener("click", () => {
  setStatus(`Enriching ${scrapedListings.length} websites (this can take a minute)...`);
  enrichBtn.disabled = true;

  chrome.runtime.sendMessage({ type: "ENRICH", listings: scrapedListings, pauseMs: 300 }, (response) => {
    if (!response || !response.ok) {
      setStatus("Enrichment failed.");
      enrichBtn.disabled = false;
      return;
    }
    enrichedLeads = response.leads;
    setStatus(`Enriched ${enrichedLeads.length} deduped leads.`);
    exportFullBtn.disabled = enrichedLeads.length === 0;
  });
});

exportFullBtn.addEventListener("click", () => {
  const header = ["Email", "Owner/Founder/CEO Name", "Company Name", "Website", "Pinterest Link", "Phone Number"];
  const rows = enrichedLeads.map((lead) =>
    [lead.email, lead.ownerName, lead.companyName, lead.website, lead.pinterest, lead.phone].map(csvEscape).join(",")
  );
  downloadCsv([header.join(","), ...rows].join("\r\n"), "leads_full.csv");
});

// ---- Step 2: reupload CSV, search Google per row, visit result pages ----

function parseCsv(text) {
  const rows = [];
  let field = "";
  let row = [];
  let inQuotes = false;

  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    if (inQuotes) {
      if (char === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        field += char;
      }
    } else if (char === '"') {
      inQuotes = true;
    } else if (char === ",") {
      row.push(field);
      field = "";
    } else if (char === "\r") {
      // ignore, \n below ends the row
    } else if (char === "\n") {
      row.push(field);
      rows.push(row);
      field = "";
      row = [];
    } else {
      field += char;
    }
  }
  if (field.length > 0 || row.length > 0) {
    row.push(field);
    rows.push(row);
  }
  return rows.filter((r) => r.some((cell) => cell.trim() !== ""));
}

csvInput.addEventListener("change", async () => {
  const file = csvInput.files[0];
  if (!file) return;

  const rows = parseCsv(await file.text());
  if (rows.length < 2) {
    loadStatusEl.textContent = "CSV looks empty.";
    return;
  }

  const header = rows[0].map((h) => h.trim().toLowerCase());
  const websiteIdx = header.findIndex((h) => h.includes("website"));
  const companyIdx = header.findIndex((h) => h.includes("company"));
  if (websiteIdx === -1 || companyIdx === -1) {
    loadStatusEl.textContent = 'CSV needs "Website" and "Company Name" columns.';
    return;
  }

  importedRows = rows
    .slice(1)
    .filter((r) => r.length > Math.max(websiteIdx, companyIdx))
    .map((r) => ({ domain: domainOf(r[websiteIdx]), companyName: r[companyIdx] }))
    .filter((r) => r.domain || r.companyName);

  loadStatusEl.textContent = `Loaded ${importedRows.length} rows.`;
  searchBtn.disabled = importedRows.length === 0;
});

searchBtn.addEventListener("click", () => {
  const queryTemplate = document.getElementById("queryTemplate").value || "{company} {domain}";
  const resultsToVisit = Number(document.getElementById("resultsToVisit").value) || 3;
  searchBtn.disabled = true;
  searchStatusEl.textContent = `Starting search for ${importedRows.length} rows...`;

  chrome.runtime.sendMessage(
    { type: "SEARCH_ENRICH", rows: importedRows, queryTemplate, resultsToVisit, pauseMs: 2500 },
    (response) => {
      searchBtn.disabled = false;
      if (!response || !response.ok) {
        searchStatusEl.textContent = "Search run failed.";
        return;
      }
      searchResults = response.results;
      const foundCount = searchResults.filter((r) => r.email).length;
      searchStatusEl.textContent = `Done. Found an email for ${foundCount}/${searchResults.length} rows.`;
      exportSearchBtn.disabled = searchResults.length === 0;
    }
  );
});

chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "SEARCH_PROGRESS") {
    searchStatusEl.textContent = `Row ${message.index + 1}/${message.total}: ${message.note}`;
  }
});

exportSearchBtn.addEventListener("click", () => {
  const header = ["Email", "Owner/Founder/CEO Name", "Company Name", "Website", "Pinterest Link", "Phone Number"];
  const rows = searchResults.map((r) =>
    [r.email, r.ownerName, r.companyName, r.domain, r.pinterest, ""].map(csvEscape).join(",")
  );
  downloadCsv([header.join(","), ...rows].join("\r\n"), "leads_final.csv");
});

// Restore results from a run that finished (or was still running) after the popup closed.
chrome.storage.local.get(["searchResults"], (data) => {
  if (data.searchResults && data.searchResults.length) {
    searchResults = data.searchResults;
    searchStatusEl.textContent = `Restored ${searchResults.length} result(s) from a previous run.`;
    exportSearchBtn.disabled = false;
  }
});
