#!/usr/bin/env python3
"""
Meridian Scraper Server — v3
Correct URLs and selectors for FT, Economist, Foreign Affairs.
"""

import json, os, sys, time, hashlib, logging, threading, sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    PLAYWRIGHT_OK = True
except ImportError:
    PLAYWRIGHT_OK = False

try:
    from bs4 import BeautifulSoup
    BS4_OK = True
except ImportError:
    BS4_OK = False

BASE_DIR = Path(__file__).parent
DB_PATH  = BASE_DIR / "meridian.db"
LOG_PATH = BASE_DIR / "meridian.log"
CREDS    = BASE_DIR / "credentials.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("meridian")

app = Flask(__name__)
CORS(app)

# ── database ──────────────────────────────────────────────────────────────────
def init_db():
    with sqlite3.connect(DB_PATH) as cx:
        cx.execute("""CREATE TABLE IF NOT EXISTS articles (
            id TEXT PRIMARY KEY, source TEXT NOT NULL, url TEXT,
            title TEXT, body TEXT, summary TEXT, topic TEXT, tags TEXT,
            saved_at INTEGER, fetched_at INTEGER, status TEXT DEFAULT 'pending', pub_date TEXT DEFAULT '')""")
        cx.execute("""CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT,
            started_at INTEGER, finished_at INTEGER,
            articles_found INTEGER DEFAULT 0, articles_new INTEGER DEFAULT 0, error TEXT)""")
        cx.commit()

def article_exists(aid):
    with sqlite3.connect(DB_PATH) as cx:
        return cx.execute("SELECT 1 FROM articles WHERE id=?", (aid,)).fetchone() is not None

def upsert_article(art):
    with sqlite3.connect(DB_PATH) as cx:
        cx.execute("""INSERT OR REPLACE INTO articles
          (id,source,url,title,body,summary,topic,tags,saved_at,fetched_at,status,pub_date)
          VALUES (:id,:source,:url,:title,:body,:summary,:topic,:tags,:saved_at,:fetched_at,:status,:pub_date)""", art)
        cx.commit()

def all_articles(source=None, limit=200):
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        if source:
            rows = cx.execute("SELECT * FROM articles WHERE source=? ORDER BY COALESCE(NULLIF(pub_date,''),datetime(saved_at/1000,'unixepoch')) DESC LIMIT ?", (source, limit)).fetchall()
        else:
            rows = cx.execute("SELECT * FROM articles ORDER BY COALESCE(NULLIF(pub_date,''),datetime(saved_at/1000,'unixepoch')) DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

def load_creds():
    return json.loads(CREDS.read_text()) if CREDS.exists() else {}

def save_creds(data):
    CREDS.write_text(json.dumps(data, indent=2))
    os.chmod(CREDS, 0o600)

def make_id(source, url):
    return hashlib.sha1(f"{source}:{url}".encode()).hexdigest()[:16]

def now_ts():
    return int(time.time() * 1000)

def enrich_article_with_ai(art):
    """Send article text to Claude API for summary, key points and tags.
    Only called for articles with body text. Updates art dict in place."""
    creds = load_creds()
    api_key = creds.get("anthropic_api_key", "")
    if not api_key or api_key == "TEST_VALUE_123":
        log.warning("No API key — skipping AI enrichment")
        return art

    body_text = art.get("body", "")
    if not body_text or len(body_text) < 200:
        log.info(f"Skipping AI enrichment for '{art.get('title','')[:50]}' — body too short")
        return art

    import urllib.request, urllib.error, json as _json
    prompt = f"""You are a research assistant. Analyse this article and respond ONLY with a JSON object (no markdown):
{{
  "summary": "2-3 sentence summary of the main argument",
  "fullSummary": "4-6 paragraph detailed analysis",
  "keyPoints": ["point 1", "point 2", "point 3", "point 4"],
  "tags": ["tag1", "tag2", "tag3"],
  "topic": "pick from: Markets, Economics, Geopolitics, Technology, Politics, Business, Energy, Finance, Society, Science — or invent a new max 2-word topic if none fit",
  "pub_date": "publication date as Month Year e.g. March 2026, or empty string if unknown"
}}

Article title: {art.get('title','')}
Article source: {art.get('source','')}

Article text:
{body_text[:8000]}"""

    payload = _json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = _json.loads(resp.read())
            text = data["content"][0]["text"]
            parsed = _json.loads(text.replace("```json","").replace("```","").strip())
            art["summary"]     = parsed.get("summary", art.get("summary",""))
            art["body"]        = parsed.get("fullSummary", art.get("body",""))
            art["tags"]        = _json.dumps(parsed.get("tags", []))
            art["topic"]       = parsed.get("topic", art.get("topic",""))
            art["pub_date"]    = parsed.get("pub_date", art.get("pub_date",""))
            log.info(f"AI enriched: '{art.get('title','')[:50]}'")
    except Exception as e:
        log.warning(f"AI enrichment failed for '{art.get('title','')[:50]}': {e}")
    return art

def fetch_ft_article_text(page, url):
    """Fetch full text and pub_date of an FT article using logged-in browser page."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(2000)
        soup = BeautifulSoup(page.content(), "html.parser")
        # Extract pub_date from time element or published date
        pub_date = ""
        time_el = soup.select_one("time[datetime], time[data-o-component]")
        if time_el and time_el.get("datetime"):
            pub_date = time_el["datetime"]
        if not pub_date:
            # fallback: look for "Published" text near a date
            for el in soup.select("div[class*='date'], span[class*='date'], div[class*='timestamp']"):
                txt = el.get_text(strip=True)
                if txt:
                    pub_date = txt; break
        # FT article body selectors
        body_el = soup.select_one("div.article__content, div[class*='article-body'], div[class*='body-text']")
        text = ""
        if body_el:
            paragraphs = body_el.find_all("p")
            text = " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30)
        return text, pub_date
    except Exception as e:
        log.warning(f"FT fetch text error for {url}: {e}")
        return "", ""

def fetch_economist_article_text(page, url):
    """Fetch full text and pub_date of an Economist article using logged-in browser page."""
    try:
        # Extract pub_date from URL e.g. /2026/03/24/
        import re
        pub_date = ""
        m = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
        if m:
            pub_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}T00:00:00Z"
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(2000)
        soup = BeautifulSoup(page.content(), "html.parser")
        # Economist uses data-component="paragraph" for article body
        paragraphs = soup.select('p[data-component="paragraph"]')
        if paragraphs:
            return " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30), pub_date
        # Fallback: broader selectors
        body_el = soup.select_one("div[class*='article__body'], div[class*='body__'], article")
        if body_el:
            paragraphs = body_el.find_all("p")
            return " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30), pub_date
        return "", pub_date
    except Exception as e:
        log.warning(f"Economist fetch text error for {url}: {e}")
        return "", ""

@app.route('/newsletters')
def get_newsletters():
    source = request.args.get('source', None)
    limit = int(request.args.get('limit', 20))
    offset = int(request.args.get('offset', 0))
    conn = sqlite3.connect('/Users/alexdakers/meridian-server/meridian.db')
    c = conn.cursor()
    if source:
        rows = c.execute("""
            SELECT id, gmail_id, source, subject, body_html, body_text, received_at
            FROM newsletters WHERE source = ?
            ORDER BY received_at DESC LIMIT ? OFFSET ?
        """, (source, limit, offset)).fetchall()
        total = c.execute('SELECT COUNT(*) FROM newsletters WHERE source=?', (source,)).fetchone()[0]
    else:
        rows = c.execute("""
            SELECT id, gmail_id, source, subject, body_html, body_text, received_at
            FROM newsletters
            ORDER BY received_at DESC LIMIT ? OFFSET ?
        """, (limit, offset)).fetchall()
        total = c.execute('SELECT COUNT(*) FROM newsletters').fetchone()[0]
    conn.close()
    newsletters = []
    for row in rows:
        newsletters.append({
            'id': row[0], 'gmail_id': row[1], 'source': row[2],
            'subject': row[3], 'body_html': row[4],
            'body_text': row[5], 'received_at': row[6]
        })
    return jsonify({'newsletters': newsletters, 'total': total, 'offset': offset})

# ── Scrapers ──────────────────────────────────────────────────────────────────
class FTScraper:
    name = "Financial Times"
    SAVED_URL = "https://www.ft.com/myft/saved-articles/197493b5-7e8e-4f13-8463-3c046200835c"

    def __init__(self, email="", password=""):
        pass

    def scrape(self):
        if not PLAYWRIGHT_OK: raise RuntimeError("playwright not installed")
        profile_dir = BASE_DIR / "ft_profile"
        profile_dir.mkdir(exist_ok=True)
        articles = []
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                str(profile_dir), headless=False,
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                args=["--disable-blink-features=AutomationControlled"])
            page = browser.new_page()
            try:
                log.info("FT: opening saved articles")
                page.goto(self.SAVED_URL, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(4000)
                if "login" in page.url or "signin" in page.url:
                    log.info("FT: login required — waiting 90s")
                    page.wait_for_timeout(90000)
                    page.goto(self.SAVED_URL, wait_until="domcontentloaded", timeout=40000)
                    page.wait_for_timeout(4000)
                soup = BeautifulSoup(page.content(), "html.parser")
                cards = soup.select("div.o-teaser, li.o-teaser, article")
                log.info(f"FT: found {len(cards)} cards")
                JUNK_PREFIXES = ("FT quiz:", "Letter:", "FTAV's further reading", "FT News Briefing", "Correction:", "The best books of the week")
                JUNK_SUBSTRINGS = (" live:", " as it happened", "live blog", "htsi stories", "how to spend it")
                found_existing = False
                for card in cards:
                    if found_existing: break
                    a = card.select_one("a[href*='/content/']")
                    if not a: continue
                    url = "https://www.ft.com" + a["href"] if a["href"].startswith("/") else a["href"]
                    url = url.split("?")[0]
                    title_el = card.select_one(".o-teaser__heading, h3, h2")
                    title = title_el.get_text(strip=True) if title_el else a.get_text(strip=True)
                    if not title or len(title) < 5: continue
                    if any(title.startswith(p) for p in JUNK_PREFIXES): continue
                    if any(s in title.lower() for s in JUNK_SUBSTRINGS): continue
                    art_id = make_id(self.name, url)
                    if article_exists(art_id):
                        log.info("FT: hit existing article, stopping")
                        found_existing = True; break
                    cat_el = card.select_one(".o-teaser__tag, .o-teaser__concept")
                    category = cat_el.get_text(strip=True) if cat_el else ""
                    articles.append({"id":art_id,"source":self.name,"url":url,"title":title,"body":"","summary":"","topic":category,"tags":"[]","saved_at":now_ts(),"fetched_at":now_ts(),"status":"fetched","pub_date":""})
                    log.info(f"FT: scraped '{title[:60]}'")
                log.info(f"FT: total {len(articles)} articles scraped")
                new_arts = [a for a in articles if not article_exists(a["id"])]
                log.info(f"FT: {len(new_arts)} new articles to enrich")
                for art in new_arts:
                    if not art.get("url"): continue
                    log.info(f"FT: fetching full text for '{art['title'][:50]}'")
                    text, pub_date = fetch_ft_article_text(page, art["url"])
                    if pub_date:
                        art["pub_date"] = pub_date
                    if text:
                        art["body"] = text
                        enrich_article_with_ai(art)
                    else:
                        art["status"] = "title_only"
            except Exception as e: log.error(f"FT error: {e}", exc_info=True)
            finally: browser.close()
        return articles


class EconomistScraper:
    name = "The Economist"
    SAVED_URL = "https://www.economist.com/for-you/bookmarks"

    def __init__(self, email="", password=""):
        pass

    def scrape(self):
        if not PLAYWRIGHT_OK: raise RuntimeError("playwright not installed")
        articles = []
        profile_dir = BASE_DIR / "economist_profile"
        profile_dir.mkdir(exist_ok=True)
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                str(profile_dir), headless=False,
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                args=["--disable-blink-features=AutomationControlled"])
            page = browser.new_page()
            try:
                log.info("Economist: opening bookmarks")
                page.goto(self.SAVED_URL, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(3000)
                # Click Load more until we hit existing articles
                found_existing = False
                for _ in range(20):
                    if found_existing: break
                    try:
                        # Use Playwright selector for Load more button
                        btn = page.query_selector("button[data-test-id='load-more']") or                               page.query_selector("button:has-text('Load more')")
                        if not btn: break
                        btn.click()
                        page.wait_for_timeout(2000)
                        soup = BeautifulSoup(page.content(), "html.parser")
                        for a in soup.select("a[href*='/20']"):
                            url = "https://www.economist.com" + a["href"] if a["href"].startswith("/") else a["href"]
                            art_id = make_id(self.name, url.split("?")[0])
                            if article_exists(art_id):
                                log.info("Economist: found existing article after Load more, stopping")
                                found_existing = True; break
                        log.info("Economist: clicked Load more")
                    except Exception as _e:
                        log.warning(f"Economist: Load more error: {_e}"); break
                soup = BeautifulSoup(page.content(), "html.parser")
                links = soup.select("a[href*='/20']")
                log.info(f"Economist: found {len(links)} article links")
                seen_urls = set()
                for a in links:
                    if found_existing: break
                    url = "https://www.economist.com" + a["href"] if a["href"].startswith("/") else a["href"]
                    url = url.split("?")[0]
                    if url in seen_urls: continue
                    seen_urls.add(url)
                    title = a.get_text(strip=True)
                    if not title or len(title) < 5: continue
                    art_id = make_id(self.name, url)
                    if article_exists(art_id):
                        log.info("Economist: hit existing article, stopping")
                        found_existing = True; break
                    articles.append({"id":art_id,"source":self.name,"url":url,"title":title,"body":"","summary":"","topic":"","tags":"[]","saved_at":now_ts(),"fetched_at":now_ts(),"status":"fetched","pub_date":""})
                    log.info(f"Economist: scraped '{title[:60]}'")
                log.info(f"Economist: total {len(articles)} articles scraped")
                # full text + AI enrichment for new articles
                new_arts = [a for a in articles if not article_exists(a["id"])]
                log.info(f"Economist: {len(new_arts)} new articles to enrich")
                for art in new_arts:
                    if not art.get("url"): continue
                    log.info(f"Economist: fetching full text for '{art['title'][:50]}'")
                    text, pub_date = fetch_economist_article_text(page, art["url"])
                    if pub_date:
                        art["pub_date"] = pub_date
                    if text:
                        art["body"] = text
                        enrich_article_with_ai(art)
                    else:
                        log.info(f"Economist: no text extracted for '{art['title'][:50]}'")
                # clip any previously fetched articles missing full text
                import sqlite3 as _sq
                _cx = _sq.connect(DB_PATH)
                pending = _cx.execute(
                    "SELECT id, url, title FROM articles WHERE source='The Economist' AND status='fetched' AND url!=''").fetchall()
                _cx.close()
                if pending:
                    log.info(f"Economist: {len(pending)} previously fetched articles to clip")
                for pid, purl, ptitle in (pending or []):
                    try:
                        text, pub_date = fetch_economist_article_text(page, purl)
                        if text:
                            art = {"id": pid, "source": "The Economist", "url": purl,
                                   "title": ptitle, "body": text, "summary": "", "topic": "",
                                   "tags": "[]", "status": "fetched", "pub_date": pub_date or ""}
                            enrich_article_with_ai(art)
                            log.info(f"Economist: clipped existing '{ptitle[:50]}'")
                        else:
                            log.info(f"Economist: no text for existing '{ptitle[:50]}'")
                    except Exception as _e:
                        log.warning(f"Economist: clip error for '{ptitle[:50]}': {_e}")
            except Exception as e: log.error(f"Economist error: {e}", exc_info=True)
            finally: browser.close()
        return articles


class ForeignAffairsScraper:
    name = "Foreign Affairs"
    SAVED_URL = "https://www.foreignaffairs.com/my-foreign-affairs/saved-articles"

    def __init__(self, email="", password=""):
        pass

    def scrape(self):
        if not PLAYWRIGHT_OK: raise RuntimeError("playwright not installed")
        profile_dir = BASE_DIR / "fa_profile"
        profile_dir.mkdir(exist_ok=True)
        articles = []
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                str(profile_dir), headless=False,
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                args=["--disable-blink-features=AutomationControlled"])
            page = browser.new_page()
            try:
                log.info("FA: opening saved articles")
                page.goto(self.SAVED_URL, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(4000)
                if "sign-in" in page.url or "login" in page.url:
                    log.info("FA: login required — waiting 120s")
                    page.wait_for_timeout(120000)
                    page.goto(self.SAVED_URL, wait_until="domcontentloaded", timeout=40000)
                    page.wait_for_timeout(4000)
                soup = BeautifulSoup(page.content(), "html.parser")
                cards = soup.select("h3.body-m, div.article-preview, li.saved-article")
                log.info(f"FA: found {len(cards)} cards")
                found_existing = False
                for card in cards:
                    if found_existing: break
                    a = card if card.name == "a" else card.select_one("a[href*='foreignaffairs.com']")
                    if not a:
                        a = card.find_parent("a") or card.select_one("a")
                    if not a: continue
                    href = a.get("href", "")
                    if not href: continue
                    url = "https://www.foreignaffairs.com" + href if href.startswith("/") else href
                    url = url.split("?")[0]
                    title = card.get_text(strip=True) if card.name != "a" else card.get_text(strip=True)
                    if not title or len(title) < 5: continue
                    art_id = make_id(self.name, url)
                    if article_exists(art_id):
                        log.info("FA: hit existing article, stopping")
                        found_existing = True; break
                    articles.append({"id":art_id,"source":self.name,"url":url,"title":title,"body":"","summary":"","topic":"","tags":"[]","saved_at":now_ts(),"fetched_at":now_ts(),"status":"fetched","pub_date":""})
                    log.info(f"FA: scraped '{title[:60]}'")
                log.info(f"FA: total {len(articles)} articles scraped")
                new_arts = [a for a in articles if not article_exists(a["id"])]
                log.info(f"FA: {len(new_arts)} new articles to enrich")
                for art in new_arts:
                    if not art.get("url"): continue
                    log.info(f"FA: fetching full text for '{art['title'][:50]}'")
                    text, pub_date = fetch_fa_article_text(page, art["url"])
                    if pub_date:
                        art["pub_date"] = pub_date
                    if text:
                        art["body"] = text
                        enrich_article_with_ai(art)
                    else:
                        log.info(f"FA: no text for '{art['title'][:50]}'")
            except Exception as e: log.error(f"FA error: {e}", exc_info=True)
            finally: browser.close()
        return articles


SCRAPERS = {"ft": FTScraper, "economist": EconomistScraper, "fa": ForeignAffairsScraper}

# ── Sync state ────────────────────────────────────────────────────────────────
sync_status = {}

def run_sync(source_key):
    global sync_status
    if source_key not in SCRAPERS:
        raise ValueError(f"Unknown source: {source_key}")
    sync_status[source_key] = {"running": True, "last_run": None, "last_error": None, "articles_found": 0, "articles_new": 0}
    found = new = 0
    try:
        scraper = SCRAPERS[source_key]()
        articles = scraper.scrape()
        found = len(articles)
        for art in articles:
            if not article_exists(art["id"]):
                upsert_article(art)
                new += 1
        log.info(f"{source_key}: sync done — {found} found, {new} new")
        sync_status[source_key] = {"running":False,"last_run":datetime.now().isoformat(timespec="seconds"),"last_error":None,"articles_found":found,"articles_new":new}
    except Exception as e:
        log.error(f"{source_key}: sync error: {e}", exc_info=True)
        sync_status[source_key] = {"running":False,"last_run":datetime.now().isoformat(timespec="seconds"),"last_error":str(e),"articles_found":found,"articles_new":new}


# ── Flask routes ──────────────────────────────────────────────────────────────
@app.route("/api/health")
def health():
    return jsonify({"ok": True, "version": "3.0.0"})

@app.route("/api/articles")
def get_articles():
    source = request.args.get("source")
    limit  = int(request.args.get("limit", 200))
    rows   = all_articles(source, limit)
    arts   = []
    for r in rows:
        a = dict(r)
        try: a["tags"] = json.loads(a.get("tags") or "[]")
        except: a["tags"] = []
        arts.append(a)
    return jsonify({"articles": arts, "total": len(arts)})

@app.route("/api/articles/<aid>", methods=["DELETE"])
def delete_article(aid):
    with sqlite3.connect(DB_PATH) as cx:
        cx.execute("DELETE FROM articles WHERE id=?", (aid,))
    return jsonify({"ok": True})

@app.route("/api/articles/<aid>", methods=["PATCH"])
def update_article(aid):
    body = request.json or {}
    cx = sqlite3.connect(DB_PATH)
    for key in ["body", "summary", "topic", "tags", "status", "pub_date"]:
        if key in body:
            cx.execute(f"UPDATE articles SET {key}=? WHERE id=?", (body[key], aid))
    cx.commit()
    cx.close()
    return jsonify({"ok": True})

@app.route("/api/articles", methods=["POST"])
def add_article():
    body = request.json or {}
    url   = body.get("url", "")
    title = body.get("title", "")
    source = body.get("source", "Manual")
    art_id = make_id(source, url)
    art = {
        "id": art_id, "source": source, "url": url, "title": title,
        "body": body.get("body",""), "summary": body.get("summary",""),
        "topic": body.get("topic",""), "tags": body.get("tags","[]"),
        "saved_at": now_ts(), "fetched_at": now_ts(),
        "status": body.get("status","fetched"),
        "pub_date": body.get("pub_date",""),
    }
    upsert_article(art)
    return jsonify({"ok": True, "id": art_id})

@app.route("/api/sync", methods=["POST"])
def sync_all():
    body = request.json or {}
    sources = body.get("sources", list(SCRAPERS.keys()))
    started = []
    for src in sources:
        if src in SCRAPERS and not sync_status.get(src, {}).get("running"):
            threading.Thread(target=run_sync, args=(src,), daemon=True).start()
            started.append(src)
    return jsonify({"ok": True, "started": started})

@app.route("/api/sync/<source>", methods=["POST"])
def sync_source(source):
    if source not in SCRAPERS:
        return jsonify({"ok": False, "error": "Unknown source"}), 404
    if sync_status.get(source, {}).get("running"):
        return jsonify({"ok": False, "error": "Already running"}), 409
    threading.Thread(target=run_sync, args=(source,), daemon=True).start()
    return jsonify({"ok": True, "started": source})

@app.route("/api/sync/status")
def sync_status_route():
    return jsonify(sync_status)

@app.route("/api/enrich/<aid>", methods=["POST"])
def enrich_article(aid):
    with sqlite3.connect(DB_PATH) as cx:
        row = cx.execute("SELECT * FROM articles WHERE id=?", (aid,)).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "Not found"}), 404
    art = dict(zip([d[0] for d in cx.description], row))
    enrich_article_with_ai(art)
    return jsonify({"ok": True})

@app.route("/api/claude", methods=["POST"])
def claude_proxy():
    body = request.json or {}
    creds = load_creds()
    api_key = creds.get("anthropic_api_key","")
    if not api_key:
        return jsonify({"error": "No API key"}), 500
    import urllib.request
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode(),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return jsonify(json.loads(resp.read()))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/cookies", methods=["GET"])
def get_cookies():
    try:
        with open(BASE_DIR / "cookies.json") as f:
            return jsonify(json.load(f))
    except:
        return jsonify({})

@app.route("/api/cookies", methods=["POST"])
def save_cookies():
    data = request.json or {}
    with open(BASE_DIR / "cookies.json", "w") as f:
        json.dump(data, f, indent=2)
    return jsonify({"ok": True})

def scheduler_loop(interval_hours):
    while True:
        time.sleep(interval_hours * 3600)
        now = datetime.now().hour
        if 1 <= now < 6:
            log.info("Scheduler: quiet hours, skipping")
            continue
        log.info("Scheduler: triggering auto-sync")
        for src in SCRAPERS:
            if not sync_status.get(src, {}).get("running"):
                threading.Thread(target=run_sync, args=(src,), daemon=True).start()
        # Also sync newsletters
        import subprocess
        subprocess.Popen(["python3", str(BASE_DIR / "newsletter_sync.py")])
        log.info("Scheduler: triggered newsletter sync")

@app.route("/api/newsletters/sync", methods=["POST"])
def sync_newsletters_route():
    import subprocess
    threading.Thread(
        target=lambda: subprocess.run(["python3", str(BASE_DIR / "newsletter_sync.py")]),
        daemon=True
    ).start()
    return jsonify({"ok": True, "started": True})

if __name__ == "__main__":
    init_db()
    interval = float(os.environ.get("SYNC_INTERVAL_HOURS","6"))
    threading.Thread(target=scheduler_loop, args=(interval,), daemon=True).start()
    log.info(f"Scheduler started — auto-sync every {interval}h")
    log.info("Meridian server starting on http://localhost:4242")
    app.run(host="127.0.0.1", port=4242, debug=False)
