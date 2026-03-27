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
            saved_at INTEGER, fetched_at INTEGER, status TEXT DEFAULT 'pending', pub_date TEXT DEFAULT '',
            auto_saved INTEGER DEFAULT 0)""")
        art_cols = [r[1] for r in cx.execute("PRAGMA table_info(articles)").fetchall()]
        if 'auto_saved' not in art_cols:
            cx.execute("ALTER TABLE articles ADD COLUMN auto_saved INTEGER DEFAULT 0")
        cx.execute("""CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT,
            started_at INTEGER, finished_at INTEGER,
            articles_found INTEGER DEFAULT 0, articles_new INTEGER DEFAULT 0, error TEXT)""")
        cx.execute("""CREATE TABLE IF NOT EXISTS suggested_articles (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, url TEXT, source TEXT, snapshot_date TEXT, score INTEGER DEFAULT 0, reason TEXT DEFAULT '', added_at INTEGER, status TEXT DEFAULT 'new', reviewed_at INTEGER DEFAULT NULL)""")
        existing_cols = [r[1] for r in cx.execute("PRAGMA table_info(suggested_articles)").fetchall()]
        if 'status' not in existing_cols:
            cx.execute("ALTER TABLE suggested_articles ADD COLUMN status TEXT DEFAULT 'new'")
        if 'reviewed_at' not in existing_cols:
            cx.execute("ALTER TABLE suggested_articles ADD COLUMN reviewed_at INTEGER DEFAULT NULL")
        if 'pub_date' not in existing_cols:
            cx.execute("ALTER TABLE suggested_articles ADD COLUMN pub_date TEXT DEFAULT ''")
        if 'preview' not in existing_cols:
            cx.execute("ALTER TABLE suggested_articles ADD COLUMN preview TEXT DEFAULT ''")
        cx.execute("""CREATE TABLE IF NOT EXISTS agent_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id TEXT, title TEXT, url TEXT,
            score INTEGER, reason TEXT, saved_at INTEGER)""")
        cx.execute("""CREATE TABLE IF NOT EXISTS agent_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topics TEXT, tags TEXT, title TEXT, url TEXT,
            dismissed_at INTEGER)""")
        cx.execute("""CREATE TABLE IF NOT EXISTS newsletters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gmail_id TEXT,
            source TEXT,
            subject TEXT,
            body_html TEXT,
            body_text TEXT,
            received_at TEXT)""")
        cx.execute("""CREATE TABLE IF NOT EXISTS interviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT DEFAULT '',
            source TEXT DEFAULT '',
            published_date TEXT DEFAULT '',
            added_date INTEGER,
            duration_seconds INTEGER DEFAULT 0,
            transcript TEXT DEFAULT '',
            summary TEXT DEFAULT '',
            speaker_bio TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            thumbnail_url TEXT DEFAULT '')""")
        # Add speaker_bio if missing from existing DBs
        existing_iv_cols = [r[1] for r in cx.execute("PRAGMA table_info(interviews)").fetchall()]
        if 'speaker_bio' not in existing_iv_cols:
            cx.execute("ALTER TABLE interviews ADD COLUMN speaker_bio TEXT DEFAULT ''")
        cx.commit()

def article_exists(aid):
    with sqlite3.connect(DB_PATH) as cx:
        return cx.execute("SELECT 1 FROM articles WHERE id=?", (aid,)).fetchone() is not None

def upsert_article(art):
    with sqlite3.connect(DB_PATH) as cx:
        cx.execute("""INSERT OR REPLACE INTO articles
          (id,source,url,title,body,summary,topic,tags,saved_at,fetched_at,status,pub_date,auto_saved)
          VALUES (:id,:source,:url,:title,:body,:summary,:topic,:tags,:saved_at,:fetched_at,:status,:pub_date,:auto_saved)""",
          {**art, "auto_saved": art.get("auto_saved", 0)})
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
            art["status"] = "full_text"
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
    conn = sqlite3.connect(DB_PATH)
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
                str(profile_dir), headless=True,
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
                str(profile_dir), headless=True,
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
                str(profile_dir), headless=True,
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                args=["--disable-blink-features=AutomationControlled"])
            page = browser.new_page()
            try:
                log.info("FA: opening saved articles")
                page.goto(self.SAVED_URL, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(4000)
                if "sign-in" in page.url or "login" in page.url:
                    creds = load_creds()
                    fa_creds = creds.get("fa", {})
                    fa_email = fa_creds.get("email", os.environ.get("FA_EMAIL", ""))
                    fa_pass = fa_creds.get("password", os.environ.get("FA_PASSWORD", ""))
                    if fa_email and fa_pass:
                        log.info("FA: login required — attempting auto-login")
                        page.goto("https://www.foreignaffairs.com/login", wait_until="domcontentloaded", timeout=30000)
                        page.wait_for_load_state("domcontentloaded", timeout=15000)
                        email_selectors = ['input[type="email"]', '#email', '#user_email', 'input[name="email"]', 'input[placeholder*="email" i]']
                        password_selectors = ['input[type="password"]', '#password', '#user_password', 'input[name="password"]']
                        email_filled = False
                        for sel in email_selectors:
                            try:
                                loc = page.locator(sel).first
                                if loc.is_visible(timeout=2000):
                                    loc.fill(fa_email)
                                    email_filled = True
                                    log.info(f"FA: filled email with selector '{sel}'")
                                    break
                            except Exception:
                                continue
                        pass_filled = False
                        pass_loc = None
                        for sel in password_selectors:
                            try:
                                loc = page.locator(sel).first
                                if loc.is_visible(timeout=2000):
                                    loc.fill(fa_pass)
                                    pass_filled = True
                                    pass_loc = loc
                                    log.info(f"FA: filled password with selector '{sel}'")
                                    break
                            except Exception:
                                continue
                        if not email_filled or not pass_filled:
                            log.warning(f"FA: could not find form fields (email={email_filled}, pass={pass_filled})")
                        import re
                        submitted = False
                        for submit_attempt, submit_fn in [
                            ("form[action] button[type=submit]", lambda: page.locator('form[action*="login"] button[type="submit"]').click()),
                            ("button with login text", lambda: page.locator('button[type="submit"]').filter(has_text=re.compile(r'sign.?in|log.?in|submit', re.I)).first.click()),
                            ("Enter on password field", lambda: pass_loc.press("Enter") if pass_loc else None),
                        ]:
                            try:
                                submit_fn()
                                submitted = True
                                log.info(f"FA: submitted login via '{submit_attempt}'")
                                break
                            except Exception:
                                continue
                        if not submitted:
                            log.warning("FA: could not find submit button")
                        try:
                            page.wait_for_url(lambda u: "login" not in u and "sign-in" not in u, timeout=30000)
                            log.info("FA: auto-login successful")
                        except PWTimeout:
                            log.warning("FA: auto-login may have failed — proceeding anyway")
                    else:
                        log.warning("FA: login required but no fa credentials in credentials.json — waiting 120s")
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
        cx.row_factory = sqlite3.Row
        row = cx.execute("SELECT * FROM articles WHERE id=?", (aid,)).fetchone()
        if row and row["auto_saved"]:
            cx.execute(
                "INSERT INTO agent_feedback (topics,tags,title,url,dismissed_at) VALUES (?,?,?,?,?)",
                (row["topic"] or "", row["tags"] or "[]", row["title"] or "", row["url"] or "", now_ts())
            )
            log.info(f"Agent feedback: auto-saved article deleted '{(row['title'] or '')[:50]}'")
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
    threads = []
    for src in sources:
        if src in SCRAPERS and not sync_status.get(src, {}).get("running"):
            t = threading.Thread(target=run_sync, args=(src,), daemon=True)
            t.start()
            threads.append(t)
            started.append(src)
    # After all scrapers finish, enrich any remaining title_only articles
    def _enrich_after_sync():
        for t in threads:
            t.join()
        log.info("Sync all complete — running title-only enrichment")
        enrich_title_only_articles()
    if threads:
        threading.Thread(target=_enrich_after_sync, daemon=True).start()
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

def enrich_title_only_articles():
    """Fetch full text for all title_only articles. Uses logged-in profiles for FT/Eco/FA, generic scrape for others."""
    import urllib.request as _ur
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        rows = cx.execute("SELECT * FROM articles WHERE status='title_only' AND url!=''").fetchall()
    arts = [dict(r) for r in rows]
    if not arts:
        log.info("Enrich title-only: nothing to do")
        return 0
    log.info(f"Enrich title-only: {len(arts)} articles to process")

    ft_arts  = [a for a in arts if a["source"] == "Financial Times"]
    eco_arts = [a for a in arts if a["source"] == "The Economist"]
    fa_arts  = [a for a in arts if a["source"] == "Foreign Affairs"]
    other_arts = [a for a in arts if a["source"] not in ("Financial Times","The Economist","Foreign Affairs")]
    enriched = 0

    # FT — use logged-in ft_profile
    if ft_arts and PLAYWRIGHT_OK:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                browser = pw.chromium.launch_persistent_context(
                    str(BASE_DIR / "ft_profile"),
                    headless=True, args=["--no-sandbox"]
                )
                page = browser.pages[0] if browser.pages else browser.new_page()
                for a in ft_arts:
                    text, pub_date = fetch_ft_article_text(page, a["url"])
                    if text:
                        a["body"] = text
                        if pub_date and not a.get("pub_date"):
                            a["pub_date"] = pub_date
                        with sqlite3.connect(DB_PATH) as cx:
                            cx.execute("UPDATE articles SET body=?, pub_date=?, status='fetched' WHERE id=?",
                                       (text, a.get("pub_date",""), a["id"]))
                        enrich_article_with_ai(a)
                        _save_enriched_article(a)
                        enriched += 1
                        log.info(f"Enrich title-only: FT fetched '{a['title'][:50]}'")
                browser.close()
        except Exception as e:
            log.warning(f"Enrich title-only: FT Playwright failed: {e}")

    # Economist — use logged-in economist_profile
    if eco_arts and PLAYWRIGHT_OK:
        try:
            from playwright.sync_api import sync_playwright
            eco_profile = BASE_DIR / "economist_profile"
            if not eco_profile.exists():
                eco_profile = BASE_DIR / "ft_profile"
            with sync_playwright() as pw:
                browser = pw.chromium.launch_persistent_context(
                    str(eco_profile),
                    headless=True, args=["--no-sandbox"]
                )
                page = browser.pages[0] if browser.pages else browser.new_page()
                for a in eco_arts:
                    text, pub_date = fetch_economist_article_text(page, a["url"])
                    if text:
                        a["body"] = text
                        if pub_date and not a.get("pub_date"):
                            a["pub_date"] = pub_date
                        with sqlite3.connect(DB_PATH) as cx:
                            cx.execute("UPDATE articles SET body=?, pub_date=?, status='fetched' WHERE id=?",
                                       (text, a.get("pub_date",""), a["id"]))
                        enrich_article_with_ai(a)
                        _save_enriched_article(a)
                        enriched += 1
                        log.info(f"Enrich title-only: Economist fetched '{a['title'][:50]}'")
                browser.close()
        except Exception as e:
            log.warning(f"Enrich title-only: Economist Playwright failed: {e}")

    # Foreign Affairs — use fa_profile
    if fa_arts and PLAYWRIGHT_OK:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                browser = pw.chromium.launch_persistent_context(
                    str(BASE_DIR / "fa_profile"),
                    headless=True, args=["--no-sandbox"]
                )
                page = browser.pages[0] if browser.pages else browser.new_page()
                for a in fa_arts:
                    try:
                        page.goto(a["url"], wait_until="domcontentloaded", timeout=20000)
                        page.wait_for_timeout(2000)
                        from bs4 import BeautifulSoup as _BS
                        soup = _BS(page.content(), "html.parser")
                        paragraphs = soup.select("div.article-body p, div[class*='body'] p")
                        text = " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 60)
                        if text:
                            a["body"] = text
                            with sqlite3.connect(DB_PATH) as cx:
                                cx.execute("UPDATE articles SET body=?, status='fetched' WHERE id=?", (text, a["id"]))
                            enrich_article_with_ai(a)
                            _save_enriched_article(a)
                            enriched += 1
                            log.info(f"Enrich title-only: FA fetched '{a['title'][:50]}'")
                    except Exception as e:
                        log.warning(f"Enrich title-only: FA fetch failed for {a['url']}: {e}")
                browser.close()
        except Exception as e:
            log.warning(f"Enrich title-only: FA Playwright failed: {e}")

    # Other sources — generic scrape (no login)
    for a in other_arts:
        try:
            req = _ur.Request(a["url"], headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            })
            with _ur.urlopen(req, timeout=20) as r:
                html = r.read().decode("utf-8", errors="ignore")
            body = ""
            if BS4_OK:
                from bs4 import BeautifulSoup as _BS
                soup = _BS(html, "html.parser")
                for tag in soup(["script","style","nav","header","footer","aside","form"]):
                    tag.decompose()
                container = soup.find("article") or soup.find("main") or soup.find("body")
                if container:
                    paragraphs = container.find_all("p")
                    body = " ".join(p.get_text(" ", strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 60)
            if len(body) < 200:
                log.warning(f"Enrich title-only: insufficient text from {a['url']} — may be paywalled")
                continue
            a["body"] = body[:8000]
            with sqlite3.connect(DB_PATH) as cx:
                cx.execute("UPDATE articles SET body=?, status='fetched' WHERE id=?", (a["body"], a["id"]))
            enrich_article_with_ai(a)
            _save_enriched_article(a)
            enriched += 1
            log.info(f"Enrich title-only: generic fetched '{a['title'][:50]}'")
        except Exception as e:
            log.warning(f"Enrich title-only: generic fetch failed for {a['url']}: {e}")

    log.info(f"Enrich title-only: done — {enriched}/{len(arts)} enriched")
    return enriched

def _save_enriched_article(art):
    """Save enriched article fields back to DB after enrich_article_with_ai."""
    with sqlite3.connect(DB_PATH) as cx:
        cx.execute(
            "UPDATE articles SET summary=?, body=?, tags=?, topic=?, pub_date=?, status=? WHERE id=?",
            (art.get("summary",""), art.get("body",""), art.get("tags","[]"),
             art.get("topic",""), art.get("pub_date",""), art.get("status","fetched"), art["id"])
        )

@app.route("/api/enrich-title-only", methods=["POST"])
def enrich_title_only_route():
    if getattr(enrich_title_only_route, "_running", False):
        return jsonify({"ok": False, "error": "Already running"}), 409
    def _run():
        enrich_title_only_route._running = True
        try:
            enrich_title_only_articles()
        finally:
            enrich_title_only_route._running = False
    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok": True, "started": True})

@app.route("/api/enrich-title-only/status", methods=["GET"])
def enrich_title_only_status():
    return jsonify({"running": getattr(enrich_title_only_route, "_running", False)})

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


# ── Interview routes ──────────────────────────────────────────────────────────

@app.route("/api/interviews", methods=["GET"])
def get_interviews():
    limit = int(request.args.get("limit", 50))
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        rows = cx.execute(
            "SELECT * FROM interviews ORDER BY added_date DESC LIMIT ?", (limit,)
        ).fetchall()
    return jsonify({"interviews": [dict(r) for r in rows], "total": len(rows)})

@app.route("/api/interviews", methods=["POST"])
def add_interview():
    body = request.json or {}
    import time as _time
    with sqlite3.connect(DB_PATH) as cx:
        cx.execute("""INSERT INTO interviews
            (title, url, source, published_date, added_date, duration_seconds,
             transcript, summary, status, thumbnail_url)
            VALUES (?,?,?,?,?,?,?,?,?,?)""", (
            body.get("title", "Untitled"),
            body.get("url", ""),
            body.get("source", ""),
            body.get("published_date", ""),
            int(_time.time() * 1000),
            body.get("duration_seconds", 0),
            body.get("transcript", ""),
            body.get("summary", ""),
            body.get("status", "pending"),
            body.get("thumbnail_url", ""),
        ))
        iid = cx.execute("SELECT last_insert_rowid()").fetchone()[0]
    return jsonify({"ok": True, "id": iid})

@app.route("/api/interviews/<int:iid>", methods=["PATCH"])
def update_interview(iid):
    body = request.json or {}
    with sqlite3.connect(DB_PATH) as cx:
        for key in ["title","url","source","published_date","duration_seconds",
                    "transcript","summary","status","thumbnail_url","speaker_bio"]:
            if key in body:
                cx.execute("UPDATE interviews SET {}=? WHERE id=?".format(key), (body[key], iid))
    return jsonify({"ok": True})

@app.route("/api/interviews/<int:iid>", methods=["DELETE"])
def delete_interview(iid):
    with sqlite3.connect(DB_PATH) as cx:
        cx.execute("DELETE FROM interviews WHERE id=?", (iid,))
    return jsonify({"ok": True})

@app.route("/api/interviews/fetch-meta", methods=["POST"])
def fetch_interview_meta():
    import urllib.request, json as _json, re
    body = request.json or {}
    url = body.get("url", "")
    if not url:
        return jsonify({"ok": False, "error": "No URL"}), 400
    vid = None
    for pattern in [r"v=([A-Za-z0-9_-]{11})", r"youtu\.be/([A-Za-z0-9_-]{11})", r"embed/([A-Za-z0-9_-]{11})"]:
        m = re.search(pattern, url)
        if m:
            vid = m.group(1)
            break
    if not vid:
        return jsonify({"ok": False, "error": "Could not extract video ID"}), 400
    oembed_url = "https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={}&format=json".format(vid)
    try:
        with urllib.request.urlopen(oembed_url, timeout=10) as r:
            data = _json.loads(r.read())
        thumbnail = "https://img.youtube.com/vi/{}/hqdefault.jpg".format(vid)
        return jsonify({
            "ok": True,
            "title": data.get("title", ""),
            "thumbnail_url": thumbnail,
            "author": data.get("author_name", ""),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── Suggested Articles ────────────────────────────────────────────────────────


def scrape_ft_most_read(limit=8):
    """Scrape FT most-read using logged-in Playwright profile."""
    if not PLAYWRIGHT_OK:
        return []
    profile_dir = BASE_DIR / "ft_profile"
    if not profile_dir.exists():
        return []
    articles = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                str(profile_dir), headless=True,
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                args=["--disable-blink-features=AutomationControlled"])
            page = browser.new_page()
            try:
                # Homepage has 186 article links when logged in; most-read page returns 0
                page.goto("https://www.ft.com", wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(3000)
                soup = BeautifulSoup(page.content(), "html.parser")
                seen = set()
                for a in soup.select("a[href*='/content/']"):
                    title = a.get_text(strip=True)
                    href = a.get("href", "")
                    if not title or len(title) < 10: continue
                    url = ("https://www.ft.com" + href if href.startswith("/") else href).split("?")[0]
                    if url in seen: continue
                    seen.add(url)
                    articles.append({"source": "Financial Times", "title": title, "url": url})
                    if len(articles) >= limit: break
                log.info(f"Suggested: FT most-read scraped {len(articles)} articles")
            finally:
                browser.close()
    except Exception as e:
        log.warning(f"Suggested: FT Playwright error: {e}")
    return articles


def scrape_economist_most_read(limit=8):
    """Scrape Economist most-read using logged-in Playwright profile.
    Tries 3 URLs in order: most-read page, /latest, homepage."""
    if not PLAYWRIGHT_OK:
        return []
    profile_dir = BASE_DIR / "economist_profile"
    if not profile_dir.exists():
        return []

    # Known Economist section paths — used to validate article URLs
    SECTION_PATHS = (
        "/briefing/", "/leaders/", "/finance-and-economics/", "/united-states/",
        "/china/", "/middle-east-and-africa/", "/asia/", "/europe/", "/britain/",
        "/international/", "/business/", "/science-and-technology/", "/culture/",
        "/graphic-detail/", "/the-world-ahead/", "/special-report/",
    )
    SKIP_PATHS = (
        "/podcasts/", "/newsletters/", "/events/", "/shop/", "/subscribe",
        "/login", "/register", "/search", "/topics/", "/authors/",
    )

    def extract_articles(soup, seen, limit):
        """Extract valid article links from soup — strict selector."""
        results = []
        # Target anchor tags that contain a headline element or are inside article cards
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if not href: continue
            url = ("https://www.economist.com" + href if href.startswith("/") else href).split("?")[0]
            # Must be economist.com
            if "economist.com" not in url: continue
            # Must be a known section path or year-based URL
            path = url.replace("https://www.economist.com", "")
            is_section = any(path.startswith(s) for s in SECTION_PATHS)
            is_dated = "/20" in path and len(path) > 15
            if not (is_section or is_dated): continue
            # Skip non-article paths
            if any(skip in path for skip in SKIP_PATHS): continue
            # Skip very short paths (section index pages like /china)
            if len(path.strip("/").split("/")) < 2: continue
            if url in seen: continue
            title = a.get_text(strip=True)
            # Title must be meaningful — not a nav label
            if not title or len(title) < 15: continue
            # Skip if title looks like a section label (all caps, very short)
            if title.isupper() and len(title) < 30: continue
            seen.add(url)
            results.append({"source": "The Economist", "title": title, "url": url})
            if len(results) >= limit: break
        return results

    articles = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                str(profile_dir), headless=True,
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                args=["--disable-blink-features=AutomationControlled"])
            page = browser.new_page()
            seen = set()
            try:
                urls_to_try = [
                    ("most-read", "https://www.economist.com/most-read"),
                    ("latest",    "https://www.economist.com/latest"),
                    ("homepage",  "https://www.economist.com"),
                ]
                for label, url in urls_to_try:
                    if len(articles) >= 3:
                        break
                    try:
                        log.info(f"Suggested: Economist trying {label}")
                        page.goto(url, wait_until="domcontentloaded", timeout=20000)
                        page.wait_for_timeout(3000)
                        soup = BeautifulSoup(page.content(), "html.parser")
                        found = extract_articles(soup, seen, limit - len(articles))
                        articles.extend(found)
                        log.info(f"Suggested: Economist {label} yielded {len(found)} articles (total {len(articles)})")
                    except Exception as e:
                        log.warning(f"Suggested: Economist {label} failed: {e}")
                        continue
            finally:
                browser.close()
    except Exception as e:
        log.warning(f"Suggested: Economist Playwright error: {e}")
    log.info(f"Suggested: Economist scraped {len(articles)} articles total")
    return articles

def extract_pub_date_from_url(url):
    """Extract publication date from URL patterns used by FT, Economist, FA."""
    import re as _re
    # Economist: /2026/03/26/
    m = _re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
    if m:
        return f"{m.group(3)} {_month_name(int(m.group(2)))} {m.group(1)}"
    # FT: /content/ URLs don't have dates — skip
    return ""

def _month_name(n):
    return ["","January","February","March","April","May","June",
            "July","August","September","October","November","December"][n]

def scrape_suggested_articles():
    """Scrape FT/Economist via Playwright + Claude web_search for FA and others."""
    import urllib.request, json as _json

    # Get user interests
    with sqlite3.connect(DB_PATH) as cx:
        rows = cx.execute("SELECT topic, tags FROM articles ORDER BY saved_at DESC LIMIT 100").fetchall()
        saved_urls = set(r[0] for r in cx.execute("SELECT url FROM articles WHERE url!=''").fetchall())

    # Scrape FT and Economist via logged-in Playwright (runs in background threads)
    ft_results = []
    eco_results = []
    import threading as _threading
    ft_thread = _threading.Thread(target=lambda: ft_results.extend(scrape_ft_most_read(8)))
    eco_thread = _threading.Thread(target=lambda: eco_results.extend(scrape_economist_most_read(8)))
    ft_thread.start()
    eco_thread.start()
    ft_thread.join(timeout=45)
    eco_thread.join(timeout=45)
    log.info(f"Suggested: Playwright got {len(ft_results)} FT, {len(eco_results)} Economist")
    topic_counts = {}
    for row in rows:
        if row[0]: topic_counts[row[0]] = topic_counts.get(row[0],0) + 1
        try:
            for tag in _json.loads(row[1] or "[]"):
                topic_counts[tag] = topic_counts.get(tag,0) + 1
        except: pass
    top_interests = sorted(topic_counts, key=lambda x: -topic_counts[x])[:15]
    interests_str = ", ".join(top_interests) if top_interests else "geopolitics, economics, finance, markets"

    # Build negative signal from dismissed suggested articles
    avoid_counts = {}
    with sqlite3.connect(DB_PATH) as cx:
        dismissed_rows = cx.execute(
            "SELECT sa.title, a.topic, a.tags FROM suggested_articles sa "
            "LEFT JOIN articles a ON sa.url = a.url "
            "WHERE sa.status='dismissed'"
        ).fetchall()
    for title, topic, tags in dismissed_rows:
        if topic: avoid_counts[topic] = avoid_counts.get(topic, 0) + 1
        try:
            for tag in _json.loads(tags or "[]"):
                avoid_counts[tag] = avoid_counts.get(tag, 0) + 1
        except: pass
    # Also include agent feedback (deleted auto-saved articles) as negative signals
    with sqlite3.connect(DB_PATH) as cx:
        feedback_rows = cx.execute("SELECT topics, tags FROM agent_feedback").fetchall()
    for fb_topics, fb_tags in feedback_rows:
        for t in (fb_topics or "").split(","):
            t = t.strip()
            if t: avoid_counts[t] = avoid_counts.get(t, 0) + 2
        try:
            for tag in _json.loads(fb_tags or "[]"):
                avoid_counts[tag] = avoid_counts.get(tag, 0) + 2
        except: pass
    top_avoid = sorted(avoid_counts, key=lambda x: -avoid_counts[x])[:10]
    avoid_str = ", ".join(top_avoid) if top_avoid else ""
    if avoid_str:
        log.info(f"Suggested: negative signals — {avoid_str}")

    creds = load_creds()
    api_key = creds.get("anthropic_api_key","")
    if not api_key:
        log.warning("Suggested: no API key")
        return []

    # Claude web search for FA + other quality sources (FT/Economist handled by Playwright above)
    prompt = (
        "You are a research assistant finding articles for a senior analyst. "
        "Their interests: " + interests_str + ".\n\n"
        "Do these searches IN ORDER:\n"
        "1. Search: site:foreignaffairs.com last 7 days " + interests_str[:60] + "\n"
        "2. Search: latest analysis " + interests_str[:60] + " last 7 days\n"
        "3. Search: " + interests_str[:60] + " expert analysis last 7 days\n\n"
        "Find 4-5 articles per search from quality sources "
        "(Foreign Affairs, Foreign Policy, Atlantic Council, Brookings, RAND, CFR, major newspapers). "
        "You MUST attempt ALL THREE searches.\n\n"
        "Scoring: 1-10 relevance to analyst interests. "
        "Exclude: news briefs, quizzes, recipes, lifestyle, sport, obituaries." +
        (" Analyst has explicitly dismissed articles about: " + avoid_str + " — score these topics lower." if avoid_str else "") +
        "\n\n"
        "Use the actual publication name for source field.\n\n"
        "Respond with ONLY a JSON array sorted by score descending:\n"
        '[{"title":"...","url":"...","source":"...","score":8,"reason":"one sentence why","pub_date":"26 March 2026 or empty string"}]'
    )

    req = None  # placeholder — request built in agentic loop below
    try:
        messages = [{"role": "user", "content": prompt}]
        # Agentic loop — web_search requires multiple roundtrips
        for attempt in range(6):
            payload = _json.dumps({
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 2000,
                "tools": [{"type": "web_search_20250305", "name": "web_search"}],
                "messages": messages
            }).encode()
            req2 = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=payload,
                headers={"Content-Type":"application/json","x-api-key":api_key,"anthropic-version":"2023-06-01"},
                method="POST"
            )
            log.info(f"Suggested: web search attempt {attempt+1}/6")
            try:
                with urllib.request.urlopen(req2, timeout=60) as r:
                    data = _json.loads(r.read())
            except Exception as _loop_e:
                log.warning(f"Suggested: web search attempt {attempt+1} failed: {_loop_e}")
                break
            stop_reason = data.get("stop_reason","")
            log.info(f"Suggested: attempt {attempt+1} stop_reason={stop_reason}")
            content_blocks = data.get("content", [])
            # Append assistant turn
            messages.append({"role": "assistant", "content": content_blocks})
            # If done, extract text
            if stop_reason == "end_turn":
                text = ""
                for block in content_blocks:
                    if block.get("type") == "text":
                        text += block.get("text","")
                text = text.strip()
                if not text:
                    log.warning("Suggested: empty final response")
                    return []
                # Extract JSON array even if surrounded by prose
                import re as _re
                json_match = _re.search(r'\[[\s\S]*\]', text)
                if not json_match:
                    log.warning(f"Suggested: no JSON array in response: {text[:200]}")
                    return []
                results = _json.loads(json_match.group(0))
                results = [a for a in results if a.get("url","") not in saved_urls and a.get("title","")]
                log.info(f"Suggested: Claude found {len(results)} articles via web search")
                # Score FT/Economist via Claude (same quality as web search results)
                seen_urls = set(a['url'] for a in results)
                playwright_arts = [a for a in ft_results + eco_results
                                   if a['url'] not in saved_urls and a['url'] not in seen_urls]
                for _pa in playwright_arts:
                    if not _pa.get("pub_date"):
                        _pa["pub_date"] = extract_pub_date_from_url(_pa["url"])
                # Look up pub_dates for any still missing via Claude web search
                needs_date = [a for a in playwright_arts if not a.get("pub_date")]
                if needs_date:
                    time.sleep(5)  # avoid 429 after main web search
                    try:
                        date_titles = _json.dumps([{"title": a["title"], "source": a["source"]} for a in needs_date])
                        date_prompt = ("For each of these articles, find the publication date. "
                                      "Respond ONLY with a JSON array (same order): "
                                      '[{"pub_date":"26 March 2026"}] '
                                      "Use empty string if unknown. Articles: " + date_titles)
                        date_payload = _json.dumps({
                            "model": "claude-sonnet-4-20250514",
                            "max_tokens": 500,
                            "tools": [{"type": "web_search_20250305", "name": "web_search"}],
                            "messages": [{"role": "user", "content": date_prompt}]
                        }).encode()
                        date_msgs = [{"role": "user", "content": date_prompt}]
                        for _da in range(4):
                            date_req = urllib.request.Request(
                                "https://api.anthropic.com/v1/messages",
                                data=_json.dumps({
                                    "model": "claude-sonnet-4-20250514",
                                    "max_tokens": 500,
                                    "tools": [{"type": "web_search_20250305", "name": "web_search"}],
                                    "messages": date_msgs
                                }).encode(),
                                headers={"Content-Type":"application/json","x-api-key":api_key,"anthropic-version":"2023-06-01"},
                                method="POST"
                            )
                            with urllib.request.urlopen(date_req, timeout=30) as dr:
                                date_data = _json.loads(dr.read())
                            date_msgs.append({"role": "assistant", "content": date_data.get("content", [])})
                            if date_data.get("stop_reason") == "end_turn":
                                date_text = "".join(b.get("text","") for b in date_data.get("content",[]) if b.get("type")=="text")
                                date_match = _re.search(r"\[[\s\S]*\]", date_text)
                                if date_match:
                                    dates = _json.loads(date_match.group(0))
                                    for i, a in enumerate(needs_date):
                                        if i < len(dates):
                                            a["pub_date"] = dates[i].get("pub_date", "")
                                    log.info(f"Suggested: pub_dates fetched for {len(needs_date)} Playwright articles")
                                break
                            elif date_data.get("stop_reason") == "tool_use":
                                tool_results = [{"type":"tool_result","tool_use_id":b["id"],"content":"Search completed."} for b in date_data.get("content",[]) if b.get("type")=="tool_use"]
                                if tool_results:
                                    date_msgs.append({"role":"user","content":tool_results})
                    except Exception as de:
                        log.warning(f"Suggested: pub_date lookup failed: {de}")
                if playwright_arts:
                    time.sleep(5)  # avoid 429 after pub_date lookup
                    titles_str = _json.dumps([{"title": a["title"], "source": a["source"]} for a in playwright_arts])
                    score_prompt = ("You are scoring news articles for a senior analyst. Their interests: " + interests_str + ". Score each article 0-10 for relevance to these interests. Be strict - only score 6+ if genuinely relevant. Exclude: lifestyle, sport, celebrity, recipes, quizzes, obituaries." + (" The analyst has dismissed articles about: " + avoid_str + " — score these lower." if avoid_str else "") + " Articles to score: " + titles_str + " Respond ONLY with a JSON array (same order): [{score:8,reason:one sentence why relevant}]")
                    try:
                        score_payload = _json.dumps({
                            "model": "claude-sonnet-4-20250514",
                            "max_tokens": 1000,
                            "messages": [{"role": "user", "content": score_prompt}]
                        }).encode()
                        score_req = urllib.request.Request(
                            "https://api.anthropic.com/v1/messages",
                            data=score_payload,
                            headers={"Content-Type":"application/json","x-api-key":api_key,"anthropic-version":"2023-06-01"},
                            method="POST"
                        )
                        # Retry once on 429
                        import urllib.error as _ue
                        for _attempt in range(2):
                            try:
                                with urllib.request.urlopen(score_req, timeout=30) as sr:
                                    score_data = _json.loads(sr.read())
                                break
                            except _ue.HTTPError as _he:
                                if _he.code == 429 and _attempt == 0:
                                    log.warning("Suggested: Claude scoring 429 — retrying in 10s")
                                    time.sleep(10)
                                    score_req = urllib.request.Request(
                                        "https://api.anthropic.com/v1/messages",
                                        data=score_payload,
                                        headers={"Content-Type":"application/json","x-api-key":api_key,"anthropic-version":"2023-06-01"},
                                        method="POST"
                                    )
                                else:
                                    raise
                        score_text = ""
                        for block in score_data.get("content", []):
                            if block.get("type") == "text":
                                score_text += block.get("text", "")
                        json_match2 = _re.search(r'\[[\s\S]*\]', score_text)
                        if json_match2:
                            scores = _json.loads(json_match2.group(0))
                            for i, art in enumerate(playwright_arts):
                                if i < len(scores):
                                    art["score"] = scores[i].get("score", 0)
                                    art["reason"] = scores[i].get("reason", "From " + art["source"])
                                else:
                                    art["score"] = 0
                            playwright_arts = [a for a in playwright_arts if a.get("score", 0) >= 6]
                            log.info(f"Suggested: Claude scored {len(playwright_arts)} FT/Economist articles ≥6")
                        else:
                            log.warning("Suggested: could not parse Claude scores for Playwright articles")
                            playwright_arts = []
                    except Exception as se:
                        log.warning(f"Suggested: Claude scoring of Playwright articles failed: {se}")
                        playwright_arts = []
                    for art in playwright_arts:
                        seen_urls.add(art["url"])
                        results.append(art)
                results.sort(key=lambda x: -x.get('score', 0))
                log.info(f"Suggested: {len(results)} total after merging Playwright + web search")
                return results
            # If tool_use, feed results back
            if stop_reason == "tool_use":
                tool_results = []
                for block in content_blocks:
                    if block.get("type") == "tool_use":
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block["id"],
                            "content": "Search completed."
                        })
                if tool_results:
                    messages.append({"role": "user", "content": tool_results})
            else:
                break
        log.warning("Suggested: agentic loop exhausted without end_turn")
        return []
    except Exception as e:
        log.warning(f"Suggested: Claude web search failed: {e}")
        return []


def save_suggested_snapshot(articles):
    snapshot_date = datetime.now().strftime("%Y-%m-%d")
    added = 0
    with sqlite3.connect(DB_PATH) as cx:
        existing_urls = set(r[0] for r in cx.execute("SELECT url FROM suggested_articles").fetchall())
        for a in articles:
            url = a.get("url","")
            if not url or url in existing_urls:
                continue
            cx.execute(
                "INSERT INTO suggested_articles (title,url,source,snapshot_date,score,reason,added_at,status,pub_date) VALUES (?,?,?,?,?,?,?,'new',?)",
                (a.get("title",""), url, a.get("source",""),
                 snapshot_date, a.get("score",0), a.get("reason",""), now_ts(), a.get("pub_date",""))
            )
            existing_urls.add(url)
            added += 1
    log.info(f"Suggested: added {added} new articles (skipped duplicates) for {snapshot_date}")


@app.route("/api/suggested", methods=["GET"])
def get_suggested():
    since = request.args.get("since", "")
    status_filter = request.args.get("status", "")
    source_filter = request.args.get("source", "")
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        conditions = []
        params = []
        if since:
            conditions.append("snapshot_date >= ?")
            params.append(since)
        if status_filter and status_filter != "all":
            conditions.append("status = ?")
            params.append(status_filter)
        if source_filter:
            conditions.append("source = ?")
            params.append(source_filter)
        # Sync status for any suggested articles whose URL is now in Feed
        cx.execute("""UPDATE suggested_articles SET status='saved'
            WHERE status NOT IN ('saved','dismissed')
            AND url IN (SELECT url FROM articles WHERE url!='')""")
        # Always exclude saved articles from UI — they are already in Feed
        conditions.append("status != 'saved'")
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = cx.execute(
            f"SELECT * FROM suggested_articles {where} ORDER BY score DESC, added_at DESC",
            params
        ).fetchall()
        new_count = cx.execute("SELECT COUNT(*) FROM suggested_articles WHERE status='new'").fetchone()[0]
        last_added = cx.execute("SELECT MAX(added_at) FROM suggested_articles").fetchone()[0] or 0
    return jsonify({"articles":[dict(r) for r in rows], "new_count":new_count, "last_added_ts":last_added})


@app.route("/api/suggested/refresh", methods=["POST"])
def refresh_suggested():
    if getattr(refresh_suggested, "_running", False):
        return jsonify({"ok":False,"error":"Already running"}), 409
    def _run():
        refresh_suggested._running = True
        try:
            arts = scrape_suggested_articles()
            if arts: save_suggested_snapshot(arts)
        finally:
            refresh_suggested._running = False
    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok":True,"started":True})

@app.route("/api/suggested/status", methods=["GET"])
def suggested_status():
    return jsonify({"running": getattr(refresh_suggested, "_running", False)})

@app.route("/api/suggested/<int:sid>", methods=["PATCH"])
def patch_suggested(sid):
    data = request.get_json() or {}
    status = data.get("status")
    if status not in ("new","reviewed","saved","dismissed"):
        return jsonify({"ok":False,"error":"invalid status"}), 400
    ts = now_ts() if status == "reviewed" else None
    with sqlite3.connect(DB_PATH) as cx:
        cx.execute("UPDATE suggested_articles SET status=?, reviewed_at=? WHERE id=?", (status, ts, sid))
    return jsonify({"ok":True})

@app.route("/api/suggested/<int:sid>/preview", methods=["POST"])
def preview_suggested(sid):
    import urllib.request as _ur, json as _json
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        row = cx.execute("SELECT * FROM suggested_articles WHERE id=?", (sid,)).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "not found"}), 404
    row = dict(row)
    # Return cached preview if available
    if row.get("preview"):
        return jsonify({"ok": True, "preview": row["preview"]})
    # Fetch article text
    try:
        req = _ur.Request(row["url"], headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        with _ur.urlopen(req, timeout=20) as r:
            html = r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return jsonify({"ok": False, "error": f"Could not fetch article: {e}"}), 502
    body = ""
    if BS4_OK:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
            tag.decompose()
        container = soup.find("article") or soup.find("main") or soup.find("body")
        if container:
            paragraphs = container.find_all("p")
            body = " ".join(p.get_text(" ", strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 60)
    if len(body) < 100:
        return jsonify({"ok": False, "error": "Could not extract enough text (may be paywalled)"}), 422
    # Summarise with Claude
    creds = load_creds()
    api_key = creds.get("anthropic_api_key", "")
    if not api_key:
        return jsonify({"ok": False, "error": "No API key configured"}), 500
    prompt = f"""Summarise this article in 3-4 sentences. Focus on why it would be relevant to someone interested in geopolitics, economics, markets, and international affairs.

Title: {row['title']}
Source: {row['source']}

Article text:
{body[:6000]}"""
    payload = _json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()
    req = _ur.Request(
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
        with _ur.urlopen(req, timeout=30) as resp:
            data = _json.loads(resp.read())
            preview = data["content"][0]["text"].strip()
    except Exception as e:
        return jsonify({"ok": False, "error": f"Claude API error: {e}"}), 502
    # Cache in DB
    with sqlite3.connect(DB_PATH) as cx:
        cx.execute("UPDATE suggested_articles SET preview=? WHERE id=?", (preview, sid))
    return jsonify({"ok": True, "preview": preview})

@app.route("/api/suggested/bulk-delete", methods=["POST"])
def bulk_delete_suggested():
    data = request.get_json() or {}
    ids = data.get("ids", [])
    if not ids:
        return jsonify({"ok":False,"error":"no ids"}), 400
    with sqlite3.connect(DB_PATH) as cx:
        cx.execute(f"DELETE FROM suggested_articles WHERE id IN ({','.join('?'*len(ids))})", ids)
    return jsonify({"ok":True,"deleted":len(ids)})

# ── reading agent ─────────────────────────────────────────────────────────────
def run_agent():
    """Auto-save high-scoring suggested articles to Feed."""
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        candidates = cx.execute(
            "SELECT * FROM suggested_articles WHERE status='new' AND score >= 8"
        ).fetchall()
    saved = []
    for row in candidates:
        row = dict(row)
        aid = make_id(row["source"], row["url"])
        if article_exists(aid):
            with sqlite3.connect(DB_PATH) as cx:
                cx.execute("UPDATE suggested_articles SET status='saved' WHERE id=?", (row["id"],))
            continue
        art = {
            "id": aid, "source": row["source"], "url": row["url"],
            "title": row["title"], "body": "", "summary": row.get("reason", ""),
            "topic": "", "tags": "[]", "saved_at": now_ts(), "fetched_at": None,
            "status": "agent", "pub_date": row.get("pub_date", ""), "auto_saved": 1,
        }
        upsert_article(art)
        with sqlite3.connect(DB_PATH) as cx:
            cx.execute("UPDATE suggested_articles SET status='saved' WHERE id=?", (row["id"],))
            cx.execute(
                "INSERT INTO agent_log (article_id,title,url,score,reason,saved_at) VALUES (?,?,?,?,?,?)",
                (aid, row["title"], row["url"], row["score"], row.get("reason", ""), now_ts())
            )
        saved.append({"id": aid, "title": row["title"], "score": row["score"]})
        log.info(f"Agent: auto-saved '{row['title'][:50]}' (score {row['score']})")
    log.info(f"Agent: saved {len(saved)} articles")
    return saved

@app.route("/api/agent/run", methods=["POST"])
def agent_run():
    saved = run_agent()
    return jsonify({"ok": True, "saved": len(saved), "articles": saved})

@app.route("/api/agent/log", methods=["GET"])
def agent_log_route():
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        rows = cx.execute("SELECT * FROM agent_log ORDER BY saved_at DESC LIMIT 50").fetchall()
    return jsonify({"entries": [dict(r) for r in rows]})

@app.route("/api/agent/feedback", methods=["POST"])
def agent_feedback():
    data = request.get_json() or {}
    topics = data.get("topics", "")
    tags = data.get("tags", "")
    title = data.get("title", "")
    url = data.get("url", "")
    with sqlite3.connect(DB_PATH) as cx:
        cx.execute(
            "INSERT INTO agent_feedback (topics,tags,title,url,dismissed_at) VALUES (?,?,?,?,?)",
            (topics, tags, title, url, now_ts())
        )
    log.info(f"Agent feedback: negative signal for '{title[:50]}' — topics={topics}")
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
    app.run(host="0.0.0.0", port=4242, debug=False)
