let scrapedListings = [];
let enrichedLeads = [];

const statusEl = document.getElementById("status");
const scrapeBtn = document.getElementById("scrapeBtn");
const enrichBtn = document.getElementById("enrichBtn");
const exportBtn = document.getElementById("exportBtn");

function setStatus(text) {
  statusEl.textContent = text;
}

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
      setStatus(`Scrape failed: ${reason}\nMake sure the Maps results list is visible and try again.`);
      return;
    }
    scrapedListings = response.listings;
    setStatus(`Scraped ${scrapedListings.length} listings.`);
    enrichBtn.disabled = scrapedListings.length === 0;
  });
});

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
    exportBtn.disabled = enrichedLeads.length === 0;
  });
});

function toCsv(leads) {
  const header = ["Email", "Owner/Founder/CEO Name", "Company Name", "Website", "Pinterest Link", "Phone Number"];
  const escape = (value) => `"${String(value ?? "").replace(/"/g, '""')}"`;
  const rows = leads.map((lead) =>
    [lead.email, lead.ownerName, lead.companyName, lead.website, lead.pinterest, lead.phone].map(escape).join(",")
  );
  return [header.join(","), ...rows].join("\r\n");
}

exportBtn.addEventListener("click", () => {
  const csv = toCsv(enrichedLeads);
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  chrome.downloads.download({ url, filename: "leads.csv", saveAs: true }, () => {
    setStatus(`Downloaded ${enrichedLeads.length} leads as leads.csv`);
  });
});
