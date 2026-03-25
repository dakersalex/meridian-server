const SERVER = 'http://localhost:4242';

const BOOKMARKS_PAGES = {
  'economist.com/for-you/bookmarks': { source: 'The Economist', key: 'eco' },
  'ft.com/myft/saved-articles':      { source: 'Financial Times', key: 'ft' },
};

function detectBookmarksPage(url) {
  for (const pattern of Object.keys(BOOKMARKS_PAGES)) {
    if (url.includes(pattern)) return BOOKMARKS_PAGES[pattern];
  }
  return null;
}

function detectSource(url) {
  if (url.includes('ft.com'))        return 'Financial Times';
  if (url.includes('economist.com')) return 'The Economist';
  return 'Unknown';
}

// ── Auto-scroll and extract all bookmarks ──
function scrollAndExtract() {
  return new Promise(resolve => {
    const getLinks = () => {
      const links = [];
      const url = location.href;
      if (url.includes('economist.com')) {
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
    };

    let previousCount = 0;
    let stableRounds = 0;
    const maxStableRounds = 5;
    const scrollInterval = 1200;

    const scroll = setInterval(() => {
      window.scrollBy(0, 600);
      const current = getLinks().length;
      const atBottom = (window.innerHeight + window.scrollY) >= document.body.scrollHeight - 200;

      if (current === previousCount && atBottom) {
        stableRounds++;
        if (stableRounds >= maxStableRounds) {
          clearInterval(scroll);
          window.scrollTo(0, 0);
          resolve(getLinks());
        }
      } else {
        stableRounds = 0;
        previousCount = current;
      }
    }, scrollInterval);
  });
}

// ── Sync bookmarks ──
async function syncBookmarks(source) {
  const btn = document.getElementById('sync-btn');
  const status = document.getElementById('status');
  btn.disabled = true;
  status.textContent = 'Scrolling page to find all articles...';
  status.className = '';

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: scrollAndExtract,
    });

    const articles = results[0].result;
    if (!articles || articles.length === 0) {
      status.textContent = 'No articles found on this page.';
      status.className = 'error';
      btn.disabled = false;
      return;
    }

    status.textContent = `Found ${articles.length} articles, checking...`;

    const listResp = await fetch(SERVER + '/api/articles?limit=2000');
    const listData = await listResp.json();
    const existing = new Set((listData.articles || []).map(a => a.url));

    let added = 0;
    for (const art of articles) {
      if (existing.has(art.url)) continue;
      const id = 'bm_' + Math.abs(art.url.split('').reduce((a, c) => (a << 5) - a + c.charCodeAt(0), 0)).toString(16).slice(0, 12);
      await fetch(SERVER + '/api/articles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id, url: art.url, title: art.title,
          body: '', source, status: 'title_only',
          saved_at: Date.now(), fetched_at: Date.now(), pub_date: '',
        })
      });
      added++;
    }

    status.textContent = added > 0
      ? `✓ Added ${added} new article${added !== 1 ? 's' : ''} to Meridian`
      : '✓ All articles already in Meridian';
    status.className = 'success';

  } catch (err) {
    status.textContent = 'Error: ' + err.message;
    status.className = 'error';
  }

  btn.disabled = false;
}

// ── Clip article ──
async function clipArticle() {
  const btn = document.getElementById('clip-btn');
  const status = document.getElementById('status');
  btn.disabled = true;
  status.textContent = 'Reading page...';
  status.className = '';

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  document.getElementById('page-url').textContent = tab.url;

  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: extractText
    });

    const { title, text, url, pubDate } = results[0].result;
    if (!text || text.length < 200) {
      status.textContent = 'Could not extract text — are you on the article page?';
      status.className = 'error';
      btn.disabled = false;
      return;
    }

    status.textContent = 'Sending to Meridian...';

    const listResp = await fetch(SERVER + '/api/articles?limit=2000');
    const listData = await listResp.json();
    const articles = listData.articles || [];
    const match = articles.find(a => a.url && url.includes(a.url.split('?')[0]));

    if (match) {
      const resp = await fetch(SERVER + '/api/articles/' + match.id, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ body: text, status: 'full_text', pub_date: pubDate })
      });
      if (resp.ok) {
        status.textContent = '✓ Updated "' + match.title.slice(0, 40) + '..."';
        status.className = 'success';
      } else {
        throw new Error('Update failed');
      }
    } else {
      const id = 'clip_' + Date.now();
      const resp = await fetch(SERVER + '/api/articles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id, url, title, body: text,
          source: detectSource(url),
          status: 'full_text',
          saved_at: Date.now(), fetched_at: Date.now(), pub_date: pubDate,
        })
      });
      if (resp.ok) {
        status.textContent = '✓ Saved new article';
        status.className = 'success';
      } else {
        throw new Error('Save failed');
      }
    }
  } catch (err) {
    status.textContent = 'Error: ' + err.message;
    status.className = 'error';
    btn.disabled = false;
  }
}

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
        text = Array.from(paras).map(p => p.innerText.trim()).filter(t => t.length > 30 && !t.startsWith('Your browser does not support')).map(t => t.replace(/^([A-Z]) ([a-z])/, '$1$2')).join('\n\n');
        break;
      }
    }
  }
  let pubDate = '';
  const dateEl = document.querySelector('time, [class*="date"], [class*="Date"]');
  if (dateEl) pubDate = dateEl.getAttribute('datetime') || dateEl.textContent.trim();
  return { url, title, text, pubDate };
}

// ── Auto-clip on load if meridian_autoclip param present ──
chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
  if (tab.url && tab.url.includes('meridian_autoclip=1')) {
    // Wait for page to load then auto-clip
    setTimeout(async () => {
      const status = document.getElementById('status');
      status.textContent = 'Auto-clipping...';
      await clipArticle();
    }, 3000);
  }
});

// ── Init ──
chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
  document.getElementById('page-url').textContent = tab.url;
  const bm = detectBookmarksPage(tab.url);
  if (bm) {
    const syncBtn = document.getElementById('sync-btn');
    const divider = document.getElementById('divider');
    syncBtn.style.display = 'block';
    divider.style.display = 'block';
    syncBtn.addEventListener('click', () => syncBookmarks(bm.source));
  }
});

document.getElementById('clip-btn').addEventListener('click', clipArticle);
