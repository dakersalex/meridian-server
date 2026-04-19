const SERVER = 'http://localhost:4242';
const BODY_FETCH_INTERVAL_MINUTES = 15;

function extractText() {
  const url = location.href;
  const title = document.title;
  const selectors = [
    'div.article__content', 'div[class*="article-body"]', 'div[class*="body-text"]',
    'div[class*="article__body"]', 'div[data-component="paragraph"]',
    'div.body-content', 'article', 'main'
  ];
  let text = '';
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el) {
      const paras = el.querySelectorAll('p');
      if (paras.length > 2) {
        text = Array.from(paras).map(p => p.innerText.trim()).filter(t => t.length > 30).join('\n\n');
        break;
      }
    }
  }
  let pubDate = '';
  const dateEl = document.querySelector('time, [class*="date"], [class*="Date"]');
  if (dateEl) pubDate = dateEl.getAttribute('datetime') || dateEl.textContent.trim();
  return { url: url.split('?')[0], title, text, pubDate };
}

function detectSource(url) {
  if (url.includes('ft.com'))        return 'Financial Times';
  if (url.includes('economist.com')) return 'The Economist';
  if (url.includes('bloomberg.com')) return 'Bloomberg';
  return 'Unknown';
}

// ── Auto-harvest FT cookies when FT saved articles page loads ──
const FT_SAVED_URL = 'ft.com/myft/saved-articles';
const ECONOMIST_SAVED_URL = 'economist.com/for-you/bookmarks';

async function harvestAndSaveCookies(url, pubKey) {
  try {
    // Get all cookies for the domain
    const cookieDomain = url.includes('ft.com') ? 'ft.com' : 'economist.com';
    const allCookies = await chrome.cookies.getAll({});
    const cookies = allCookies.filter(c => c.domain.includes(cookieDomain));
    console.log('Meridian: harvested', cookies.length, 'cookies for', cookieDomain, cookies.map(c=>c.name).join(', '));
    if (!cookies || cookies.length === 0) return;

    // Format as cookie string
    const cookieStr = cookies.map(c => `${c.name}=${c.value}`).join('; ');

    // Send to Meridian server
    const resp = await fetch('http://localhost:4242/api/cookies', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ publication: pubKey, cookies: cookieStr })
    });
    const data = await resp.json();
    if (data.ok) {
      console.log(`Auto-harvested cookies for ${pubKey}`);
    }
  } catch(e) {
    console.error('Cookie harvest error:', e);
  }
}

chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (changeInfo.status !== 'complete') return;
  if (!tab.url) return;

  // Auto-harvest FT cookies
  if (tab.url.includes(FT_SAVED_URL)) {
    await new Promise(r => setTimeout(r, 2000));
    await harvestAndSaveCookies(tab.url, 'ft');
    console.log('FT cookies harvested automatically');
  }

  // Auto-harvest Economist cookies
  if (tab.url.includes(ECONOMIST_SAVED_URL)) {
    await new Promise(r => setTimeout(r, 2000));
    await harvestAndSaveCookies(tab.url, 'eco');
    console.log('Economist cookies harvested automatically');
  }
});

chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (changeInfo.status !== 'complete') return;
  if (!tab.url || !tab.url.includes('meridian_autoclip=1')) return;

  await new Promise(r => setTimeout(r, 2500));

  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId },
      func: extractText
    });

    const { title, text, url, pubDate } = results[0].result;
    if (!text || text.length < 200) {
      console.log('Auto-clip: no text found for', title);
      return;
    }

    // Detect paywall/subscription content and reject
    const paywallPhrases = [
      'save now on essential digital access',
      'subscribe to read',
      'become an ft subscriber',
      'savings apply for your first year',
      'complete digital access to quality ft journalism',
      'subscribe for full access',
      'already a subscriber',
      'to continue reading',
    ];
    const lowerText = text.toLowerCase();
    if (paywallPhrases.some(p => lowerText.includes(p))) {
      console.log('Auto-clip: paywall detected for', title, '— skipping');
      return;
    }

    const listResp = await fetch(SERVER + '/api/articles?limit=2000');
    const listData = await listResp.json();
    const arts = listData.articles || [];
    const cleanUrl = url.split('?')[0];
    const match = arts.find(a => a.url && a.url.split('?')[0] === cleanUrl);

    if (match) {
      await fetch(SERVER + '/api/articles/' + match.id, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ body: text, status: 'full_text', pub_date: pubDate })
      });
      console.log('Auto-clip: updated', title);
    } else {
      const id = 'clip_' + Date.now() + '_' + Math.random().toString(36).slice(2,6);
      await fetch(SERVER + '/api/articles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id, url, title, body: text,
          source: detectSource(url),
          status: 'full_text',
          saved_at: Date.now(),
          fetched_at: Date.now(),
          pub_date: pubDate,
        })
      });
      console.log('Auto-clip: saved new', title);
    }
  } catch(e) {
    console.error('Auto-clip error:', e);
  }
});

// ── Background body fetcher ──────────────────────────────────────────────────
// Periodically checks for title_only articles and fetches their body text
// using the user's logged-in browser session (bypasses paywalls naturally).

async function fetchPendingBodies() {
  try {
    const resp = await fetch(SERVER + '/api/articles/pending-body?limit=5');
    if (!resp.ok) return;
    const data = await resp.json();
    const articles = data.articles || [];
    if (articles.length === 0) {
      console.log('Meridian body-fetch: no pending articles');
      return;
    }
    console.log(`Meridian body-fetch: ${articles.length} articles to process`);

    for (const art of articles) {
      try {
        await fetchBodyForArticle(art);
        // Wait between articles to avoid rate limiting
        await new Promise(r => setTimeout(r, 5000));
      } catch(e) {
        console.error(`Meridian body-fetch error for ${art.title}:`, e);
      }
    }
  } catch(e) {
    console.error('Meridian body-fetch: failed to get pending list:', e);
  }
}

async function fetchBodyForArticle(art) {
  console.log(`Meridian body-fetch: opening ${art.title.substring(0, 50)}...`);

  // Open in background tab
  const tab = await chrome.tabs.create({ url: art.url, active: false });

  // Wait for page to load
  await new Promise(resolve => {
    const listener = (tabId, changeInfo) => {
      if (tabId === tab.id && changeInfo.status === 'complete') {
        chrome.tabs.onUpdated.removeListener(listener);
        resolve();
      }
    };
    chrome.tabs.onUpdated.addListener(listener);
    // Timeout after 20s
    setTimeout(() => {
      chrome.tabs.onUpdated.removeListener(listener);
      resolve();
    }, 20000);
  });

  // Extra wait for JS rendering
  await new Promise(r => setTimeout(r, 3000));

  // Extract text
  const results = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: extractText
  });

  // Close the tab
  try { await chrome.tabs.remove(tab.id); } catch(e) {}

  const { title, text, url, pubDate } = results[0].result;

  if (!text || text.length < 200) {
    console.log(`Meridian body-fetch: insufficient text for ${art.title.substring(0, 40)} (${(text||'').length} chars)`);
    return;
  }

  // Check for paywall content
  const paywallPhrases = [
    'save now on essential digital access',
    'subscribe to read', 'become an ft subscriber',
    'subscribe for full access', 'already a subscriber',
    'to continue reading', 'complete digital access',
  ];
  const lowerText = text.toLowerCase();
  if (paywallPhrases.some(p => lowerText.includes(p))) {
    console.log(`Meridian body-fetch: paywall detected for ${art.title.substring(0, 40)}`);
    return;
  }

  // PATCH the article with real body text
  const patchResp = await fetch(SERVER + '/api/articles/' + art.id, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      body: text,
      status: 'full_text',
      pub_date: pubDate || undefined
    })
  });
  const patchData = await patchResp.json();
  if (patchData.ok) {
    console.log(`Meridian body-fetch: ✅ got body for ${art.title.substring(0, 50)} (${text.length} chars)`);
    // Trigger enrichment for this article
    fetch(SERVER + '/api/enrich/' + art.id, { method: 'POST' }).catch(() => {});
  }
}

// Set up periodic alarm
chrome.alarms.create('fetchBodies', { periodInMinutes: BODY_FETCH_INTERVAL_MINUTES });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'fetchBodies') {
    fetchPendingBodies();
  }
});

// Also run once on extension startup
setTimeout(fetchPendingBodies, 10000);

