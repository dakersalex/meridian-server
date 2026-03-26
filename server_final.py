#!/usr/bin/env python3
"""
Meridian Scraper Server — v3
Correct URLs and selectors for FT, Economist and Bloomberg.
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
            saved_at INTEGER, fetched_at INTEGER, status TEXT DEFAULT 'pending')""")
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
          (id,source,url,title,body,summary,topic,tags,saved_at,fetched_at,status)
          VALUES (:id,:source,:url,:title,:body,:summary,:topic,:tags,:saved_at,:fetched_at,:status)""", art)
        cx.commit()

def all_articles(source=None, limit=200):
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        if source:
            rows = cx.execute("SELECT * FROM articles WHERE source=? ORDER BY saved_at DESC LIMIT ?", (source, limit)).fetchall()
        else:
            rows = cx.execute("SELECT * FROM articles ORDER BY saved_at DESC LIMIT ?", (limit,)).fetchall()
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

def new_browser(p, headless=True):
    return p.chromium.launch(headless=headless)

def new_context(browser):
    return browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

# ── FT scraper ────────────────────────────────────────────────────────────────
class FTScraper:
    name = "Financial Times"
    # FT saved articles live at this search URL
    SAVED_URL = "https://www.ft.com/search?q=My+saved+articles&sort=date&isFirstView=true"
    LOGIN_URL = "https://accounts.ft.com/login"

    def __init__(self, email, password):
        self.email = email
        self.password = password

    def scrape(self):
        if not PLAYWRIGHT_OK: raise RuntimeError("playwright not installed")
        articles = []
        with sync_playwright() as p:
            browser = new_browser(p, headless=True)
            ctx = new_context(browser)
            page = ctx.new_page()
            try:
                log.info("FT: logging in …")
                page.goto(self.LOGIN_URL, wait_until="domcontentloaded", timeout=40000)
                page.wait_for_timeout(2000)

                # dismiss cookie/consent popups
                for sel in ['button[title="Accept cookies"]', 'button.o-cookie-message__button']:
                    try: page.click(sel, timeout=3000); page.wait_for_timeout(500); break
                    except: pass
                try:
                    frame = page.frame_locator('iframe[id*="sp_message"]')
                    frame.locator('button[title*="Accept"], button[aria-label*="Accept"]').click(timeout=4000)
                    log.info("FT: dismissed consent iframe")
                    page.wait_for_timeout(1000)
                except: pass

                # fill email
                page.wait_for_selector('input[type="email"]', timeout=15000)
                page.fill('input[type="email"]', self.email)
                page.wait_for_timeout(500)
                try: page.click('button[type="submit"]', timeout=10000)
                except: page.keyboard.press("Enter")

                # fill password
                page.wait_for_selector('input[type="password"]', timeout=15000)
                page.fill('input[type="password"]', self.password)
                page.wait_for_timeout(500)
                try: page.click('button[type="submit"]', timeout=10000)
                except: page.keyboard.press("Enter")

                # wait for redirect away from login
                page.wait_for_timeout(5000)
                log.info(f"FT: after login, URL is {page.url}")

                # now go directly to saved articles search page
                log.info("FT: navigating to saved articles …")
                page.goto(self.SAVED_URL, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3000)
                log.info(f"FT: saved articles page loaded, URL: {page.url}")

                page_num = 1
                while page_num <= 12:  # 25 per page * 12 = 300 articles
                    log.info(f"FT: scraping page {page_num} …")
                    soup = BeautifulSoup(page.content(), "html.parser")

                    # each result is a div with class containing 'search-item' or 'o-teaser'
                    results = soup.select("div[class*='search-item'], div.o-teaser, li[class*='stream-item']")
                    log.info(f"FT page {page_num}: found {len(results)} result containers")

                    # fallback: grab all article links directly
                    if len(results) == 0:
                        links = soup.select("a[href*='/content/']")
                        for a in links:
                            href  = a.get("href","")
                            title = a.get_text(strip=True)
                            if len(title) < 15: continue
                            url = href if href.startswith("http") else f"https://www.ft.com{href}"
                            art_id = make_id(self.name, url)
                            articles.append({"id":art_id,"source":self.name,"url":url,"title":title,"body":"","summary":"","topic":"","tags":"[]","saved_at":now_ts(),"fetched_at":now_ts(),"status":"fetched"})
                            log.info(f"FT: scraped '{title[:60]}'")
                    else:
                        for item in results:
                            a_tag = item.select_one("a[href*='/content/'], a.js-teaser-heading-link")
                            if not a_tag: continue
                            href  = a_tag.get("href","")
                            url   = href if href.startswith("http") else f"https://www.ft.com{href}"
                            title = a_tag.get_text(strip=True)
                            # category is usually in a span with colour styling
                            category_el = item.select_one("span[class*='tag'], a[class*='tag'], span[class*='section']")
                            category = category_el.get_text(strip=True) if category_el else ""
                            snippet_el = item.select_one("p[class*='standfirst'], p[class*='summary'], p.o-teaser__standfirst")
                            snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                            art_id = make_id(self.name, url)
                            articles.append({"id":art_id,"source":self.name,"url":url,"title":title,"body":snippet,"summary":snippet,"topic":category,"tags":"[]","saved_at":now_ts(),"fetched_at":now_ts(),"status":"fetched"})
                            log.info(f"FT: scraped '{title[:60]}'")

                    # next page
                    try:
                        nxt = page.locator('a[aria-label="Next page"], a[data-trackable="next-page"], button:has-text("Next")')
                        if nxt.count() > 0:
                            nxt.first.click(); page.wait_for_timeout(3000); page_num += 1
                        else:
                            log.info("FT: no more pages"); break
                    except: break

                log.info(f"FT: total {len(articles)} articles scraped")

            except PWTimeout as e: log.error(f"FT timeout: {e}")
            except Exception as e: log.error(f"FT error: {e}", exc_info=True)
            finally: browser.close()
        return articles


# ── Economist scraper ─────────────────────────────────────────────────────────
class EconomistScraper:
    name = "The Economist"
    # Economist bookmarks live here
    SAVED_URL = "https://www.economist.com/for-you/bookmarks"
    LOGIN_URL = "https://www.economist.com/sign-in"

    def __init__(self, email, password):
        self.email = email
        self.password = password

    def scrape(self):
        if not PLAYWRIGHT_OK: raise RuntimeError("playwright not installed")
        articles = []
        with sync_playwright() as p:
            browser = new_browser(p, headless=True)
            ctx = new_context(browser)
            page = ctx.new_page()
            try:
                log.info("Economist: logging in …")
                page.goto(self.LOGIN_URL, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(3000)

                # dismiss cookie consent
                for sel in ['button#onetrust-accept-btn-handler', 'button[title*="Accept"]', '.onetrust-accept-btn-handler']:
                    try: page.click(sel, timeout=4000); page.wait_for_timeout(1000); break
                    except: pass

                # fill email
                page.wait_for_selector('input[name="email"], input[type="email"]', timeout=20000)
                page.fill('input[name="email"], input[type="email"]', self.email)
                page.wait_for_timeout(500)
                try: page.click('button[type="submit"]', timeout=8000)
                except: page.keyboard.press("Enter")

                # fill password
                page.wait_for_timeout(2000)
                page.wait_for_selector('input[name="password"], input[type="password"]', timeout=20000)
                page.fill('input[name="password"], input[type="password"]', self.password)
                page.wait_for_timeout(500)
                try: page.click('button[type="submit"]', timeout=8000)
                except: page.keyboard.press("Enter")

                page.wait_for_timeout(5000)
                log.info(f"Economist: after login URL is {page.url}")

                # navigate to bookmarks
                log.info("Economist: navigating to bookmarks …")
                page.goto(self.SAVED_URL, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3000)

                # scroll to load all
                for _ in range(8):
                    page.keyboard.press("End")
                    page.wait_for_timeout(1500)

                soup = BeautifulSoup(page.content(), "html.parser")

                # from screenshot: each article is a card with red category label and headline
                # try multiple selectors
                cards = soup.select("article, div[class*='card'], div[class*='teaser'], li[class*='article']")
                log.info(f"Economist: found {len(cards)} cards")

                # fallback: grab all article links
                if len(cards) == 0:
                    links = soup.select("a[href*='/leaders/'], a[href*='/international/'], a[href*='/britain/'], a[href*='/europe/'], a[href*='/united-states/'], a[href*='/business/'], a[href*='/finance-and-economics/'], a[href*='/science-and-technology/'], a[href*='/middle-east-and-africa/'], a[href*='/asia/'], a[href*='/china/'], a[href*='/the-americas/']")
                    seen = set()
                    for a in links:
                        href  = a.get("href","")
                        title = a.get_text(strip=True)
                        if len(title) < 15 or href in seen: continue
                        seen.add(href)
                        url = href if href.startswith("http") else f"https://www.economist.com{href}"
                        art_id = make_id(self.name, url)
                        articles.append({"id":art_id,"source":self.name,"url":url,"title":title,"body":"","summary":"","topic":"","tags":"[]","saved_at":now_ts(),"fetched_at":now_ts(),"status":"fetched"})
                        log.info(f"Economist: scraped '{title[:60]}'")
                else:
                    for card in cards:
                        a_tag = card.select_one("a[href*='/']")
                        if not a_tag: continue
                        href  = a_tag.get("href","")
                        url   = href if href.startswith("http") else f"https://www.economist.com{href}"
                        title = a_tag.get_text(strip=True)
                        if len(title) < 10: continue
                        # red category label from screenshot
                        cat_el = card.select_one("span[class*='section'], a[class*='section'], div[class*='fly-title'], span[style*='color']")
                        category = cat_el.get_text(strip=True) if cat_el else ""
                        art_id = make_id(self.name, url)
                        articles.append({"id":art_id,"source":self.name,"url":url,"title":title,"body":"","summary":"","topic":category,"tags":"[]","saved_at":now_ts(),"fetched_at":now_ts(),"status":"fetched"})
                        log.info(f"Economist: scraped '{title[:60]}'")

                log.info(f"Economist: total {len(articles)} articles scraped")

            except Exception as e: log.error(f"Economist error: {e}", exc_info=True)
            finally: browser.close()
        return articles


# ── Bloomberg scraper ─────────────────────────────────────────────────────────
class BloombergScraper:
    name = "Bloomberg"
    SAVED_URL = "https://www.bloomberg.com/portal/saved"

    def __init__(self, email, password):
        self.email = email
        self.password = password

    def scrape(self):
        if not PLAYWRIGHT_OK: raise RuntimeError("playwright not installed")
        profile_dir = BASE_DIR / "bloomberg_profile"
        profile_dir.mkdir(exist_ok=True)
        articles = []

        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                str(profile_dir), headless=False,
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                args=["--disable-blink-features=AutomationControlled"],
            )
            page = browser.new_page()
            try:
                log.info("Bloomberg: opening saved articles …")
                page.goto(self.SAVED_URL, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(4000)

                if "login" in page.url or "signin" in page.url or "sign-in" in page.url:
                    print("\n⚠️  Bloomberg needs you to log in.")
                    print("   Please log in in the browser window, then press Enter here.\n")
                    input("Press Enter once logged in …")
                    page.goto(self.SAVED_URL, wait_until="domcontentloaded", timeout=40000)
                    page.wait_for_timeout(4000)

                # try to show 50 per page
                try: page.select_option('select', '50'); page.wait_for_timeout(2000)
                except: pass

                page_num = 1
                while page_num <= 10:
                    log.info(f"Bloomberg: scraping page {page_num} …")
                    soup = BeautifulSoup(page.content(), "html.parser")
                    seen_urls = set()

                    for a_tag in soup.select("a[href*='/news/articles/'], a[href*='/features/'], a[href*='/opinion/'], a[href*='/markets/'], a[href*='/technology/'], a[href*='/politics/']"):
                        href  = a_tag.get("href","")
                        title = a_tag.get_text(strip=True)
                        if not href or len(title) < 20: continue
                        url = href if href.startswith("http") else f"https://www.bloomberg.com{href}"
                        if url in seen_urls: continue
                        seen_urls.add(url)
                        # get category from parent element
                        parent = a_tag.find_parent("li") or a_tag.find_parent("div")
                        category = ""
                        if parent:
                            for s in parent.select("span, div"):
                                t = s.get_text(strip=True)
                                if 5 < len(t) < 25 and t != title:
                                    category = t; break
                        art_id = make_id(self.name, url)
                        articles.append({"id":art_id,"source":self.name,"url":url,"title":title,"body":"","summary":"","topic":category,"tags":"[]","saved_at":now_ts(),"fetched_at":now_ts(),"status":"fetched"})
                        log.info(f"Bloomberg: scraped '{title[:60]}'")

                    # next page button
                    try:
                        nxt = page.locator('button[aria-label="Next page"], [aria-label="next"]')
                        if nxt.count() > 0:
                            nxt.first.click(); page.wait_for_timeout(3000); page_num += 1
                        else: break
                    except: break

                log.info(f"Bloomberg: total {len(articles)} articles scraped")

            except Exception as e: log.error(f"Bloomberg error: {e}", exc_info=True)
            finally: browser.close()
        return articles


SCRAPERS = {"ft": FTScraper, "economist": EconomistScraper, "bloomberg": BloombergScraper}

# ── sync engine ───────────────────────────────────────────────────────────────
sync_status = {}

def run_sync(source_key):
    creds = load_creds()
    scraper_cls = SCRAPERS.get(source_key)
    if not scraper_cls: return
    sc = creds.get(source_key, {})
    sync_status[source_key] = {"running": True, "last_error": None}
    started = int(time.time())
    found = new = 0
    try:
        scraper  = scraper_cls(sc.get("email",""), sc.get("password",""))
        arts     = scraper.scrape()
        found    = len(arts)
        for art in arts:
            if not article_exists(art["id"]):
                upsert_article(art); new += 1
        sync_status[source_key] = {"running":False,"last_run":datetime.now().isoformat(timespec="seconds"),"last_error":None,"articles_found":found,"articles_new":new}
        log.info(f"{source_key}: sync done — {found} found, {new} new")
    except Exception as e:
        log.error(f"{source_key}: sync error — {e}", exc_info=True)
        sync_status[source_key] = {"running":False,"last_run":datetime.now().isoformat(timespec="seconds"),"last_error":str(e),"articles_found":found,"articles_new":new}
    finally:
        with sqlite3.connect(DB_PATH) as cx:
            cx.execute("INSERT INTO sync_log (source,started_at,finished_at,articles_found,articles_new,error) VALUES (?,?,?,?,?,?)",
                (source_key, started, int(time.time()), found, new, sync_status[source_key].get("last_error")))
            cx.commit()

# ── API routes ────────────────────────────────────────────────────────────────
@app.route("/api/health")
def health(): return jsonify({"ok":True,"version":"3.0.0"})

@app.route("/api/articles")
def get_articles():
    arts = all_articles(source=request.args.get("source"), limit=int(request.args.get("limit",500)))
    for a in arts:
        try: a["tags"] = json.loads(a["tags"] or "[]")
        except: a["tags"] = []
    return jsonify({"articles":arts,"total":len(arts)})

@app.route("/api/sync", methods=["POST"])
def trigger_sync():
    body   = request.get_json(force=True, silent=True) or {}
    source = body.get("source","all")
    keys   = list(SCRAPERS.keys()) if source == "all" else [source]
    started = []
    for k in keys:
        if sync_status.get(k,{}).get("running"): continue
        threading.Thread(target=run_sync, args=(k,), daemon=True).start()
        started.append(k)
    return jsonify({"started":started})

@app.route("/api/sync/status")
def sync_status_route(): return jsonify(sync_status)

@app.route("/api/credentials", methods=["GET","POST"])
def credentials():
    if request.method == "POST":
        save_creds(request.get_json(force=True)); return jsonify({"ok":True})
    creds = load_creds()
    return jsonify({k:{**v,"password":"••••••••"} for k,v in creds.items()})

@app.route("/api/articles/<article_id>", methods=["DELETE"])
def delete_article(article_id):
    with sqlite3.connect(DB_PATH) as cx: cx.execute("DELETE FROM articles WHERE id=?", (article_id,)); cx.commit()
    return jsonify({"ok":True})

@app.route("/api/article/<article_id>/topic", methods=["PATCH"])
def update_topic(article_id):
    body = request.get_json(force=True)
    with sqlite3.connect(DB_PATH) as cx:
        cx.execute("UPDATE articles SET topic=?, tags=? WHERE id=?", (body.get("topic",""), json.dumps(body.get("tags",[])), article_id)); cx.commit()
    return jsonify({"ok":True})

# ── scheduler ─────────────────────────────────────────────────────────────────
def scheduler_loop(interval_hours=6):
    while True:
        time.sleep(interval_hours * 3600)
        log.info("Scheduler: triggering auto-sync …")
        for k in SCRAPERS:
            threading.Thread(target=run_sync, args=(k,), daemon=True).start()

if __name__ == "__main__":
    init_db()
    interval = float(os.environ.get("SYNC_INTERVAL_HOURS","6"))
    threading.Thread(target=scheduler_loop, args=(interval,), daemon=True).start()
    log.info(f"Scheduler started — auto-sync every {interval}h")
    log.info("Meridian server starting on http://localhost:4242")
    app.run(host="127.0.0.1", port=4242, debug=False)
