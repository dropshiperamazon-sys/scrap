// Extracts organic result links from a live Google Search results page.
// Runs in the real rendered page (opened by background.js), so it sees
// exactly what a normal user browsing to that search would see.

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type !== "EXTRACT_RESULTS") return false;

  const links = Array.from(document.querySelectorAll('a[href^="http"]'))
    .map((a) => a.href)
    .filter((href) => !/google\.com|googleusercontent\.com|gstatic\.com/i.test(href));

  sendResponse({ ok: true, links: Array.from(new Set(links)) });
  return true;
});
