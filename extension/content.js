// Content script - runs in page context with full DOM access
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === 'getLinks') {
    sendResponse({ links: extractLinks() });
  }
  if (msg.action === 'ftHasNext') {
    const links = Array.from(document.querySelectorAll('a'));
    sendResponse({ hasNext: links.some(a => a.textContent.trim() === 'Next page') });
  }
  if (msg.action === 'ftClickNext') {
    const links = Array.from(document.querySelectorAll('a'));
    const next = links.find(a => a.textContent.trim() === 'Next page');
    if (next) { next.click(); sendResponse({ ok: true }); }
    else sendResponse({ ok: false });
  }
  return true;
});

function extractLinks() {
  const url = location.href;
  const links = [];

  if (url.includes('ft.com')) {
    const seenIds = new Set();
    document.querySelectorAll('[data-content-id]').forEach(el => {
      const id = el.getAttribute('data-content-id');
      if (seenIds.has(id)) return;
      seenIds.add(id);
      const articleLink = document.querySelector(`a[href*="${id}"]`);
      if (articleLink && articleLink.textContent.trim().length > 10) {
        links.push({ url: articleLink.href.split('?')[0], title: articleLink.textContent.trim() });
      }
    });
  } else if (url.includes('bloomberg.com')) {
    document.querySelectorAll('a[href]').forEach(a => {
      const href = a.href;
      const title = a.textContent.trim();
      if ((href.includes('/news/articles/') || href.includes('/opinion/')) && title.length > 20) {
        links.push({ url: href, title });
      }
    });
  } else if (url.includes('economist.com')) {
    document.querySelectorAll('a[href]').forEach(a => {
      const href = a.href;
      const title = a.textContent.trim();
      if (href.includes('/20') && title.length > 20 && !href.includes('/for-you')) {
        links.push({ url: href, title });
      }
    });
  }

  const seen = new Set();
  return links.filter(l => { if (seen.has(l.url)) return false; seen.add(l.url); return true; });
}
