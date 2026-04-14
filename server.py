#!/usr/bin/env python3
"""
Meridian Scraper Server — v3
Correct URLs and selectors for FT, Economist, Foreign Affairs.
"""

import json, os, sys, time, hashlib, logging, threading, sqlite3, re, urllib.request, urllib.error
from datetime import datetime, timedelta
from pathlib import Path

_MONTHS = {
    'january':1,'february':2,'march':3,'april':4,'may':5,'june':6,
    'july':7,'august':8,'september':9,'october':10,'november':11,'december':12,
    'jan':1,'feb':2,'mar':3,'apr':4,'jun':6,'jul':7,'aug':8,
    'sep':9,'oct':10,'nov':11,'dec':12
}

def normalize_pub_date(d):
    """Normalise any pub_date string to ISO YYYY-MM-DD."""
    if not d or not str(d).strip():
        return ''
    d = str(d).strip()
    # Already ISO
    m = re.match(r'^(\d{4}-\d{2}-\d{2})', d)
    if m:
        return m.group(1)
    # DD Month YYYY e.g. '01 April 2026'
    m = re.match(r'^(\d{1,2})\s+(\w+)\s+(\d{4})$', d)
    if m:
        day, mon, year = int(m.group(1)), m.group(2).lower(), int(m.group(3))
        if mon in _MONTHS:
            return f'{year:04d}-{_MONTHS[mon]:02d}-{day:02d}'
    # Month D, YYYY e.g. 'April 2, 2026'
    m = re.match(r'^(\w+)\s+(\d{1,2}),\s+(\d{4})$', d)
    if m:
        mon, day, year = m.group(1).lower(), int(m.group(2)), int(m.group(3))
        if mon in _MONTHS:
            return f'{year:04d}-{_MONTHS[mon]:02d}-{day:02d}'
    # Month YYYY (no day) e.g. 'March 2026' -> 1st
    m = re.match(r'^(\w+)\s+(\d{4})$', d)
    if m:
        mon, year = m.group(1).lower(), int(m.group(2))
        if mon in _MONTHS:
            return f'{year:04d}-{_MONTHS[mon]:02d}-01'
    # X days ago
    m = re.match(r'^(\d+)\s+days?\s+ago$', d, re.I)
    if m:
        return (datetime.utcnow() - timedelta(days=int(m.group(1)))).strftime('%Y-%m-%d')
    if d.lower() == 'yesterday':
        return (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
    if d.lower() in ('today', 'now'):
        return datetime.utcnow().strftime('%Y-%m-%d')
    if re.match(r'^\d+\s+hours?\s+ago$', d, re.I):
        return datetime.utcnow().strftime('%Y-%m-%d')
    return d


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
        # -- Incremental Key Themes tables --
        cx.execute('CREATE TABLE IF NOT EXISTS article_theme_tags '
                   '(article_id TEXT NOT NULL, theme_name TEXT NOT NULL, tagged_at INTEGER NOT NULL,'
                   ' PRIMARY KEY (article_id, theme_name))')
        cx.execute('CREATE TABLE IF NOT EXISTS kt_themes '
                   '(name TEXT PRIMARY KEY, emoji TEXT DEFAULT "", keywords TEXT DEFAULT "[]",'
                   ' overview TEXT DEFAULT "", key_facts TEXT DEFAULT "[]",'
                   ' subtopics TEXT DEFAULT "[]", subtopic_details TEXT DEFAULT "{}",'
                   ' article_count INTEGER DEFAULT 0, last_updated INTEGER NOT NULL)')
        cx.execute('CREATE TABLE IF NOT EXISTS kt_meta '
                   '(key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        # -- Economist chart/map capture --
        cx.execute("""CREATE TABLE IF NOT EXISTS article_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id TEXT NOT NULL,
            caption TEXT NOT NULL,
            description TEXT DEFAULT '',
            image_data BLOB NOT NULL,
            width INTEGER DEFAULT 0,
            height INTEGER DEFAULT 0,
            captured_at INTEGER NOT NULL,
            FOREIGN KEY (article_id) REFERENCES articles(id)
        )""")
        # Add insight column if missing (added Session 27)
        ai_cols = [r[1] for r in cx.execute("PRAGMA table_info(article_images)").fetchall()]
        if 'insight' not in ai_cols:
            cx.execute("ALTER TABLE article_images ADD COLUMN insight TEXT DEFAULT ''")
        cx.commit()

def article_exists(aid):
    with sqlite3.connect(DB_PATH) as cx:
        return cx.execute("SELECT 1 FROM articles WHERE id=?", (aid,)).fetchone() is not None

def upsert_article(art):
    if art.get('pub_date'):
        art['pub_date'] = normalize_pub_date(art['pub_date'])
    with sqlite3.connect(DB_PATH) as cx:
        cx.execute("""INSERT OR REPLACE INTO articles
          (id,source,url,title,body,summary,topic,tags,saved_at,fetched_at,status,pub_date,auto_saved)
          VALUES (:id,:source,:url,:title,:body,:summary,:topic,:tags,:saved_at,:fetched_at,:status,:pub_date,:auto_saved)""",
          {**art, "auto_saved": art.get("auto_saved", 0)})
        cx.commit()

def all_articles(source=None, limit=500):
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        if source:
            rows = cx.execute("SELECT * FROM articles WHERE source=? ORDER BY COALESCE(NULLIF(pub_date,''),datetime(saved_at/1000,'unixepoch')) DESC LIMIT ?", (source, limit)).fetchall()
        else:
            rows = cx.execute("SELECT * FROM articles ORDER BY COALESCE(NULLIF(pub_date,''),datetime(saved_at/1000,'unixepoch')) DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

# ── credentials cache ────────────────────────────────────────────────────────
_creds_cache: dict = {}
_creds_mtime: float = 0.0

def load_creds() -> dict:
    """Return credentials, re-reading from disk only if the file has changed."""
    global _creds_cache, _creds_mtime
    if not CREDS.exists():
        return {}
    mtime = CREDS.stat().st_mtime
    if mtime != _creds_mtime:
        _creds_cache = json.loads(CREDS.read_text())
        _creds_mtime = mtime
        log.info("Credentials reloaded from disk")
    return _creds_cache

def save_creds(data):
    global _creds_cache, _creds_mtime
    CREDS.write_text(json.dumps(data, indent=2))
    os.chmod(CREDS, 0o600)
    _creds_cache = data
    _creds_mtime = CREDS.stat().st_mtime

# ── shared Anthropic API helper ───────────────────────────────────────────────
def call_anthropic(payload: dict, timeout: int = 30, retries: int = 2) -> dict:
    """POST to Anthropic /v1/messages with retry on 429. Raises on failure."""
    api_key = load_creds().get("anthropic_api_key", "")
    if not api_key:
        raise RuntimeError("No Anthropic API key configured")
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    for attempt in range(retries):
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=data,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                wait = 15 * (attempt + 1)
                log.warning(f"Anthropic 429 — retrying in {wait}s (attempt {attempt+1})")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("call_anthropic: exhausted retries")

def make_id(source, url):
    return hashlib.sha1(f"{source}:{url}".encode()).hexdigest()[:16]

def now_ts():
    return int(time.time() * 1000)

def enrich_article_with_ai(art):
    """Send article text to Claude API for summary, key points and tags.
    Only called for articles with body text. Updates art dict in place."""
    api_key = load_creds().get("anthropic_api_key", "")
    if not api_key or api_key == "TEST_VALUE_123":
        log.warning("No API key — skipping AI enrichment")
        return art

    body_text = art.get("body", "")
    if not body_text or len(body_text) < 200:
        log.info(f"Skipping AI enrichment for '{art.get('title','')[:50]}' — body too short")
        return art

    prompt = f"""You are a research assistant. Analyse this article and respond ONLY with a JSON object (no markdown):
{{
  "summary": "2-3 sentence summary of the main argument",
  "fullSummary": "4-6 paragraph detailed analysis",
  "keyPoints": ["point 1", "point 2", "point 3", "point 4"],
  "tags": ["tag1", "tag2", "tag3"],
  "topic": "pick from: Markets, Economics, Geopolitics, Technology, Politics, Business, Energy, Finance, Society, Science — or invent a new max 2-word topic if none fit",
  "pub_date": "publication date in YYYY-MM-DD format e.g. 2026-03-27, or empty string if unknown"
}}

Article title: {art.get('title','')}
Article source: {art.get('source','')}

Article text:
{body_text[:8000]}"""

    try:
        data = call_anthropic({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}]
        })
        text = data["content"][0]["text"]
        parsed = json.loads(text.replace("```json","").replace("```","").strip())
        art["summary"]  = parsed.get("summary", art.get("summary",""))
        # Do NOT overwrite body with fullSummary — preserve raw scraped text as body
        # fullSummary is stored only if body is currently empty
        if not art.get("body") or len(art.get("body","")) < 200:
            art["body"] = parsed.get("fullSummary", art.get("body",""))
        art["tags"]     = json.dumps(parsed.get("tags", []))
        art["topic"]    = parsed.get("topic", art.get("topic",""))
        # Only use Claude's pub_date if we don't already have one from URL extraction
        if not art.get("pub_date"):
            art["pub_date"] = parsed.get("pub_date", "")
        art["status"]   = "full_text"
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
            raw = time_el["datetime"]
            m = re.match(r'(\d{4}-\d{2}-\d{2})', raw)
            pub_date = m.group(1) if m else raw
        if not pub_date:
            # fallback: look for "Published" text near a date
            for el in soup.select("div[class*='date'], span[class*='date'], div[class*='timestamp']"):
                txt = el.get_text(strip=True)
                if txt:
                    pub_date = txt; break
        # FT article body selectors — updated for FT's current markup (o3/n-content classes)
        paragraphs = (
            soup.select("div.n-content-body p") or
            soup.select("div[class*='n-content-body'] p") or
            soup.select("div[class*='article__content'] p") or
            soup.select("div[class*='article-body'] p") or
            soup.select("div[class*='body-text'] p")
        )
        text = " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30)
        return text, pub_date
    except Exception as e:
        log.warning(f"FT fetch text error for {url}: {e}")
        return "", ""

def fetch_bloomberg_article_text(page, url):
    """Fetch full text and pub_date of a Bloomberg article using logged-in browser page."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
        page.wait_for_timeout(3000)
        soup = BeautifulSoup(page.content(), "html.parser")
        # Bloomberg article body selectors
        paragraphs = (
            soup.select("div.body-content p") or
            soup.select("div[class*='body-copy'] p") or
            soup.select("article p") or
            soup.select("div[class*='article-body'] p")
        )
        text = " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40)
        pub_date = ""
        meta = soup.select_one("meta[property='article:published_time'], time[datetime]")
        if meta:
            raw = meta.get("content") or meta.get("datetime") or ""
            m = re.match(r'(\d{4}-\d{2}-\d{2})', raw)
            pub_date = m.group(1) if m else raw
        return text, pub_date
    except Exception as e:
        log.warning(f"Bloomberg fetch text error for {url}: {e}")
        return "", ""

def fetch_fa_article_text(page, url):
    """Fetch full text and pub_date of a Foreign Affairs article using logged-in browser page."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
        page.wait_for_timeout(3000)
        soup = BeautifulSoup(page.content(), "html.parser")
        # FA uses article__body-content (confirmed via Playwright inspection April 2026)
        paragraphs = (
            soup.select("div.article__body-content p") or
            soup.select("section.rich-text p") or
            soup.select("div.article__body p") or
            soup.select("div.article-body p") or
            soup.select("main p")
        )
        text = " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40)
        # pub_date from meta tag — normalise to YYYY-MM-DD for consistent JS parsing
        pub_date = ""
        meta = soup.select_one("meta[property='article:published_time'], meta[name='pubdate']")
        if meta and meta.get("content"):
            raw = meta["content"]
            # Extract just the date part from ISO strings like 2026-03-05T00:00:00-05:00
            m = re.match(r'(\d{4}-\d{2}-\d{2})', raw)
            pub_date = m.group(1) if m else raw
        return text, pub_date
    except Exception as e:
        log.warning(f"FA fetch text error for {url}: {e}")
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

def capture_economist_charts(page, article_id):
    """Capture charts and maps from the current Economist article page.
    Page must already be loaded. Finds all <figure> elements whose <figcaption>
    contains 'Chart:' or 'Map:', screenshots them, generates AI descriptions.
    Saves to article_images table. Skips article if images already captured.
    Returns count of images captured."""
    import base64 as _b64

    # Skip if already captured
    with sqlite3.connect(DB_PATH) as cx:
        existing = cx.execute(
            "SELECT COUNT(*) FROM article_images WHERE article_id=?", (article_id,)
        ).fetchone()[0]
    if existing > 0:
        log.info(f"Charts: article {article_id} already has {existing} images — skipping")
        return 0

    try:
        # Scroll fully to trigger lazy-loading of all images
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1500)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)

        # Find all figure elements with Chart: or Map: captions
        figures = page.locator("figure").all()
        captured = 0
        ts = now_ts()

        for fig in figures:
            try:
                caption_el = fig.locator("figcaption").first
                if caption_el.count() == 0:
                    continue
                caption_text = caption_el.inner_text(timeout=2000).strip()
                caption_lower = caption_text.lower()
                if not ("chart:" in caption_lower or "map:" in caption_lower):
                    continue

                # Scroll figure into view to ensure it's rendered
                fig.scroll_into_view_if_needed(timeout=3000)
                page.wait_for_timeout(500)

                # Screenshot the figure element as PNG bytes
                png_bytes = fig.screenshot(timeout=10000)
                if not png_bytes or len(png_bytes) < 1000:
                    log.info(f"Charts: figure too small ({len(png_bytes)} bytes) — skipping")
                    continue

                # Get dimensions from bounding box
                bbox = fig.bounding_box()
                width = int(bbox['width']) if bbox else 0
                height = int(bbox['height']) if bbox else 0

                # Generate AI description via Claude Haiku with vision
                description = ""
                try:
                    img_b64 = _b64.b64encode(png_bytes).decode('utf-8')
                    desc_resp = call_anthropic({
                        "model": "claude-haiku-4-5-20251001",
                        "max_tokens": 120,
                        "messages": [{
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/png",
                                        "data": img_b64
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": "Describe this chart or map in one concise sentence (max 25 words). Focus on what data it shows, key trend or geographic subject. No preamble."
                                }
                            ]
                        }]
                    }, timeout=20)
                    description = desc_resp["content"][0]["text"].strip()
                except Exception as de:
                    log.warning(f"Charts: AI description failed for {article_id}: {de}")
                    description = caption_text[:100]

                # Save to DB
                with sqlite3.connect(DB_PATH) as cx:
                    cx.execute(
                        "INSERT INTO article_images (article_id, caption, description, image_data, width, height, captured_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (article_id, caption_text, description, png_bytes, width, height, ts)
                    )
                captured += 1
                log.info(f"Charts: captured '{caption_text[:40]}' for {article_id} ({len(png_bytes)} bytes) — '{description[:60]}'")

            except Exception as fe:
                log.warning(f"Charts: figure error for {article_id}: {fe}")
                continue

        log.info(f"Charts: {captured} images captured for article {article_id}")
        return captured

    except Exception as e:
        log.warning(f"Charts: capture failed for {article_id}: {e}")
        return 0


# ── Image insight enrichment ──────────────────────────────────────────────────
_insight_job = {"running": False, "total": 0, "done": 0, "enriched": 0, "error": None, "started_at": None}

def enrich_image_insights():
    """Generate insight strings for all article_images rows that have empty insight.
    Insight = what analytical point this chart supports in the context of its source article.
    Uses Haiku vision + article title/summary. Runs as async job after backfill completes,
    and incrementally after each sync to pick up new images."""
    import base64 as _b64
    global _insight_job

    with sqlite3.connect(DB_PATH) as cx:
        rows = cx.execute("""
            SELECT ai.id, ai.article_id, ai.caption, ai.description, ai.image_data,
                   a.title, a.summary
            FROM article_images ai
            JOIN articles a ON ai.article_id = a.id
            WHERE ai.insight = '' OR ai.insight IS NULL
        """).fetchall()

    if not rows:
        log.info("Insight enrichment: nothing to do")
        return 0

    log.info(f"Insight enrichment: {len(rows)} images to process")
    _insight_job.update({"running": True, "total": len(rows), "done": 0, "enriched": 0,
                         "error": None, "started_at": now_ts()})
    enriched = 0

    for i, row in enumerate(rows):
        img_id, article_id, caption, description, image_data, title, summary = row
        try:
            img_b64 = _b64.b64encode(image_data).decode("utf-8")
            prompt = (
                f"This chart appears in an Economist article titled: '{title}'\n"
                f"The article argues: {(summary or '')[:300]}\n"
                f"The chart shows: {description}\n\n"
                "In ONE sentence (max 30 words), explain what analytical point or argument this chart "
                "supports in the context of that article. Be specific — name the trend, statistic, or "
                "conclusion it evidences. No preamble."
            )
            resp = call_anthropic({
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 80,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_b64}},
                        {"type": "text", "text": prompt}
                    ]
                }]
            }, timeout=20)
            insight = resp["content"][0]["text"].strip()
            with sqlite3.connect(DB_PATH) as cx:
                cx.execute("UPDATE article_images SET insight=? WHERE id=?", (insight, img_id))
            enriched += 1
            log.info(f"Insight [{i+1}/{len(rows)}] img {img_id}: {insight[:80]}")
        except Exception as e:
            log.warning(f"Insight enrichment: failed for img {img_id}: {e}")
        finally:
            _insight_job["done"] = i + 1
            _insight_job["enriched"] = enriched
        # Rate limit: 1s between calls, extra pause every 20
        time.sleep(1)
        if (i + 1) % 20 == 0:
            time.sleep(10)

    _insight_job["running"] = False
    log.info(f"Insight enrichment: done — {enriched}/{len(rows)} images enriched")
    return enriched

@app.route("/api/images/enrich-insights", methods=["POST"])
def enrich_insights_route():
    """Async job: generate insight strings for all images missing them."""
    if _insight_job.get("running"):
        return jsonify({"ok": False, "error": "Already running"}), 409
    threading.Thread(target=enrich_image_insights, daemon=True).start()
    return jsonify({"ok": True, "started": True})

@app.route("/api/images/enrich-insights/status", methods=["GET"])
def enrich_insights_status():
    with sqlite3.connect(DB_PATH) as cx:
        pending = cx.execute(
            "SELECT COUNT(*) FROM article_images WHERE insight='' OR insight IS NULL"
        ).fetchone()[0]
    return jsonify({**_insight_job, "pending": pending})


# ── Backfill job state ────────────────────────────────────────────────────────
_backfill_job = {"running": False, "total": 0, "done": 0, "captured": 0, "error": None, "started_at": None}


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
    """Scrapes FT myFT saved articles. Paginates through all pages,
    stopping when an entire page consists only of articles already in DB."""
    name = "Financial Times"
    SAVED_URL = "https://www.ft.com/myft/saved-articles/197493b5-7e8e-4f13-8463-3c046200835c"

    def __init__(self, email="", password=""):
        pass

    def scrape(self):
        if not PLAYWRIGHT_OK:
            raise RuntimeError("playwright not installed")
        profile_dir = BASE_DIR / "ft_profile"
        profile_dir.mkdir(exist_ok=True)
        articles = []

        JUNK_PREFIXES = (
            "FT quiz:", "Letter:", "FTAV's further reading",
            "FT News Briefing", "Correction:", "The best books of the week",
        )
        JUNK_SUBSTRINGS = (" live:", " as it happened", "live blog")

        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                str(profile_dir), headless=True,
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
            page = browser.new_page()
            try:
                log.info("FT: opening saved articles page 1")
                page.goto(self.SAVED_URL, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(3000)

                if "login" in page.url or "signin" in page.url:
                    log.info("FT: login required — waiting 90s")
                    page.wait_for_timeout(90000)
                    page.goto(self.SAVED_URL, wait_until="domcontentloaded", timeout=40000)
                    page.wait_for_timeout(3000)

                page_num = 1
                while True:
                    soup = BeautifulSoup(page.content(), "html.parser")
                    cards = soup.select("div.o-teaser, li.o-teaser, article")
                    log.info("FT: page %d — %d cards" % (page_num, len(cards)))

                    page_articles = []
                    for card in cards:
                        a = card.select_one("a[href*='/content/']")
                        if not a:
                            continue
                        href = a.get("href", "")
                        url = ("https://www.ft.com" + href if href.startswith("/") else href).split("?")[0]
                        title_el = card.select_one(".o-teaser__heading, h3, h2")
                        title = title_el.get_text(strip=True) if title_el else a.get_text(strip=True)
                        if not title or len(title) < 5:
                            continue
                        if any(title.startswith(pf) for pf in JUNK_PREFIXES):
                            continue
                        if any(s in title.lower() for s in JUNK_SUBSTRINGS):
                            continue
                        art_id = make_id(self.name, url)
                        cat_el = card.select_one(".o-teaser__tag, .o-teaser__concept")
                        category = cat_el.get_text(strip=True) if cat_el else ""
                        page_articles.append({
                            "id": art_id, "source": self.name, "url": url,
                            "title": title, "body": "", "summary": "", "topic": category,
                            "tags": "[]", "saved_at": now_ts(), "fetched_at": now_ts(),
                            "status": "fetched", "pub_date": "", "auto_saved": 0,
                        })

                    if not page_articles:
                        log.info("FT: no articles on page %d — stopping" % page_num)
                        break

                    new_on_page = [a for a in page_articles if not article_exists(a["id"])]
                    existing_on_page = [a for a in page_articles if article_exists(a["id"])]
                    log.info("FT: page %d — %d new, %d existing" % (page_num, len(new_on_page), len(existing_on_page)))

                    # Fetch full text for new articles immediately
                    for art in new_on_page:
                        log.info("FT: fetching text for '%s'" % art["title"][:55])
                        text, pub_date = fetch_ft_article_text(page, art["url"])
                        if pub_date:
                            art["pub_date"] = pub_date
                        if text:
                            art["body"] = text
                            enrich_article_with_ai(art)
                        else:
                            art["status"] = "title_only"
                        # Navigate back to saved page after fetching text
                        page.goto(self.SAVED_URL, wait_until="domcontentloaded", timeout=30000)
                        page.wait_for_timeout(2000)
                        if page_num > 1:
                            # Re-navigate to correct page
                            try:
                                for _ in range(page_num - 1):
                                    nxt = page.locator("a[aria-label='Next page'], a[rel='next']").first
                                    if nxt.is_visible(timeout=2000):
                                        nxt.click()
                                        page.wait_for_timeout(2000)
                            except Exception:
                                pass

                    articles.extend(new_on_page)

                    # Stop if entire page already in DB
                    if len(existing_on_page) == len(page_articles):
                        log.info("FT: all articles on page %d already in DB — stopping" % page_num)
                        break

                    # Go to next page
                    try:
                        next_loc = page.locator("a[aria-label='Next page'], a[rel='next']").first
                        if next_loc.is_visible(timeout=2000):
                            next_loc.click()
                            page.wait_for_timeout(3000)
                            page_num += 1
                        else:
                            log.info("FT: no next page at page %d — stopping" % page_num)
                            break
                    except Exception:
                        log.info("FT: pagination ended at page %d" % page_num)
                        break

                log.info("FT: scraped %d new articles across %d pages" % (len(articles), page_num))

            except Exception as e:
                log.error("FT error: %s" % e, exc_info=True)
            finally:
                browser.close()

        return articles


class EconomistScraper:
    """Scrapes Economist bookmarks via CDP subprocess (headless, avoids Flask event loop conflict).
    Clicks Load More until the last revealed batch is entirely existing articles."""
    name = "The Economist"
    CHROME_BIN  = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    CDP_PORT    = 9223
    CDP_PROFILE = BASE_DIR / "eco_chrome_profile"

    def __init__(self, email="", password=""):
        pass

    def scrape(self):
        import subprocess as _sp, json as _json, tempfile as _tmp, sys as _sys, os as _os
        self.CDP_PROFILE.mkdir(exist_ok=True)

        # Pass known IDs to subprocess so it can stop when all new batch is already in DB
        with sqlite3.connect(DB_PATH) as _cx:
            known_ids = [r[0] for r in _cx.execute(
                "SELECT id FROM articles WHERE source='The Economist'"
            ).fetchall()]

        ids_file = _tmp.NamedTemporaryFile(suffix='.json', mode='w', delete=False)
        _json.dump(known_ids, ids_file)
        ids_file.close()

        out_file = _tmp.NamedTemporaryFile(suffix='.json', delete=False)
        out_file.close()

        sub = _sp.run(
            [_sys.executable,
             str(BASE_DIR / "eco_scraper_sub.py"),
             str(self.CDP_PROFILE), str(self.CDP_PORT),
             out_file.name, ids_file.name],
            timeout=300, capture_output=True, text=True
        )
        _os.unlink(ids_file.name)

        articles = []
        if sub.returncode != 0:
            log.error("Economist subprocess failed: " + sub.stderr[:300])
        else:
            log.info("Economist subprocess: " + sub.stderr[-400:])
            try:
                result = _json.loads(open(out_file.name).read())
                articles = result.get("articles", [])
                if result.get("error"):
                    log.error("Economist subprocess error: " + str(result["error"]))
            except Exception as e:
                log.error("Economist subprocess JSON error: " + str(e))
        _os.unlink(out_file.name)
        log.info("Economist: %d new articles found" % len(articles))

        if articles:
            articles = self._fetch_texts(articles)
        return articles

    def _fetch_texts(self, articles):
        import subprocess as _sp, json as _json, tempfile as _tmp, sys as _sys, os as _os
        in_f = _tmp.NamedTemporaryFile(suffix='.json', mode='w', delete=False)
        _json.dump([{"id": a["id"], "url": a["url"], "title": a["title"]} for a in articles], in_f)
        in_f.close()
        out_f = _tmp.NamedTemporaryFile(suffix='.json', delete=False)
        out_f.close()

        sub = _sp.run(
            [_sys.executable, str(BASE_DIR / "eco_fetch_sub.py"),
             str(self.CDP_PROFILE), str(self.CDP_PORT), in_f.name, out_f.name],
            timeout=600, capture_output=True, text=True
        )
        _os.unlink(in_f.name)
        log.info("Economist fetch: " + sub.stderr[-300:])

        try:
            results = _json.loads(open(out_f.name).read())
            by_id = {r["id"]: r for r in results}
            for art in articles:
                fetched = by_id.get(art["id"], {})
                body = fetched.get("body", "")
                if body:
                    art["body"] = body
                    art["status"] = "fetched"
                    enrich_article_with_ai(art)
                else:
                    art["status"] = "title_only"
        except Exception as e:
            log.error("Economist fetch parse error: " + str(e))
        _os.unlink(out_f.name)
        return articles


class ForeignAffairsScraper:
    """Scrapes Foreign Affairs from three sources:
    1. Saved articles page (your FA bookmarks)
    2. Two most recent issues (dynamically discovered from /issues landing page)
    3. Most-read page
    Uses h3 a selector — consistent article title heading across all FA pages.
    Deduplication via article_exists(). Cookie expires 2026-05-23."""

    BASE = "https://www.foreignaffairs.com"
    SAVED_URL = BASE + "/my-foreign-affairs/saved-articles"
    ISSUES_URL = BASE + "/issues"
    MOST_READ_URL = BASE + "/most-read"

    SKIP_PREFIXES = (
        "/issues/", "/topics/", "/tags/", "/my-foreign-affairs/",
        "/account", "/login", "/subscribe", "/podcast", "/newsletter",
        "/about", "/contact", "/search", "/archive", "/books",
        "/regions/", "/sections/", "/graduate", "/permissions",
        "/gift", "/audio", "/video", "/events", "/browse/",
        "/authors/", "/staff", "/collections/",
    )

    def __init__(self, email="", password=""):
        pass

    def scrape(self):
        if not PLAYWRIGHT_OK:
            raise RuntimeError("playwright not installed")
        profile_dir = BASE_DIR / "fa_profile"
        profile_dir.mkdir(exist_ok=True)
        articles = []
        seen = set()

        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                str(profile_dir), headless=True,
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
            page = browser.new_page()
            try:
                # 1. Saved articles
                saved = self._scrape_page(page, self.SAVED_URL, seen, "saved", requires_login=True)
                articles.extend(saved)
                log.info("FA: saved articles — %d new" % len(saved))

                # 2. Two most recent issues (discovered dynamically)
                issue_urls = self._discover_issues(page)
                for issue_url in issue_urls:
                    issue_arts = self._scrape_page(page, issue_url, seen, "issue")
                    articles.extend(issue_arts)
                    log.info("FA: issue %s — %d new" % (issue_url, len(issue_arts)))

                # 3. Most read
                most_read = self._scrape_page(page, self.MOST_READ_URL, seen, "most-read")
                articles.extend(most_read)
                log.info("FA: most-read — %d new" % len(most_read))

                # Fetch full text + enrich all new articles
                log.info("FA: %d new articles total — fetching text" % len(articles))
                for art in articles:
                    log.info("FA: fetching '%s'" % art["title"][:55])
                    text, pub_date = fetch_fa_article_text(page, art["url"])
                    if pub_date:
                        art["pub_date"] = pub_date
                    if text:
                        art["body"] = text
                        enrich_article_with_ai(art)
                    else:
                        art["status"] = "title_only"
                        log.info("FA: no text for '%s'" % art["title"][:50])

            except Exception as e:
                log.error("FA error: %s" % e, exc_info=True)
            finally:
                browser.close()

        return articles

    def _discover_issues(self, page):
        """Discover the two most recent issue URLs from the /issues landing page."""
        try:
            page.goto(self.ISSUES_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)
            from bs4 import BeautifulSoup as _BS
            soup = _BS(page.content(), "html.parser")
            seen_urls = []
            for a in soup.select("a[href]"):
                href = a.get("href", "")
                if "/issues/20" in href and href not in seen_urls:
                    seen_urls.append(href)
                if len(seen_urls) >= 2:
                    break
            if seen_urls:
                log.info("FA: discovered issues: %s" % seen_urls)
                return [self.BASE + u if u.startswith("/") else u for u in seen_urls]
        except Exception as e:
            log.warning("FA: issue discovery failed: %s" % e)
        # Fallback to known recent issues
        return [self.BASE + "/issues/2026/105/2", self.BASE + "/issues/2026/105/1"]

    def _scrape_page(self, page, url, seen, label, requires_login=False):
        """Navigate to a page and extract new FA articles using h3 a selector."""
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(3000)

            if requires_login and ("sign-in" in page.url or "login" in page.url):
                if not self._login(page):
                    log.warning("FA: login failed — skipping %s" % label)
                    return []
                page.goto(url, wait_until="domcontentloaded", timeout=40000)
                page.wait_for_timeout(3000)

            # Scroll to load lazy content on saved/most-read pages
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1500)

            return self._extract_articles(page, label, seen)

        except Exception as e:
            log.warning("FA: %s scrape failed: %s" % (label, e))
            return []

    def _extract_articles(self, page, label, seen):
        """Extract new articles from current page using h3 a selector.
        h3 elements are article title headings consistently across all FA pages."""
        from bs4 import BeautifulSoup as _BS
        soup = _BS(page.content(), "html.parser")
        new_articles = []

        for h3 in soup.select("h3"):
            a = h3.find("a", href=True)
            if not a:
                # Also try: the h3 itself might be wrapped in an <a>
                parent_a = h3.find_parent("a", href=True)
                if parent_a:
                    a = parent_a
            if not a:
                continue

            href = a.get("href", "")
            title = h3.get_text(strip=True)

            # Must be a relative FA path
            if not href.startswith("/"):
                continue

            # Skip known non-article prefixes
            if any(href.startswith(p) for p in self.SKIP_PREFIXES):
                continue

            # Must have at least 2 path segments
            parts = [p for p in href.split("?")[0].split("/") if p]
            if len(parts) < 2:
                continue

            # Title must be meaningful
            if not title or len(title) < 8:
                continue

            url = self.BASE + href.split("?")[0]
            art_id = make_id("Foreign Affairs", url)

            if art_id in seen:
                continue
            seen.add(art_id)

            if article_exists(art_id):
                continue

            new_articles.append({
                "id": art_id,
                "source": "Foreign Affairs",
                "url": url,
                "title": title[:200],
                "body": "",
                "summary": "",
                "topic": "",
                "tags": "[]",
                "saved_at": now_ts(),
                "fetched_at": now_ts(),
                "status": "fetched",
                "pub_date": "",
                "auto_saved": 0,
            })

        log.info("FA: extracted %d new articles from %s page" % (len(new_articles), label))
        return new_articles


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
        # Persist last successful scrape time to kt_meta
        with sqlite3.connect(DB_PATH) as _cx:
            _cx.execute("INSERT OR REPLACE INTO kt_meta (key, value) VALUES (?, ?)",
                        (f"last_sync_{source_key}", datetime.now().isoformat(timespec="seconds")))
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
    # then score new FT/Economist articles for auto-save
    def _enrich_after_sync():
        for t in threads:
            t.join()
        log.info("Sync all complete — running title-only enrichment")
        enrich_title_only_articles()
        enrich_fetched_articles()
        # score_and_autosave_new_articles() removed — AI picks sourced from
        # homepage scraping only, never retrospectively from saved lists.
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

@app.route("/api/sync/last-run")
def sync_last_run():
    """Return last successful scrape time per source from kt_meta."""
    with sqlite3.connect(DB_PATH) as cx:
        rows = cx.execute(
            "SELECT key, value FROM kt_meta WHERE key LIKE 'last_sync_%'"
        ).fetchall()
    result = {}
    for key, value in rows:
        source = key.replace("last_sync_", "")
        result[source] = value
    return jsonify(result)

@app.route("/api/ai-pick/economist-weekly", methods=["POST"])
def api_ai_pick_economist_weekly():
    """Trigger Economist weekly edition AI pick. Can be called manually or by scheduler."""
    def _run():
        try:
            feed, suggested = ai_pick_economist_weekly()
            log.info(f"Economist weekly endpoint: {len(feed)} Feed, {len(suggested)} Suggested")
        except Exception as e:
            log.warning(f"Economist weekly endpoint error: {e}")
    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok": True, "message": "Economist weekly pick started"})

@app.route("/api/ai-pick", methods=["POST"])
def api_ai_pick():
    """Trigger AI pick feed scrape. Called by wake_and_sync.sh after scrape completes."""
    def _run():
        try:
            feed, suggested = ai_pick_feed_scrape()
            log.info(f"AI pick endpoint: {len(feed)} Feed, {len(suggested)} Suggested")
        except Exception as e:
            log.warning(f"AI pick endpoint error: {e}")
    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok": True, "message": "AI pick started"})

@app.route("/api/sync/status")
def sync_status_route():
    return jsonify(sync_status)

def enrich_title_only_articles():
    """Fetch full text for all title_only articles. Uses logged-in profiles for FT/Eco/FA, generic scrape for others."""
    import urllib.request as _ur
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        rows = cx.execute("SELECT * FROM articles WHERE status IN ('title_only','agent') AND url!=''").fetchall()
    arts = [dict(r) for r in rows]
    if not arts:
        log.info("Enrich title-only: nothing to do")
        return 0
    log.info(f"Enrich title-only: {len(arts)} articles to process")

    ft_arts  = [a for a in arts if a["source"] == "Financial Times"]
    eco_arts = [a for a in arts if a["source"] == "The Economist"]
    fa_arts  = [a for a in arts if a["source"] == "Foreign Affairs"]
    bbg_arts = [a for a in arts if a["source"] == "Bloomberg"]
    other_arts = [a for a in arts if a["source"] not in ("Financial Times","The Economist","Foreign Affairs","Bloomberg")]
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

    # Economist — use subprocess to avoid Flask event loop conflict
    if eco_arts and PLAYWRIGHT_OK:
        import subprocess as _sp2, json as _ej, tempfile as _etmp, sys as _esys
        sub_script = str(BASE_DIR / "eco_fetch_sub.py")
        urls_and_ids = [{"id": a["id"], "url": a["url"], "title": a["title"]} for a in eco_arts]
        _in = _etmp.NamedTemporaryFile(suffix='.json', mode='w', delete=False)
        _ej.dump(urls_and_ids, _in); _in.close()
        _out2 = _etmp.NamedTemporaryFile(suffix='.json', delete=False); _out2.close()
        sub2 = _sp2.run(
            [_esys.executable, sub_script,
             str(BASE_DIR / "eco_chrome_profile"), "9223", _in.name, _out2.name],
            timeout=180, capture_output=True, text=True
        )
        import os as _os2
        _os2.unlink(_in.name)
        if sub2.returncode != 0:
            log.warning(f"Enrich title-only: Economist subprocess failed: {sub2.stderr[:200]}")
        else:
            try:
                results = _ej.loads(open(_out2.name).read())
                for item in results:
                    art = next((a for a in eco_arts if a["id"] == item["id"]), None)
                    if art and item.get("body"):
                        art["body"] = item["body"]
                        if item.get("pub_date") and not art.get("pub_date"):
                            art["pub_date"] = item["pub_date"]
                        with sqlite3.connect(DB_PATH) as cx:
                            cx.execute("UPDATE articles SET body=?, pub_date=?, status='fetched' WHERE id=?",
                                       (art["body"], art.get("pub_date",""), art["id"]))
                        enrich_article_with_ai(art)
                        _save_enriched_article(art)
                        enriched += 1
                        log.info(f"Enrich title-only: Economist fetched '{art['title'][:50]}'")
                    else:
                        title = item.get("title","?")
                        log.warning(f"Enrich title-only: Economist no text for '{title[:50]}'")
            except Exception as _eje:
                log.warning(f"Enrich title-only: Economist result parse failed: {_eje}")
        _os2.unlink(_out2.name)

    # Foreign Affairs — use fa_profile with fetch_fa_article_text (same as main scraper)
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
                        text, pub_date = fetch_fa_article_text(page, a["url"])
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
                            log.info(f"Enrich title-only: FA fetched '{a['title'][:50]}'")
                        else:
                            log.warning(f"Enrich title-only: FA got no text for '{a['title'][:50]}'")
                    except Exception as e:
                        log.warning(f"Enrich title-only: FA fetch failed for {a['url']}: {e}")
                browser.close()
        except Exception as e:
            log.warning(f"Enrich title-only: FA Playwright failed: {e}")

    # Bloomberg — use bloomberg_profile
    if bbg_arts and PLAYWRIGHT_OK:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                browser = pw.chromium.launch_persistent_context(
                    str(BASE_DIR / "bloomberg_profile"),
                    headless=True, args=["--no-sandbox"]
                )
                page = browser.pages[0] if browser.pages else browser.new_page()
                for a in bbg_arts:
                    text, pub_date = fetch_bloomberg_article_text(page, a["url"])
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
                        log.info(f"Enrich title-only: Bloomberg fetched '{a['title'][:50]}'")
                    else:
                        log.warning(f"Enrich title-only: Bloomberg no text for '{a['title'][:50]}' — may need re-auth")
                browser.close()
        except Exception as e:
            log.warning(f"Enrich title-only: Bloomberg Playwright failed: {e}")

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
def enrich_fetched_articles():
    """Enrich articles that have body text but no AI summary/topic/tags.
    Covers full_text and fetched articles that slipped through the pipeline.
    Does NOT fetch text — only calls enrich_article_with_ai() on existing body."""
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        rows = cx.execute("""
            SELECT * FROM articles
            WHERE (summary IS NULL OR summary = '')
            AND body IS NOT NULL AND LENGTH(body) > 200
            AND status IN ('full_text', 'fetched')
        """).fetchall()
    arts = [dict(r) for r in rows]
    if not arts:
        log.info("Enrich fetched: nothing to do")
        return 0
    log.info(f"Enrich fetched: {len(arts)} articles need AI enrichment")
    enriched = 0
    for a in arts:
        try:
            result = enrich_article_with_ai(a)
            if result and result.get('summary'):
                _save_enriched_article(result)
                enriched += 1
                log.info(f"Enrich fetched: enriched '{a['title'][:50]}'")
        except Exception as e:
            log.warning(f"Enrich fetched: failed for '{a['title'][:40]}': {e}")
    log.info(f"Enrich fetched: done — {enriched}/{len(arts)} enriched")
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
            enrich_fetched_articles()
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
        cx.row_factory = sqlite3.Row
        row = cx.execute("SELECT * FROM articles WHERE id=?", (aid,)).fetchone()
        if not row:
            return jsonify({"ok": False, "error": "Not found"}), 404
        art = dict(row)
    enriched = enrich_article_with_ai(art)
    summary = enriched.get("summary", "")
    if summary:
        with sqlite3.connect(DB_PATH) as cx2:
            cx2.execute(
                "UPDATE articles SET summary=?, tags=?, topic=?, pub_date=? WHERE id=?",
                (summary, enriched.get("tags","[]"), enriched.get("topic",""),
                 enriched.get("pub_date", art.get("pub_date","")), aid)
            )
    return jsonify({"ok": True, "summary_len": len(summary)})

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



def ai_pick_feed_scrape():
    """Scrape personalised FT and Economist recommendation feeds + FA most-read.
    Pass unsaved articles to Sonnet for relevance scoring.
    score >=9  -> Feed (auto_saved=1)
    score 6-8  -> Suggested inbox

    FT: uses _feedTimelineTeasers JS variable — gives title, URL, publishedDate, standfirst
    Economist: subprocess off-screen Chrome (feed pages blocked, skip for now)
    FA: plain HTTP fetch (public page)
    Gate: twice daily keyed as ai_pick_last_run_morning / ai_pick_last_run_midday.
    """
    import json as _j
    import urllib.request as _ur
    import os as _os
    import tempfile as _tf
    import subprocess as _sp

    # ── Gate: twice daily ────────────────────────────────────────────────────
    _now_h = datetime.now().hour
    _gate_key = 'ai_pick_last_run_morning' if _now_h < 12 else 'ai_pick_last_run_midday'
    _today = datetime.now().strftime('%Y-%m-%d')
    with sqlite3.connect(DB_PATH) as _gx:
        _gx.execute("CREATE TABLE IF NOT EXISTS kt_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        _last = _gx.execute("SELECT value FROM kt_meta WHERE key=?", (_gate_key,)).fetchone()
    if _last and _last[0] == _today:
        log.info(f"AI pick: already ran today [{_gate_key}] — skipping")
        return [], []

    # ── Build known URLs ──────────────────────────────────────────────────────
    with sqlite3.connect(DB_PATH) as _cx:
        _saved = set(r[0] for r in _cx.execute("SELECT url FROM articles WHERE url!=''").fetchall())
        _suggested = set(r[0] for r in _cx.execute("SELECT url FROM suggested_articles WHERE url!=''").fetchall())
    _known = _saved | _suggested

    # ── Build interest profile ────────────────────────────────────────────────
    with sqlite3.connect(DB_PATH) as _cx:
        _rows = _cx.execute("SELECT topic, tags FROM articles ORDER BY saved_at DESC LIMIT 150").fetchall()
    _counts = {}
    for _topic, _tags in _rows:
        if _topic: _counts[_topic] = _counts.get(_topic, 0) + 1
        try:
            for _t in _j.loads(_tags or "[]"):
                _counts[_t] = _counts.get(_t, 0) + 1
        except: pass
    _interests = ", ".join(sorted(_counts, key=lambda x: -_counts[x])[:15]) or "geopolitics, economics, finance, markets"
    log.info(f"AI pick: interests = {_interests[:80]}")

    candidates = []

    # ── 1. FT personalised feed — extract _feedTimelineTeasers JS variable ────
    FT_FEED = "https://www.ft.com/myft/following/197493b5-7e8e-4f13-8463-3c046200835c/time"
    try:
        _ft_script = _tf.NamedTemporaryFile(mode='w', suffix='.py', delete=False, dir='/tmp')
        _ft_out = _tf.NamedTemporaryFile(mode='w', suffix='.json', delete=False, dir='/tmp')
        _ft_script_path = _ft_script.name
        _ft_out_path = _ft_out.name
        _ft_script.write(f"""
import json, os, sys
from playwright.sync_api import sync_playwright

profile = sys.argv[1]
out_path = sys.argv[2]

lock = os.path.join(profile, 'SingletonLock')
if os.path.exists(lock): os.remove(lock)

with sync_playwright() as pw:
    browser = pw.chromium.launch_persistent_context(
        profile, headless=False,
        args=["--no-sandbox", "--window-position=-3000,-3000", "--window-size=1280,900"]
    )
    page = browser.new_page()
    page.goto("{FT_FEED}", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)

    articles = page.evaluate('''() => {{
        // Use _feedTimelineTeasers JS variable — contains full article data with dates
        if (window._feedTimelineTeasers && window._feedTimelineTeasers.length > 0) {{
            return window._feedTimelineTeasers
                .filter(a => a.type === 'article' && a.url && a.title)
                .map(a => ({{
                    title: a.title,
                    url: a.url.split('?')[0],
                    source: 'Financial Times',
                    pub_date: a.publishedDate ? a.publishedDate.substring(0, 10) : '',
                    standfirst: a.standfirst || '',
                    is_opinion: a.indicators ? a.indicators.isOpinion : false,
                    is_podcast: a.indicators ? a.indicators.isPodcast : false,
                    already_saved: false
                }}));
        }}
        // Fallback: DOM scrape without dates
        const results = [];
        const seen = new Set();
        document.querySelectorAll('a[href*="/content/"]').forEach(a => {{
            const url = a.href.split('?')[0];
            const title = a.innerText.trim();
            if (title.length > 15 && url.includes('ft.com/content/') && !seen.has(url)) {{
                seen.add(url);
                results.push({{title, url, source: 'Financial Times', pub_date: '', standfirst: '', is_opinion: false, is_podcast: false, already_saved: false}});
            }}
        }});
        return results;
    }}''')
    browser.close()

with open(out_path, 'w') as f:
    json.dump(articles, f)
""")
        _ft_script.close()
        _ft_out.close()
        _proc = _sp.run(
            ["python3", _ft_script_path, str(BASE_DIR / "ft_profile"), _ft_out_path],
            timeout=90, capture_output=True
        )
        if _proc.returncode == 0:
            with open(_ft_out_path) as f:
                _ft_articles = _j.load(f)
            _ft_new = [a for a in _ft_articles
                       if not a.get('already_saved')
                       and not a.get('is_podcast')
                       and a['url'] not in _known
                       and '/content/' in a['url']]
            log.info(f"AI pick: FT feed — {len(_ft_articles)} articles, {len(_ft_new)} unsaved/new")
            candidates.extend(_ft_new)
        else:
            log.warning(f"AI pick: FT subprocess failed: {_proc.stderr.decode()[:200]}")
        try: _os.unlink(_ft_script_path)
        except: pass
        try: _os.unlink(_ft_out_path)
        except: pass
    except Exception as _e:
        log.warning(f"AI pick: FT feed scrape failed: {_e}")

    # ── 2. Foreign Affairs most-read (public, plain HTTP) ────────────────────
    FA_MOST_READ = "https://www.foreignaffairs.com/most-read"
    try:
        _req = _ur.Request(FA_MOST_READ, headers={"User-Agent": "Mozilla/5.0"})
        with _ur.urlopen(_req, timeout=15) as _resp:
            _html = _resp.read().decode("utf-8", errors="ignore")
        import re as _re
        _fa_links = _re.findall(r'href="(/articles/[^"]+)"[^>]*>\s*([^<]{15,})<', _html)
        _fa_seen = set()
        for _path, _title in _fa_links:
            _url = "https://www.foreignaffairs.com" + _path.split("?")[0]
            _title = _title.strip()
            if _url not in _known and _url not in _fa_seen and len(_title) > 15:
                candidates.append({
                    "title": _title, "url": _url, "source": "Foreign Affairs",
                    "pub_date": "", "standfirst": "", "is_opinion": False, "is_podcast": False
                })
                _fa_seen.add(_url)
        log.info(f"AI pick: FA most-read — {len(_fa_seen)} new candidates")
    except Exception as _e:
        log.warning(f"AI pick: FA most-read fetch failed: {_e}")

    if not candidates:
        log.warning("AI pick: no candidates found from any source")
        with sqlite3.connect(DB_PATH) as _rx:
            _rx.execute("INSERT OR REPLACE INTO kt_meta (key, value) VALUES (?, ?)", (_gate_key, _today))
        return [], []

    # Deduplicate
    _seen_u = set()
    _deduped = []
    for _c in candidates:
        if _c['url'] not in _seen_u:
            _seen_u.add(_c['url'])
            _deduped.append(_c)
    candidates = _deduped
    log.info(f"AI pick: {len(candidates)} total candidates across all sources")

    # ── Load taste profile ────────────────────────────────────────────────────
    with sqlite3.connect(DB_PATH) as _pcx:
        _ft_row = _pcx.execute("SELECT value FROM kt_meta WHERE key='ai_pick_followed_topics'").fetchone()
        _tt_row = _pcx.execute("SELECT value FROM kt_meta WHERE key='ai_pick_taste_titles'").fetchone()
    _followed_topics = _j.loads(_ft_row[0]) if _ft_row else []
    _taste_titles = _j.loads(_tt_row[0]) if _tt_row else []
    _topics_str = ", ".join(_followed_topics) if _followed_topics else _interests
    _taste_str = "\n".join(f"- {t}" for t in _taste_titles[:50])

    # ── Sonnet scoring ────────────────────────────────────────────────────────
    _api_key = load_creds().get("anthropic_api_key", "")
    if not _api_key:
        log.warning("AI pick: no API key")
        return [], []

    _articles_list = _j.dumps([
        {"title": a["title"], "url": a["url"], "source": a["source"],
         "standfirst": a.get("standfirst", "")}
        for a in candidates
    ])

    _prompt = (
        "You are scoring news articles for a senior intelligence analyst.\n"
        "FOLLOWED TOPICS: " + _topics_str + ".\n\n"
        + ("RECENT SAVES (use to calibrate taste):\n" + _taste_str + "\n\n" if _taste_str else "")
        + "Score each candidate article 0-10:\n"
        "9-10: CONCRETE BREAKING DEVELOPMENT — war starts/ends, sanctions, central bank decision, "
        "major diplomatic event, energy crisis, market shock. Not reading it today = missed a real event.\n"
        "7-8: High-quality analysis — market moves, geopolitical analysis, economic policy, "
        "AI with real-world impact (new models, defence/finance deployment, regulation).\n"
        "6: Relevant and interesting — essays, AI and society, analysis on followed topics.\n"
        "0-5: Not relevant — lifestyle, sport, celebrity, health, local politics, "
        "company earnings unrelated to macro.\n"
        "CRITICAL: 9-10 = concrete event. A thoughtful essay = 6-7. "
        "Calibrate against the recent saves above — match that taste level.\n"
        "Use the standfirst (subtitle) where provided to improve scoring accuracy.\n"
        "Respond ONLY with a JSON array in the same order as input, no prose, no markdown:\n"
        '[{"score":7,"reason":"one sentence"}]'
        "\n\nCandidate articles:\n" + _articles_list
    )

    log.info(f"AI pick: calling Sonnet to score {len(candidates)} candidates...")
    _payload = _j.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": _prompt}]
    }).encode()
    _req2 = _ur.Request(
        "https://api.anthropic.com/v1/messages",
        data=_payload,
        headers={"Content-Type": "application/json", "x-api-key": _api_key,
                 "anthropic-version": "2023-06-01"},
        method="POST"
    )
    try:
        with _ur.urlopen(_req2, timeout=60) as _resp2:
            _data = _j.loads(_resp2.read())
    except Exception as _e:
        log.warning(f"AI pick: Sonnet call failed: {_e}")
        return [], []

    _text = "".join(b.get("text", "") for b in _data.get("content", []) if b.get("type") == "text")
    if not _text:
        log.warning("AI pick: empty Sonnet response")
        return [], []

    try:
        _text = _text.strip()
        if "```" in _text:
            _text = _text.split("```", 2)[1]
            if _text.startswith("json"): _text = _text[4:]
            _text = _text.rsplit("```", 1)[0].strip()
        import re as _re2
        _m = _re2.search(r'\[[\s\S]*\]', _text)
        _scores = _j.loads(_m.group(0)) if _m else []
    except Exception as _e:
        log.warning(f"AI pick: score parse failed: {_e} — raw: {_text[:200]}")
        return [], []

    log.info(f"AI pick: Sonnet returned {len(_scores)} scores")

    # ── Route by score ────────────────────────────────────────────────────────
    TRUSTED_SOURCES = {"Financial Times", "The Economist", "Foreign Affairs"}
    feed_articles = []
    suggested_out = []

    for _i, _art in enumerate(candidates):
        if _i >= len(_scores): break
        _score = _scores[_i].get("score", 0)
        _reason = _scores[_i].get("reason", "")
        _source = _art["source"]
        _url = _art["url"]
        _title = _art["title"]
        _pub_date = _art.get("pub_date", "")

        if _source not in TRUSTED_SOURCES: continue
        if _url in _known: continue

        _art_id = make_id(_source, _url)
        log.info(f"AI pick: score={_score} [{_source}] {_title[:60]}")

        if _score >= 9:
            feed_articles.append({
                "id": _art_id, "source": _source, "url": _url, "title": _title,
                "body": "", "summary": _reason, "topic": "", "tags": "[]",
                "saved_at": now_ts(), "fetched_at": now_ts(),
                "status": "title_only", "pub_date": _pub_date, "auto_saved": 1
            })
        elif _score >= 6:
            suggested_out.append({
                "title": _title, "url": _url, "source": _source,
                "score": _score, "reason": _reason, "pub_date": _pub_date
            })

    # ── Save Feed picks ───────────────────────────────────────────────────────
    if feed_articles:
        with sqlite3.connect(DB_PATH) as _cx:
            for _fp in feed_articles:
                if not article_exists(_fp["id"]):
                    _cx.execute(
                        'INSERT OR IGNORE INTO articles '
                        '(id,source,url,title,body,summary,topic,tags,saved_at,fetched_at,status,pub_date,auto_saved) '
                        'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        (_fp["id"], _fp["source"], _fp["url"], _fp["title"], _fp["body"],
                         _fp["summary"], _fp["topic"], _fp["tags"], _fp["saved_at"],
                         _fp["fetched_at"], _fp["status"], _fp["pub_date"], 1)
                    )
        log.info(f"AI pick: saved {len(feed_articles)} -> Feed")
        # Update taste_titles
        try:
            with sqlite3.connect(DB_PATH) as _ucx:
                _tt2 = _ucx.execute("SELECT value FROM kt_meta WHERE key='ai_pick_taste_titles'").fetchone()
                _cur_tt = _j.loads(_tt2[0]) if _tt2 else []
                _new_tt = ([a["title"] for a in feed_articles if a.get("title")] + _cur_tt)[:100]
                _ucx.execute("INSERT OR REPLACE INTO kt_meta (key, value) VALUES (?, ?)",
                    ("ai_pick_taste_titles", _j.dumps(_new_tt)))
            log.info(f"AI pick: taste_titles updated ({len(_new_tt)} titles)")
        except Exception as _ue:
            log.warning(f"AI pick: taste_titles update failed: {_ue}")

    # ── Save Suggested picks ──────────────────────────────────────────────────
    if suggested_out:
        save_suggested_snapshot(suggested_out)
        log.info(f"AI pick: saved {len(suggested_out)} -> Suggested")

    # ── Write gate ────────────────────────────────────────────────────────────
    with sqlite3.connect(DB_PATH) as _rx:
        _rx.execute("INSERT OR REPLACE INTO kt_meta (key, value) VALUES (?, ?)", (_gate_key, _today))

    log.info(f"AI pick complete: {len(feed_articles)} -> Feed, {len(suggested_out)} -> Suggested")
    return feed_articles, suggested_out

def scrape_suggested_articles():
    """Thin stub — delegates to ai_pick_feed_scrape().
    Kept for scheduler backwards compatibility."""
    feed, suggested = ai_pick_feed_scrape()
    return suggested

def ai_pick_economist_weekly():
    """Scrape The Economist weekly edition page via CDP and score with Sonnet.
    Runs once per edition (Thursday evening, keyed by edition date).
    Uses eco_chrome_profile via CDP — same approach as eco_scraper_sub.py.

    Gate key: ai_pick_economist_weekly_YYYY-MM-DD (edition date = following Saturday).
    Scheduled: 22:00 UTC Thursdays.
    """
    import json as _j
    import urllib.request as _ur
    import subprocess as _sp
    import tempfile as _tf
    import os as _os
    import time as _t

    # ── Calculate current edition date ───────────────────────────────────────
    # Economist releases Thursday ~21:00 UTC, dated to FOLLOWING Saturday.
    # Logic: if today is Thu after 20:00 UTC, Fri, or Sat -> this coming Saturday
    #        otherwise -> last Saturday (edition already out)
    from datetime import date, timedelta
    from datetime import datetime as _dt
    _today = date.today()
    _now_utc = _dt.utcnow()
    _weekday = _today.weekday()  # 0=Mon, 3=Thu, 4=Fri, 5=Sat, 6=Sun
    # Days since last Saturday
    _days_since_sat = (_weekday - 5) % 7
    _last_sat = _today - timedelta(days=_days_since_sat)
    # Days to next Saturday
    _days_to_next_sat = (5 - _weekday) % 7 or 7
    _next_sat = _today + timedelta(days=_days_to_next_sat)
    # Use next Saturday if: today is Thursday after 20:00 UTC, Friday, or Saturday
    if (_weekday == 3 and _now_utc.hour >= 20) or _weekday == 4 or _weekday == 5:
        _edition_date = _next_sat
    else:
        _edition_date = _last_sat
    _edition_str = _edition_date.strftime('%Y-%m-%d')
    _gate_key = f"ai_pick_economist_weekly_{_edition_str}"
    _edition_url = f"https://www.economist.com/weeklyedition/{_edition_str}"

    log.info(f"Economist weekly: edition {_edition_str}, url={_edition_url}")

    # ── Gate: once per edition ────────────────────────────────────────────────
    with sqlite3.connect(DB_PATH) as _gx:
        _gx.execute("CREATE TABLE IF NOT EXISTS kt_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        _last = _gx.execute("SELECT value FROM kt_meta WHERE key=?", (_gate_key,)).fetchone()
    if _last:
        log.info(f"Economist weekly: already ran for edition {_edition_str} — skipping")
        return [], []

    # ── Build taste profile ───────────────────────────────────────────────────
    with sqlite3.connect(DB_PATH) as _cx:
        _ft_row = _cx.execute("SELECT value FROM kt_meta WHERE key='ai_pick_followed_topics'").fetchone()
        _tt_row = _cx.execute("SELECT value FROM kt_meta WHERE key='ai_pick_taste_titles'").fetchone()
        _known_urls = set(r[0] for r in _cx.execute("SELECT url FROM articles WHERE url!=''").fetchall())
        _sug_urls = set(r[0] for r in _cx.execute("SELECT url FROM suggested_articles WHERE url!=''").fetchall())
    _known = _known_urls | _sug_urls
    _followed = _j.loads(_ft_row[0]) if _ft_row else []
    _taste = _j.loads(_tt_row[0]) if _tt_row else []
    _topics_str = ", ".join(_followed) if _followed else "geopolitics, economics, finance, markets"
    _taste_str = "\n".join(f"- {t}" for t in _taste[:50])

    # ── Scrape weekly edition via CDP subprocess ──────────────────────────────
    _profile = str(BASE_DIR / "eco_chrome_profile")
    _lock = BASE_DIR / "eco_chrome_profile" / "SingletonLock"
    if _lock.exists():
        _lock.unlink()

    _scrape_script = _tf.NamedTemporaryFile(mode='w', suffix='.py', delete=False, dir='/tmp')
    _scrape_out = _tf.NamedTemporaryFile(mode='w', suffix='.json', delete=False, dir='/tmp')
    _scrape_script_path = _scrape_script.name
    _scrape_out_path = _scrape_out.name

    _scrape_script.write(f"""
import json, subprocess, time, os, sys
from playwright.sync_api import sync_playwright

PROFILE = sys.argv[1]
URL = sys.argv[2]
OUT = sys.argv[3]
PORT = 9224

lock = os.path.join(PROFILE, 'SingletonLock')
if os.path.exists(lock): os.remove(lock)

chrome = subprocess.Popen([
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    f'--remote-debugging-port={{PORT}}',
    f'--user-data-dir={{PROFILE}}',
    '--no-first-run', '--no-default-browser-check',
    '--window-position=-3000,-3000', '--window-size=1280,900',
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(4)

articles = []
try:
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(f'http://localhost:{{PORT}}')
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()
        page.goto(URL, wait_until='domcontentloaded', timeout=30000)
        page.wait_for_timeout(4000)

        title = page.title()
        if 'moment' in title.lower() or 'login' in page.url.lower():
            print(f'BLOCKED: {{title}}', file=sys.stderr)
        else:
            articles = page.evaluate('''() => {{
                const results = [];
                const seen = new Set();
                document.querySelectorAll('a[href*="/2026/"], a[href*="/2025/"]').forEach(a => {{
                    const url = a.href.split('?')[0];
                    const text = a.innerText.trim();
                    if (text.length > 15 && !seen.has(url) &&
                        !url.includes('/weeklyedition') && !url.includes('/for-you')) {{
                        seen.add(url);
                        // Walk up DOM to find standfirst <p>
                        let el = a.parentElement;
                        let standfirst = '';
                        for (let i = 0; i < 8; i++) {{
                            if (!el) break;
                            const ps = el.querySelectorAll('p');
                            for (const p of ps) {{
                                const t = p.innerText.trim();
                                if (t.length > 20 && t.length < 200) {{
                                    standfirst = t;
                                    break;
                                }}
                            }}
                            if (standfirst) break;
                            el = el.parentElement;
                        }}
                        results.push({{title: text, url, standfirst}});
                    }}
                }});
                return results;
            }}''')
        browser.close()
finally:
    chrome.terminate()

with open(OUT, 'w') as f:
    json.dump(articles, f)
print(f'Scraped {{len(articles)}} articles')
""")
    _scrape_script.close()
    _scrape_out.close()

    try:
        _proc = _sp.run(
            ["python3", _scrape_script_path, _profile, _edition_url, _scrape_out_path],
            timeout=90, capture_output=True
        )
        if _proc.returncode != 0:
            log.warning(f"Economist weekly: scrape failed: {_proc.stderr.decode()[:200]}")
            return [], []
        with open(_scrape_out_path) as f:
            _raw_articles = _j.load(f)
        log.info(f"Economist weekly: scraped {len(_raw_articles)} articles from {_edition_str}")
    except Exception as _e:
        log.warning(f"Economist weekly: scrape error: {_e}")
        return [], []
    finally:
        try: _os.unlink(_scrape_script_path)
        except: pass
        try: _os.unlink(_scrape_out_path)
        except: pass

    # Filter out already known, exclude cartoons/letters/indicators
    EXCLUDE = ['cartoon', 'letters', 'economic-and-financial-indicators',
               'the-world-this-week', 'interactive']
    candidates = [
        a for a in _raw_articles
        if a['url'] not in _known
        and not any(e in a['url'] for e in EXCLUDE)
        and len(a['title']) > 15
    ]
    log.info(f"Economist weekly: {len(candidates)} new candidates after filtering")

    if not candidates:
        log.info("Economist weekly: no new candidates")
        with sqlite3.connect(DB_PATH) as _rx:
            _rx.execute("INSERT OR REPLACE INTO kt_meta (key, value) VALUES (?, ?)", (_gate_key, _edition_str))
        return [], []

    # ── Sonnet scoring ────────────────────────────────────────────────────────
    _api_key = load_creds().get("anthropic_api_key", "")
    if not _api_key:
        log.warning("Economist weekly: no API key")
        return [], []

    _articles_list = _j.dumps([
        {"title": a["title"], "url": a["url"],
         "standfirst": a.get("standfirst", ""), "source": "The Economist"}
        for a in candidates
    ])

    _prompt = (
        "You are scoring articles from The Economist weekly print edition for a senior intelligence analyst.\n"
        "FOLLOWED TOPICS: " + _topics_str + ".\n\n"
        + ("RECENT SAVES (use to calibrate taste):\n" + _taste_str + "\n\n" if _taste_str else "")
        + "Score each article 0-10. Use the standfirst (subtitle) where provided to help score.\n"
        "9-10: CONCRETE BREAKING DEVELOPMENT — war, sanctions, central bank decision, "
        "major diplomatic event, energy crisis, market shock.\n"
        "7-8: High-quality analysis — geopolitics, economic policy, markets, "
        "AI with real-world impact, trade war, finance.\n"
        "6: Relevant and interesting — quality essays, AI and society, analysis on followed topics.\n"
        "0-5: Not relevant — lifestyle, sport, obituary (unless major figure), science unrelated to interests.\n"
        "CRITICAL: 9-10 = concrete event. A thoughtful essay = 6-7.\n"
        "Respond ONLY with a JSON array in the same order as input, no prose, no markdown:\n"
        '[{"score":8,"reason":"one sentence"}]'
        "\n\nArticles:\n" + _articles_list
    )

    log.info(f"Economist weekly: calling Sonnet to score {len(candidates)} articles...")
    _payload = _j.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": _prompt}]
    }).encode()
    _req = _ur.Request(
        "https://api.anthropic.com/v1/messages",
        data=_payload,
        headers={"Content-Type": "application/json", "x-api-key": _api_key,
                 "anthropic-version": "2023-06-01"},
        method="POST"
    )
    try:
        with _ur.urlopen(_req, timeout=60) as _resp:
            _data = _j.loads(_resp.read())
    except Exception as _e:
        log.warning(f"Economist weekly: Sonnet call failed: {_e}")
        return [], []

    _text = "".join(b.get("text","") for b in _data.get("content",[]) if b.get("type")=="text")
    try:
        _text = _text.strip()
        if "```" in _text:
            _text = _text.split("```",2)[1]
            if _text.startswith("json"): _text = _text[4:]
            _text = _text.rsplit("```",1)[0].strip()
        import re as _re
        _m = _re.search(r'\[[\s\S]*\]', _text)
        _scores = _j.loads(_m.group(0)) if _m else []
    except Exception as _e:
        log.warning(f"Economist weekly: score parse failed: {_e}")
        return [], []

    log.info(f"Economist weekly: Sonnet returned {len(_scores)} scores")

    # ── Route by score ────────────────────────────────────────────────────────
    feed_articles = []
    suggested_out = []

    for _i, _art in enumerate(candidates):
        if _i >= len(_scores): break
        _score = _scores[_i].get("score", 0)
        _reason = _scores[_i].get("reason", "")
        _url = _art["url"]
        _title = _art["title"]
        _art_id = make_id("The Economist", _url)
        log.info(f"Economist weekly: score={_score} {_title[:60]}")

        if _score >= 9:
            feed_articles.append({
                "id": _art_id, "source": "The Economist", "url": _url, "title": _title,
                "body": "", "summary": _reason, "topic": "", "tags": "[]",
                "saved_at": now_ts(), "fetched_at": now_ts(),
                "status": "title_only", "pub_date": _edition_str, "auto_saved": 1
            })
        elif _score >= 6:
            suggested_out.append({
                "title": _title, "url": _url, "source": "The Economist",
                "score": _score, "reason": _reason, "pub_date": _edition_str
            })

    # ── Save to DB ────────────────────────────────────────────────────────────
    if feed_articles:
        with sqlite3.connect(DB_PATH) as _cx:
            for _fp in feed_articles:
                if not article_exists(_fp["id"]):
                    _cx.execute(
                        'INSERT OR IGNORE INTO articles '
                        '(id,source,url,title,body,summary,topic,tags,saved_at,fetched_at,status,pub_date,auto_saved) '
                        'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        (_fp["id"],_fp["source"],_fp["url"],_fp["title"],_fp["body"],
                         _fp["summary"],_fp["topic"],_fp["tags"],_fp["saved_at"],
                         _fp["fetched_at"],_fp["status"],_fp["pub_date"],1)
                    )
        log.info(f"Economist weekly: saved {len(feed_articles)} -> Feed")

    if suggested_out:
        save_suggested_snapshot(suggested_out)
        log.info(f"Economist weekly: saved {len(suggested_out)} -> Suggested")

    # ── Write gate ────────────────────────────────────────────────────────────
    with sqlite3.connect(DB_PATH) as _rx:
        _rx.execute("INSERT OR REPLACE INTO kt_meta (key, value) VALUES (?, ?)", (_gate_key, _edition_str))

    log.info(f"Economist weekly complete: {len(feed_articles)} -> Feed, {len(suggested_out)} -> Suggested")
    return feed_articles, suggested_out


def normalise_url(url):
    """Strip query parameters and fragments for dedup purposes."""
    return url.split('?')[0].split('#')[0].rstrip('/')

def save_suggested_snapshot(articles):
    snapshot_date = datetime.now().strftime("%Y-%m-%d")
    added = 0
    with sqlite3.connect(DB_PATH) as cx:
        existing_urls = set(normalise_url(r[0]) for r in cx.execute("SELECT url FROM suggested_articles").fetchall())
        for a in articles:
            url = a.get("url","")
            if not url or normalise_url(url) in existing_urls:
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
        req = urllib.request.Request(row["url"], headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        with urllib.request.urlopen(req, timeout=20) as r:
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
    if not load_creds().get("anthropic_api_key"):
        return jsonify({"ok": False, "error": "No API key configured"}), 500
    prompt = f"""Summarise this article in 3-4 sentences. Focus on why it would be relevant to someone interested in geopolitics, economics, markets, and international affairs.

Title: {row['title']}
Source: {row['source']}

Article text:
{body[:6000]}"""
    try:
        data = call_anthropic({
            "model": "claude-sonnet-4-6",
            "max_tokens": 300,
            "messages": [{"role": "user", "content": prompt}]
        })
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

# score_and_autosave_new_articles() removed — Session 48


def auto_dismiss_old_suggested(days=30):
    """Auto-dismiss suggested articles older than N days that are still unreviewed."""
    cutoff_ts = now_ts() - (days * 24 * 60 * 60 * 1000)
    with sqlite3.connect(DB_PATH) as cx:
        result = cx.execute(
            "UPDATE suggested_articles SET status='dismissed' WHERE status='new' AND added_at < ?",
            (cutoff_ts,)
        )
        dismissed = result.rowcount
    if dismissed:
        log.info(f"Auto-dismiss: {dismissed} suggested articles older than {days} days dismissed")
    return dismissed

# Core sources allowed in the main Feed via auto-save
FEED_CORE_SOURCES = {'Financial Times', 'The Economist', 'Foreign Affairs', 'Bloomberg'}

def run_agent():
    """Auto-save high-scoring suggested articles to Feed.
    Only FT/Economist/FA/Bloomberg go to Feed — all other sources stay in Suggested."""
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        candidates = cx.execute(
            "SELECT * FROM suggested_articles WHERE status='new' AND score >= 9"
        ).fetchall()
    saved = []
    for row in candidates:
        row = dict(row)
        aid = make_id(row["source"], row["url"])
        if article_exists(aid):
            with sqlite3.connect(DB_PATH) as cx:
                cx.execute("UPDATE suggested_articles SET status='saved' WHERE id=?", (row["id"],))
            continue
        # Non-core sources stay in Suggested — only core sources go to Feed
        if row["source"] not in FEED_CORE_SOURCES:
            log.info(f"Agent: '{row['title'][:50]}' from '{row['source']}' — non-core, keeping in Suggested only")
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

@app.route("/api/agent/score-new", methods=["POST"])
def agent_score_new():
    """Manually trigger scoring of recent FT/Economist articles.
    Accepts optional ?hours=N param (default 24) to control lookback window."""
    hours = int(request.args.get("hours", 24))
    def _run():
        # Temporarily patch cutoff for this call
        original_now = None
        try:
            # Use the hours param by calling with extended window
            cutoff_ts = now_ts() - (hours * 60 * 60 * 1000)
            with sqlite3.connect(DB_PATH) as cx:
                cx.row_factory = sqlite3.Row
                rows = cx.execute("""
                    SELECT id, source, url, title, topic, tags
                    FROM articles
                    WHERE source IN ('Financial Times', 'The Economist')
                      AND auto_saved = 0
                      AND status NOT IN ('agent')
                      AND saved_at >= ?
                      AND title != ''
                """, (cutoff_ts,)).fetchall()
            candidates = [dict(r) for r in rows]
            if not candidates:
                log.info(f"agent/score-new: no FT/Economist articles in last {hours}h")
                return
            log.info(f"agent/score-new: {len(candidates)} candidates in last {hours}h")
            # Reuse score_and_autosave but we need to temporarily widen the window
            # Simplest: just call it directly — it uses 24h internally, so for
            # manual runs we re-implement inline with the requested window
            with sqlite3.connect(DB_PATH) as cx:
                interest_rows = cx.execute(
                    "SELECT topic, tags FROM articles ORDER BY saved_at DESC LIMIT 100"
                ).fetchall()
            topic_counts: dict = {}
            for r in interest_rows:
                if r[0]: topic_counts[r[0]] = topic_counts.get(r[0], 0) + 1
                try:
                    for t in json.loads(r[1] or "[]"):
                        topic_counts[t] = topic_counts.get(t, 0) + 1
                except: pass
            interests_str = ", ".join(sorted(topic_counts, key=lambda x: -topic_counts[x])[:15]) or "geopolitics, economics, finance, markets"
            titles_str = json.dumps([{"id": a["id"], "title": a["title"], "source": a["source"]} for a in candidates])
            score_prompt = (
                "You are scoring news articles for a senior analyst. "
                f"Their interests: {interests_str}. "
                "Score each 0-10: 9-10 essential (geopolitics/finance/markets/diplomacy); "
                "7-8 highly relevant; 5-6 moderate; 0-4 lifestyle/health/culture/sport. "
                f"Articles: {titles_str} "
                'Respond ONLY with JSON array: [{"id":"abc","score":8,"reason":"why"}]'
            )
            # Batch in groups of 20 to avoid token limits
            all_scores = []
            batch_size = 20
            for batch_start in range(0, len(candidates), batch_size):
                batch = candidates[batch_start:batch_start + batch_size]
                batch_titles = json.dumps([{"id": a["id"], "title": a["title"], "source": a["source"]} for a in batch])
                batch_prompt = (
                    "You are scoring news articles for a senior analyst. "
                    f"Their interests: {interests_str}. "
                    "Score each 0-10: 9-10 essential (geopolitics/finance/markets/diplomacy); "
                    "7-8 highly relevant; 5-6 moderate; 0-4 lifestyle/health/culture/sport. "
                    f"Articles: {batch_titles} "
                    'Respond ONLY with a JSON array, no prose: [{"id":"abc","score":8,"reason":"why"}]'
                )
                score_data = call_anthropic({
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": batch_prompt}]
                })
                score_text = "".join(b.get("text", "") for b in score_data.get("content", []) if b.get("type") == "text")
                score_match = re.search(r'\[[\s\S]*?\]', score_text)
                if not score_match:
                    log.warning(f"agent/score-new: could not parse batch {batch_start//batch_size + 1} scores — response: {score_text[:200]}")
                    continue
                batch_scores = json.loads(score_match.group(0))
                all_scores.extend(batch_scores)
                log.info(f"agent/score-new: batch {batch_start//batch_size + 1} scored {len(batch_scores)} articles")
            scores = all_scores
            score_map = {s["id"]: s for s in scores if "id" in s}
            saved_count = 0
            for art in candidates:
                s = score_map.get(art["id"], {})
                score = s.get("score", 0)
                reason = s.get("reason", "")
                log.info(f"agent/score-new: '{art['title'][:50]}' => {score}")
                if score < 8:
                    continue
                with sqlite3.connect(DB_PATH) as cx:
                    cx.execute(
                        "UPDATE articles SET auto_saved=1, summary=CASE WHEN summary='' OR summary IS NULL THEN ? ELSE summary END WHERE id=?",
                        (reason, art["id"])
                    )
                    cx.execute(
                        "INSERT INTO agent_log (article_id,title,url,score,reason,saved_at) VALUES (?,?,?,?,?,?)",
                        (art["id"], art["title"], art["url"], score, reason, now_ts())
                    )
                saved_count += 1
                log.info(f"agent/score-new: auto-saved '{art['title'][:50]}' (score {score})")
            log.info(f"agent/score-new: done — {saved_count}/{len(candidates)} saved")
        except Exception as e:
            log.warning(f"agent/score-new error: {e}")
    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok": True, "started": True})

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

# Flask scheduler: newsletter sync + post-scrape tasks only.
# Scrapers are owned exclusively by launchd (05:40 and 11:40 Geneva).
# Newsletter sync at 06:30 Geneva (04:30 UTC) catches Bloomberg delivery.
NEWSLETTER_SYNC_TIMES_UTC = [(4, 30)]
# Economist weekly edition: Thursday 22:00 UTC (23:00 Geneva, ~1hr after Thursday 22:00 London release)
ECONOMIST_WEEKLY_UTC = {"hour": 22, "weekday": 3}  # weekday 3 = Thursday

def scheduler_loop(interval_hours):
    log.info("Scheduler: newsletter + post-scrape tasks only (scrapers owned by launchd)")
    nl_last_run_date = {t: None for t in NEWSLETTER_SYNC_TIMES_UTC}
    while True:
        now = datetime.utcnow()
        # Newsletter sync + post-scrape tasks at 06:30 Geneva (04:30 UTC)
        for (h, m) in NEWSLETTER_SYNC_TIMES_UTC:
            scheduled = now.replace(hour=h, minute=m, second=0, microsecond=0)
            diff_minutes = (now - scheduled).total_seconds() / 60
            if 0 <= diff_minutes < 5 and nl_last_run_date[(h, m)] != now.date():
                nl_last_run_date[(h, m)] = now.date()
                log.info(f"Scheduler: 06:30 Geneva tasks starting")
                import subprocess as _sp2
                _sp2.Popen(["python3", str(BASE_DIR / "newsletter_sync.py")])
                log.info("Scheduler: triggered newsletter sync")
                def _push_newsletters_to_vps():
                    """Push newsletters to VPS after sync so Points of Return is on mobile by 06:35."""
                    import time as _t2, sqlite3 as _sq2, json as _jj, urllib.request as _ur3
                    _t2.sleep(90)  # Wait for newsletter_sync.py to complete
                    try:
                        _db = _sq2.connect(DB_PATH)
                        _db.row_factory = _sq2.Row
                        _nls = [dict(r) for r in _db.execute(
                            "SELECT gmail_id,source,subject,body_html,body_text,received_at FROM newsletters ORDER BY received_at DESC"
                        ).fetchall()]
                        _db.close()
                        if _nls:
                            _payload = _jj.dumps({"newsletters": _nls}).encode()
                            _req3 = _ur3.Request(
                                "https://meridianreader.com/api/push-newsletters",
                                data=_payload,
                                headers={"Content-Type": "application/json"},
                                method="POST"
                            )
                            with _ur3.urlopen(_req3, timeout=30) as _r3:
                                _res3 = _jj.loads(_r3.read())
                            log.info(f"Scheduler: newsletter VPS push — {_res3.get('upserted',0)} upserted")
                    except Exception as _npe:
                        log.warning(f"Scheduler: newsletter VPS push failed: {_npe}")
                threading.Thread(target=_push_newsletters_to_vps, daemon=True).start()
                def _post_scrape_tasks():
                    try:
                        saved = run_agent()
                        log.info(f"Scheduler: agent promoted {len(saved)} articles to Feed")
                        auto_dismiss_old_suggested(days=30)
                        # Tag any new untagged articles with KT themes
                        try:
                            import urllib.request as _ur2, json as _j2
                            _ur2.urlopen(_ur2.Request(
                                "http://localhost:4242/api/kt/tag-new",
                                data=b"{}",
                                headers={"Content-Type": "application/json"},
                                method="POST"
                            ), timeout=5)
                            log.info("Scheduler: triggered kt/tag-new")
                        except Exception as _kte:
                            log.warning(f"Scheduler: kt/tag-new trigger failed: {_kte}")
                        # Enrich any new images missing insight
                        try:
                            threading.Thread(target=enrich_image_insights, daemon=True).start()
                            log.info("Scheduler: triggered insight enrichment")
                        except Exception as _ie:
                            log.warning(f"Scheduler: insight enrichment trigger failed: {_ie}")
                    except Exception as e:
                        log.warning(f"Scheduler: post-scrape tasks error — {e}")
                threading.Thread(target=_post_scrape_tasks, daemon=True).start()
        # Economist weekly edition — Thursday 22:00 UTC
        _ew = ECONOMIST_WEEKLY_UTC
        if now.weekday() == _ew["weekday"] and now.hour == _ew["hour"] and 0 <= now.minute < 5:
            _ew_key = f"scheduler_eco_weekly_{now.date()}"
            if not hasattr(scheduler_loop, _ew_key):
                setattr(scheduler_loop, _ew_key, True)
                log.info("Scheduler: triggering Economist weekly edition pick")
                threading.Thread(target=ai_pick_economist_weekly, daemon=True).start()
        time.sleep(60)  # Check every minute


@app.route("/api/push-newsletters", methods=["POST"])
def push_newsletters():
    """Receive newsletters from Mac and upsert into VPS DB."""
    data = request.json or {}
    newsletters = data.get("newsletters", [])
    if not newsletters:
        return jsonify({"ok": True, "upserted": 0, "skipped": 0})
    upserted = 0; skipped = 0
    with sqlite3.connect(DB_PATH) as cx:
        for n in newsletters:
            existing = cx.execute(
                "SELECT id FROM newsletters WHERE gmail_id=?", (n.get("gmail_id",""),)
            ).fetchone()
            if existing:
                skipped += 1
                continue
            cx.execute("""
                INSERT INTO newsletters (gmail_id, source, subject, body_html, body_text, received_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (n.get("gmail_id",""), n.get("source",""), n.get("subject",""),
                  n.get("body_html",""), n.get("body_text",""), n.get("received_at","")))
            upserted += 1
    log.info(f"push-newsletters: {upserted} upserted, {skipped} skipped of {len(newsletters)}")
    return jsonify({"ok": True, "upserted": upserted, "skipped": skipped})

@app.route("/api/push-interviews", methods=["POST"])
def push_interviews():
    """Receive interviews from Mac and upsert into VPS DB."""
    data = request.json or {}
    interviews = data.get("interviews", [])
    if not interviews:
        return jsonify({"ok": True, "upserted": 0, "skipped": 0})
    # Get interviews table schema
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        cols = [r["name"] for r in cx.execute("PRAGMA table_info(interviews)").fetchall()]
    upserted = 0; skipped = 0
    with sqlite3.connect(DB_PATH) as cx:
        for iv in interviews:
            existing = cx.execute(
                "SELECT id FROM interviews WHERE id=?", (iv.get("id"),)
            ).fetchone()
            if existing:
                skipped += 1
                continue
            fields = {k: v for k, v in iv.items() if k in cols}
            placeholders = ",".join(["?" for _ in fields])
            col_names = ",".join(fields.keys())
            cx.execute(f"INSERT INTO interviews ({col_names}) VALUES ({placeholders})",
                       list(fields.values()))
            upserted += 1
    log.info(f"push-interviews: {upserted} upserted, {skipped} skipped")
    return jsonify({"ok": True, "upserted": upserted, "skipped": skipped})


@app.route("/api/push-articles", methods=["POST"])
def push_articles():
    """Receive a batch of articles from the Mac scraper and upsert them.
    Called by wake_and_sync.sh after each sync to keep VPS DB in sync."""
    data = request.json or {}
    arts = data.get("articles", [])
    if not arts:
        return jsonify({"ok": True, "upserted": 0})
    upserted = 0
    skipped = 0
    for a in arts:
        if not a.get("id") or not a.get("title"):
            continue
        # Don't overwrite a richer existing version with a poorer incoming one
        with sqlite3.connect(DB_PATH) as cx:
            existing = cx.execute("SELECT status, body FROM articles WHERE id=?", (a["id"],)).fetchone()
        if existing:
            existing_status, existing_body = existing
            # Already have full_text — skip unless incoming is also full_text
            if existing_status == "full_text" and a.get("status") != "full_text":
                skipped += 1
                continue
        art = {
            "id": a["id"],
            "source": a.get("source", ""),
            "url": a.get("url", ""),
            "title": a.get("title", ""),
            "body": a.get("body", ""),
            "summary": a.get("summary", ""),
            "topic": a.get("topic", ""),
            "tags": a.get("tags", "[]") if isinstance(a.get("tags"), str) else json.dumps(a.get("tags", [])),
            "saved_at": a.get("saved_at", now_ts()),
            "fetched_at": a.get("fetched_at"),
            "status": a.get("status", "title_only"),
            "pub_date": a.get("pub_date", ""),
            "auto_saved": a.get("auto_saved", 0),
        }
        upsert_article(art)
        upserted += 1
    log.info(f"push-articles: upserted {upserted}, skipped {skipped} of {len(arts)}")
    return jsonify({"ok": True, "upserted": upserted, "skipped": skipped})



@app.route("/api/push-meta", methods=["POST"])
def push_meta():
    """Receive kt_meta key-value pairs from Mac and upsert into VPS kt_meta.
    Used to sync last_sync_* timestamps and other operational flags."""
    data = request.json or {}
    pairs = data.get("pairs", {})
    if not pairs:
        return jsonify({"ok": True, "upserted": 0})
    upserted = 0
    with sqlite3.connect(DB_PATH) as cx:
        for key, value in pairs.items():
            cx.execute("INSERT OR REPLACE INTO kt_meta (key, value) VALUES (?, ?)", (key, str(value)))
            upserted += 1
    log.info(f"push-meta: {upserted} keys upserted")
    return jsonify({"ok": True, "upserted": upserted})

@app.route("/api/push-images", methods=["POST"])
def push_images():
    """Receive article_images rows from Mac and upsert into VPS DB.
    Deduplicates on mac_id (the Mac autoincrement PK) to correctly
    handle articles with multiple charts (all share the same caption).
    Called by wake_and_sync.sh after article push."""
    import base64 as _b64
    data = request.json or {}
    images = data.get("images", [])
    if not images:
        return jsonify({"ok": True, "upserted": 0})
    upserted = 0
    skipped = 0
    with sqlite3.connect(DB_PATH) as cx:
        # Ensure mac_id column exists (migration)
        cols = [r[1] for r in cx.execute("PRAGMA table_info(article_images)").fetchall()]
        if "mac_id" not in cols:
            cx.execute("ALTER TABLE article_images ADD COLUMN mac_id INTEGER DEFAULT NULL")
        for img in images:
            aid = img.get("article_id")
            if not aid:
                continue
            mac_id = img.get("mac_id")
            # Dedup by mac_id if provided, else fall back to article_id+description
            if mac_id is not None:
                existing = cx.execute(
                    "SELECT id FROM article_images WHERE mac_id=?", (mac_id,)).fetchone()
            else:
                existing = cx.execute(
                    "SELECT id FROM article_images WHERE article_id=? AND description=?",
                    (aid, img.get("description", ""))).fetchone()
            if existing:
                skipped += 1
                continue
            raw = img.get("image_data", "")
            blob = _b64.b64decode(raw) if isinstance(raw, str) else raw
            cx.execute(
                """INSERT INTO article_images
                   (article_id, caption, description, insight, image_data, width, height, captured_at, mac_id)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (aid,
                 img.get("caption", ""),
                 img.get("description", ""),
                 img.get("insight", ""),
                 blob,
                 img.get("width", 0),
                 img.get("height", 0),
                 img.get("captured_at", now_ts()),
                 mac_id))
            upserted += 1
    log.info(f"push-images: upserted {upserted}, skipped {skipped} of {len(images)}")
    return jsonify({"ok": True, "upserted": upserted, "skipped": skipped})

@app.route("/api/dev/shell", methods=["POST"])
def dev_shell():
    """Localhost-only shell exec for Claude automation. Never expose publicly."""
    if request.remote_addr not in ('127.0.0.1', '::1'):
        return jsonify({"error": "localhost only"}), 403
    import subprocess
    cmd = request.json.get('cmd', '')
    if not cmd:
        return jsonify({"error": "no cmd"}), 400
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=str(BASE_DIR))
    return jsonify({"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode})

@app.route("/api/newsletters/sync", methods=["POST"])
def sync_newsletters_route():
    import subprocess
    threading.Thread(
        target=lambda: subprocess.run(["python3", str(BASE_DIR / "newsletter_sync.py")]),
        daemon=True
    ).start()
    return jsonify({"ok": True, "started": True})


_kt_jobs = {}

@app.route("/api/kt/generate", methods=["POST"])
def kt_generate():
    """Start async Key Themes generation — returns job_id immediately."""
    import uuid
    data = request.json or {}
    articles = data.get("articles", [])
    if not articles:
        return jsonify({"error": "no articles"}), 400
    job_id = str(uuid.uuid4())[:8]
    _kt_jobs[job_id] = {"status": "running", "themes": None, "error": None}

    def _run():
        try:
            def _tags(a):
                t = a.get("tags", [])
                if isinstance(t, str):
                    try: t = json.loads(t)
                    except: return ""
                return ", ".join(t) if t else ""

            ctx = "\n".join(
                "- " + a.get("title", "")
                + (" [" + a.get("topic", "") + "]" if a.get("topic") else "")
                + (" (" + _tags(a) + ")" if _tags(a) else "")
                for a in articles[:400]
                if a.get("title") and a.get("status") != "title_only"
            )
            prompt = (
                "You are an intelligence analyst. Analyse these article titles and identify exactly 10 "
                "dominant intelligence themes. For each produce a JSON object with: "
                "name (3-6 words), emoji, "
                "keywords (array of 12-16 specific discriminating terms — use named entities, "
                "proper nouns, places, organisations, and specific technical terms that ONLY appear "
                "in articles genuinely about this theme. Avoid generic words like 'war', 'military', "
                "'conflict', 'economy', 'geopolitics', 'policy', 'markets' that appear across many themes. "
                "For example, for an Iran war theme use: Iran, IRGC, Hormuz, Revolutionary Guard, "
                "Khamenei, Strait, Tehran, Houthi, sanctions, ceasefire, airstrike, Persian Gulf), "
                "overview (2-3 sentences), "
                "key_facts (array of 10 objects each with title and body; use **bold** markdown for key figures/stats in body), subtopics (5-7 strings), "
                "subtopic_details (object mapping subtopic name to array of 4-6 bullet strings). "
                "Return ONLY a valid JSON array of 10 objects. No markdown, no preamble.\n\n"
                "ARTICLES:\n" + ctx
            )
            resp = call_anthropic({
                "model": "claude-sonnet-4-6",
                "max_tokens": 8000,
                "messages": [{"role": "user", "content": prompt}]
            }, timeout=180, retries=1)
            raw = resp["content"][0]["text"].strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw
                raw = raw.rsplit("```", 1)[0]
            themes = json.loads(raw)
            _kt_jobs[job_id] = {"status": "done", "themes": themes, "error": None}
            log.info(f"kt_generate job {job_id}: done ({len(themes)} themes)")
        except Exception as e:
            log.error(f"kt_generate job {job_id} error: {e}")
            _kt_jobs[job_id] = {"status": "error", "themes": None, "error": str(e)}

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok": True, "job_id": job_id})

@app.route("/api/kt/generate/status/<job_id>", methods=["GET"])
def kt_generate_status(job_id):
    """Poll for async kt/generate job result."""
    job = _kt_jobs.get(job_id)
    if not job:
        return jsonify({"error": "unknown job"}), 404
    return jsonify(job)

_kt_brief_jobs = {}

@app.route("/api/kt/brief", methods=["POST"])
def kt_brief():
    """Start async brief generation. Returns job_id immediately."""
    import uuid
    data = request.json or {}
    theme = data.get("theme", {})
    articles = data.get("articles", [])
    brief_type = data.get("type", "short")
    if not theme:
        return jsonify({"error": "no theme"}), 400

    job_id = str(uuid.uuid4())[:8]
    _kt_brief_jobs[job_id] = {"status": "running", "brief": None, "error": None}

    def _run():
        try:
            from brief_pdf import _build_prompt, _build_article_context
            name = theme.get("name", "")
            subtopics = theme.get("subtopics", [])
            art_context, art_count = _build_article_context(articles, brief_type)
            prompt = _build_prompt(name, subtopics, art_context, brief_type)
            max_tokens = 1500 if brief_type == "short" else 4000

            resp = call_anthropic({
                "model": "claude-sonnet-4-6",
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}]
            }, timeout=180, retries=1)
            text = resp["content"][0]["text"]
            _kt_brief_jobs[job_id] = {"status": "done", "brief": text, "error": None}
            log.info(f"kt_brief job {job_id}: done")
        except Exception as e:
            log.error(f"kt_brief job {job_id} error: {e}")
            _kt_brief_jobs[job_id] = {"status": "error", "brief": None, "error": str(e)}

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok": True, "job_id": job_id})

@app.route("/api/kt/brief/status/<job_id>", methods=["GET"])
def kt_brief_status(job_id):
    """Poll for async kt/brief job result."""
    job = _kt_brief_jobs.get(job_id)
    if not job:
        return jsonify({"error": "unknown job"}), 404
    return jsonify(job)



# ── Brief PDF routes (see brief_pdf.py) ──────────────────────────────────────
try:
    import brief_pdf as _bpdf
    _BRIEF_PDF_OK = True
except ImportError:
    _BRIEF_PDF_OK = False
    log.warning("brief_pdf module not found")

@app.route("/api/kt/brief/pdf", methods=["POST"])
def kt_brief_pdf():
    if not _BRIEF_PDF_OK:
        return jsonify({"error": "brief_pdf not available"}), 500
    import uuid
    data = request.json or {}
    theme = data.get("theme", {})
    articles = data.get("articles", [])
    brief_type = data.get("type", "full")
    if not theme:
        return jsonify({"error": "no theme"}), 400
    job_id = str(uuid.uuid4())[:8]
    # Accept pre-generated text from the modal brief (single-call architecture).
    # If the frontend passes the text it already has, skip the Sonnet call.
    pregenerated_text = data.get("text") or None
    _bpdf.start_pdf_job(job_id, theme, articles, brief_type, str(DB_PATH), str(BASE_DIR),
                        pregenerated_text=pregenerated_text)
    return jsonify({"ok": True, "job_id": job_id})

@app.route("/api/kt/brief/pdf/status/<job_id>", methods=["GET"])
def kt_brief_pdf_status(job_id):
    if not _BRIEF_PDF_OK:
        return jsonify({"error": "brief_pdf not available"}), 500
    job = _bpdf.get_job(job_id)
    if not job:
        return jsonify({"error": "unknown job"}), 404
    return jsonify({k: v for k, v in job.items() if k != "path"})

@app.route("/api/kt/brief/pdf/download/<job_id>", methods=["GET"])
def kt_brief_pdf_download(job_id):
    from flask import send_file
    if not _BRIEF_PDF_OK:
        return jsonify({"error": "brief_pdf not available"}), 500
    job = _bpdf.get_job(job_id)
    if not job or not job.get("ready"):
        return jsonify({"error": "not ready"}), 404
    path = Path(job.get("path", ""))
    if not path.exists():
        return jsonify({"error": "file missing"}), 404
    return send_file(str(path), mimetype="application/pdf",
                     as_attachment=True, download_name="meridian_brief.pdf")


# ── Article images routes ─────────────────────────────────────────────────────

@app.route("/api/articles/<aid>/images", methods=["GET"])
def get_article_images(aid):
    """Return all captured chart/map images for an article.
    image_data returned as base64 for frontend display."""
    import base64 as _b64
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        rows = cx.execute(
            "SELECT id, article_id, caption, description, insight, image_data, width, height, captured_at "
            "FROM article_images WHERE article_id=? ORDER BY id ASC",
            (aid,)
        ).fetchall()
    images = []
    for r in rows:
        d = dict(r)
        raw = d.pop("image_data")
        d["image_b64"] = _b64.b64encode(raw).decode('utf-8') if raw else ""
        images.append(d)
    return jsonify({"images": images, "total": len(images)})




@app.route("/api/brief/context", methods=["POST"])
def brief_context():
    """Build scored article context using the same logic as brief_pdf._build_article_context.
    Accepts a list of articles and returns the pre-selected, formatted context string
    so bgGenerate can share the same selection logic as the PDF brief pipeline."""
    from brief_pdf import _build_article_context
    data = request.json or {}
    articles = data.get("articles", [])
    brief_type = data.get("brief_type", "full")
    if not articles:
        return jsonify({"context": "", "count": 0})
    context = _build_article_context(articles, brief_type)
    count = len([a for a in articles if a.get("summary")])
    return jsonify({"context": context, "count": count})

@app.route("/api/images/recent", methods=["GET"])
def images_recent():
    """Return the most recent N images as base64 for progress monitoring.
    Query params: limit (default 20), every_nth (default 5, returns every nth image by id)"""
    import base64 as _b64
    limit = int(request.args.get("limit", 20))
    every_nth = int(request.args.get("every_nth", 5))
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        rows = cx.execute(
            "SELECT id, article_id, caption, description, image_data, captured_at FROM article_images ORDER BY id DESC LIMIT ?",
            (limit * every_nth,)
        ).fetchall()
        total = cx.execute("SELECT COUNT(*) FROM article_images").fetchone()[0]
    sampled = rows[::every_nth][:limit]
    result = []
    for row in sampled:
        img_b64 = _b64.b64encode(row["image_data"]).decode("utf-8") if row["image_data"] else None
        result.append({
            "id": row["id"],
            "article_id": row["article_id"],
            "caption": row["caption"],
            "description": row["description"],
            "image_b64": img_b64,
            "captured_at": row["captured_at"],
        })
    return jsonify({"images": result, "total": total})

@app.route("/api/images/backfill", methods=["POST"])
def images_backfill():
    """Async job: capture charts for all existing Economist articles that have
    no images yet. Processes in batches of 10 with 2s sleep between batches
    to avoid Cloudflare rate limits. Poll /api/images/backfill/status."""
    global _backfill_job
    if _backfill_job["running"]:
        return jsonify({"ok": False, "error": "Already running"}), 409

    def _run():
        global _backfill_job
        import time as _time
        _backfill_job = {"running": True, "total": 0, "done": 0, "captured": 0,
                         "error": None, "started_at": now_ts()}
        try:
            with sqlite3.connect(DB_PATH) as cx:
                # Only articles with URL and body (not title_only) that have no images yet
                rows = cx.execute(
                    "SELECT a.id, a.url, a.title FROM articles a "
                    "WHERE a.source='The Economist' AND a.url!='' AND a.status!='title_only' "
                    "AND NOT EXISTS (SELECT 1 FROM article_images ai WHERE ai.article_id=a.id) "
                    "ORDER BY a.saved_at DESC"
                ).fetchall()
            articles = [(r[0], r[1], r[2]) for r in rows]
            _backfill_job["total"] = len(articles)
            log.info(f"Backfill: {len(articles)} Economist articles to process")

            if not articles or not PLAYWRIGHT_OK:
                _backfill_job["running"] = False
                return

            eco_profile = BASE_DIR / "economist_profile"
            if not eco_profile.exists():
                _backfill_job["error"] = "economist_profile not found"
                _backfill_job["running"] = False
                return
            _clear_stale_profile_lock(eco_profile)

            with sync_playwright() as pw:
                browser = pw.chromium.launch_persistent_context(
                    str(eco_profile),
                    headless=False,
                    args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
                )
                page = browser.pages[0] if browser.pages else browser.new_page()
                try:
                    batch_size = 10
                    for i, (aid, url, title) in enumerate(articles):
                        try:
                            page.goto(url, wait_until="domcontentloaded", timeout=25000)
                            page.wait_for_timeout(2000)
                            n = capture_economist_charts(page, aid)
                            _backfill_job["captured"] += n
                            _backfill_job["done"] = i + 1
                            log.info(f"Backfill: [{i+1}/{len(articles)}] '{title[:50]}' — {n} images")
                            # Sleep between batches
                            if (i + 1) % batch_size == 0:
                                log.info(f"Backfill: batch sleep 2s")
                                _time.sleep(2)
                        except Exception as ae:
                            log.warning(f"Backfill: error on '{title[:40]}': {ae}")
                            _backfill_job["done"] = i + 1
                            continue
                finally:
                    browser.close()
            log.info(f"Backfill: done — {_backfill_job['captured']} images from {_backfill_job['done']} articles")
        except Exception as e:
            log.error(f"Backfill: fatal error: {e}", exc_info=True)
            _backfill_job["error"] = str(e)
        finally:
            _backfill_job["running"] = False

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok": True, "started": True})


@app.route("/api/images/backfill/status", methods=["GET"])
def images_backfill_status():
    """Poll backfill job progress."""
    with sqlite3.connect(DB_PATH) as cx:
        total_images = cx.execute("SELECT COUNT(*) FROM article_images").fetchone()[0]
        articles_with_images = cx.execute(
            "SELECT COUNT(DISTINCT article_id) FROM article_images"
        ).fetchone()[0]
    return jsonify({
        **_backfill_job,
        "total_images_in_db": total_images,
        "articles_with_images": articles_with_images
    })


# -- Incremental Key Themes routes --

_kt_seed_jobs = {}

@app.route("/api/kt/seed", methods=["POST"])
def kt_seed():
    """One-time (or reset) full seed. Wipes existing theme tables then seeds from scratch."""
    import uuid
    job_id = str(uuid.uuid4())[:8]
    _kt_seed_jobs[job_id] = {"status": "running", "progress": "Starting...", "error": None}

    def _run():
        try:
            with sqlite3.connect(DB_PATH) as cx:
                cx.execute("DELETE FROM article_theme_tags")
                cx.execute("DELETE FROM kt_themes")
                cx.execute("DELETE FROM kt_meta")
            log.info("kt/seed: wiped existing theme data")
            _kt_seed_jobs[job_id]["progress"] = "Fetching articles..."

            with sqlite3.connect(DB_PATH) as cx:
                cx.row_factory = sqlite3.Row
                arts = cx.execute(
                    "SELECT id, title, topic, tags, source FROM articles WHERE title!='' ORDER BY saved_at DESC"
                ).fetchall()
                interviews = cx.execute(
                    "SELECT id, title FROM interviews WHERE title!=''"
                ).fetchall()

            def _fmt_tags(t):
                if not t: return ""
                try: return ", ".join(json.loads(t))
                except: return ""

            art_lines = []
            for a in arts:
                # Titles only — keeps prompt small enough for reliable API completion
                line = "- [ART:" + a["id"] + "] " + (a["title"] or "")
                art_lines.append(line)
            for iv in interviews:
                art_lines.append("- [IVW:" + str(iv["id"]) + "] " + (iv["title"] or "") + " [Interview]")

            total = len(art_lines)
            log.info(f"kt/seed: {total} items to process")
            _kt_seed_jobs[job_id]["progress"] = f"Sending {total} articles to Claude..."

            ctx = "\n".join(art_lines[:500])

            # ── Call 1: Generate 10 themes using a representative sample ─────
            # Use every 3rd article (evenly spread across corpus) for theme ID
            # ~165 titles = ~2500 input tokens, leaving plenty for 10 theme objects
            sample_lines = art_lines[::3][:165]
            sample_ctx = "\n".join(sample_lines)
            _kt_seed_jobs[job_id]["progress"] = f"Identifying themes from {len(sample_lines)} representative articles..."
            theme_prompt = (
                "You are an intelligence analyst. Analyse these article titles (a representative sample "
                "from a corpus of " + str(total) + " articles) and identify exactly 8 "
                "dominant intelligence themes.\n\n"
                "CONSOLIDATION RULES (strictly enforced):\n"
                "- NEVER create two themes for the same geographic theatre. "
                "If articles cover both Iran/Gulf military conflict AND Iran/Gulf energy disruption, "
                "merge them into one theme covering both dimensions.\n"
                "- NEVER create two themes for the same technology competition. "
                "If articles cover both Western AI industry (Nvidia/Google/OpenAI) AND China AI "
                "competition (DeepSeek/semiconductors), merge into one theme covering the full AI race.\n"
                "- Each theme must be clearly distinct — a senior analyst should not need to read two "
                "themes to understand one coherent story.\n"
                "- Only create a theme if article volume clearly sustains it. "
                "Prefer 8 broad, well-populated themes over 10 narrow or overlapping ones.\n"
                "- Consumer/luxury themes should only appear if they constitute a major share of articles; "
                "otherwise absorb into a broader economics/demographics theme.\n\n"
                "For each theme produce a JSON object with ONLY these fields:\n"
                "- name (3-6 words)\n"
                "- emoji (single emoji)\n"
                "- keywords (array of 12-16 terms with this STRICT structure):\n"
                "  * keywords[0] MUST be a SHORT, BROAD anchor word (1-2 words max) that is the single "
                "most defining term for this theme — e.g. 'Iran', 'tariffs', 'AI', 'China', 'markets'. "
                "This anchor is used as a hard gate: articles without it are excluded entirely. "
                "It must appear in titles/summaries of at least 10%% of your corpus.\n"
                "  * keywords[1-15] are specific discriminating terms: named entities, proper nouns, "
                "places, organisations, specific technical terms that only appear in articles genuinely "
                "about this theme. Strictly avoid generic words like war, military, conflict, economy, "
                "geopolitics, policy, crisis, global, international that appear across many themes.\n"
                "- overview (2-3 sentences)\n"
                "- subtopics (array of 5-7 strings)\n\n"
                "Do NOT include key_facts or subtopic_details — generated separately.\n\n"
                "Return ONLY a valid JSON array of exactly 8 theme objects. No markdown, no preamble.\n\n"
                "ARTICLES:\n" + sample_ctx
            )
            resp1 = call_anthropic({
                "model": "claude-sonnet-4-6",
                "max_tokens": 3000,
                "messages": [{"role": "user", "content": theme_prompt}]
            }, timeout=60, retries=2)
            raw1 = resp1["content"][0]["text"].strip()
            if raw1.startswith("```"):
                raw1 = raw1.split("\n", 1)[1] if "\n" in raw1 else raw1
                raw1 = raw1.rsplit("```", 1)[0]
            themes = json.loads(raw1)
            theme_names = [t["name"] for t in themes]
            log.info(f"kt/seed call 1 done: {len(themes)} themes")

            # ── Call 2: Assign articles to themes in batches of 100 ──────────
            assignments = []
            batch_size = 50
            batches = [art_lines[i:i+batch_size] for i in range(0, len(art_lines), batch_size)]
            for bi, batch in enumerate(batches):
                _kt_seed_jobs[job_id]["progress"] = f"Assigning articles to themes (batch {bi+1}/{len(batches)})..."
                batch_ctx = "\n".join(batch)
                assign_prompt = (
                    "Assign each article to 1-2 of these themes (use exact names): " + json.dumps(theme_names) + "\n"
                    "Return ONLY a JSON array, same order as input: "
                    '[{"id":"ART:abc123","themes":["Theme Name"]}]\n'
                    "ARTICLES:\n" + batch_ctx
                )
                resp2 = call_anthropic({
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": assign_prompt}]
                }, timeout=30, retries=2)
                raw2 = resp2["content"][0]["text"].strip()
                if raw2.startswith("```"):
                    raw2 = raw2.split("\n", 1)[1] if "\n" in raw2 else raw2
                    raw2 = raw2.rsplit("```", 1)[0]
                batch_assignments = json.loads(raw2)
                assignments.extend(batch_assignments)
                log.info(f"kt/seed batch {bi+1}/{len(batches)}: {len(batch_assignments)} assignments")
            log.info(f"kt/seed call 2 done: {len(assignments)} total assignments")
            _kt_seed_jobs[job_id]["progress"] = f"Saving {len(themes)} themes and {len(assignments)} assignments..."

            ts = now_ts()
            theme_names = {t["name"] for t in themes}
            theme_counts = {t["name"]: 0 for t in themes}

            with sqlite3.connect(DB_PATH) as cx:
                for asgn in assignments:
                    aid_raw = asgn.get("id", "")
                    aid = aid_raw.replace("ART:", "").replace("IVW:", "")
                    for tname in asgn.get("themes", []):
                        if tname in theme_names:
                            theme_counts[tname] = theme_counts.get(tname, 0) + 1
                        try:
                            cx.execute(
                                "INSERT OR IGNORE INTO article_theme_tags (article_id, theme_name, tagged_at) VALUES (?,?,?)",
                                (aid, tname, ts)
                            )
                        except Exception as _e:
                            log.warning(f"kt/seed tag insert: {_e}")

                for t in themes:
                    tname = t.get("name", "")
                    cx.execute(
                        "INSERT OR REPLACE INTO kt_themes "
                        "(name, emoji, keywords, overview, key_facts, subtopics, subtopic_details, article_count, last_updated) "
                        "VALUES (?,?,?,?,?,?,?,?,?)",
                        (
                            tname,
                            t.get("emoji", ""),
                            json.dumps(t.get("keywords", [])),
                            t.get("overview", ""),
                            json.dumps(t.get("key_facts", [])),
                            json.dumps(t.get("subtopics", [])),
                            json.dumps(t.get("subtopic_details", {})),
                            theme_counts.get(tname, 0),
                            ts
                        )
                    )

                cx.execute("INSERT OR REPLACE INTO kt_meta (key, value) VALUES ('last_seeded_at', ?)", (str(ts),))
                cx.execute("INSERT OR REPLACE INTO kt_meta (key, value) VALUES ('article_count_at_seed', ?)", (str(total),))

            # ── Call 3: Generate key_facts + subtopic_details per theme (Haiku, one at a time) ──
            _kt_seed_jobs[job_id]["progress"] = "Generating key facts for each theme..."
            kf_ok = 0
            for ti, t in enumerate(themes):
                try:
                    _kt_seed_jobs[job_id]["progress"] = f"Generating key facts ({ti+1}/{len(themes)}): {t['name'][:40]}..."
                    subs = t.get("subtopics", [])
                    kf_prompt = (
                        "Generate key_facts and subtopic_details for this intelligence theme.\n\n"
                        "Theme: " + t["name"] + "\n"
                        "Overview: " + t.get("overview", "") + "\n"
                        "Subtopics: " + ", ".join(subs) + "\n\n"
                        "Return a JSON object with exactly these fields:\n"
                        "- key_facts: array of exactly 10 objects, each with 'title' (short label, "
                        "max 6 words) and 'body' (1-2 sentences; use **bold** for key figures/stats)\n"
                        "- subtopic_details: object mapping each subtopic name to array of 4-6 bullet strings\n\n"
                        "Return ONLY a valid JSON object. No markdown, no preamble."
                    )
                    kf_resp = call_anthropic({
                        "model": "claude-haiku-4-5-20251001",
                        "max_tokens": 2500,
                        "messages": [{"role": "user", "content": kf_prompt}]
                    }, timeout=45, retries=1)
                    kf_raw = kf_resp["content"][0]["text"].strip()
                    if kf_raw.startswith("```"):
                        kf_raw = kf_raw.split("\n", 1)[1] if "\n" in kf_raw else kf_raw
                        kf_raw = kf_raw.rsplit("```", 1)[0]
                    kf_item = json.loads(kf_raw)
                    kf = kf_item.get("key_facts", [])
                    sd = kf_item.get("subtopic_details", {})
                    with sqlite3.connect(DB_PATH) as cx:
                        cx.execute(
                            "UPDATE kt_themes SET key_facts=?, subtopic_details=? WHERE name=?",
                            (json.dumps(kf), json.dumps(sd), t["name"])
                        )
                    kf_ok += 1
                except Exception as kf_err:
                    log.warning(f"kt/seed: key_facts failed for '{t['name']}' (non-fatal): {kf_err}")
            log.info(f"kt/seed: key_facts enrichment done for {kf_ok}/{len(themes)} themes")

            log.info(f"kt/seed: done -- {len(themes)} themes, {len(assignments)} assignments")
            _kt_seed_jobs[job_id] = {
                "status": "done", "progress": "Complete", "error": None,
                "theme_count": len(themes), "assignment_count": len(assignments)
            }
        except Exception as e:
            log.error(f"kt/seed job {job_id} error: {e}", exc_info=True)
            _kt_seed_jobs[job_id] = {"status": "error", "progress": str(e), "error": str(e)}

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok": True, "job_id": job_id})


@app.route("/api/kt/seed/status/<job_id>", methods=["GET"])
def kt_seed_status(job_id):
    job = _kt_seed_jobs.get(job_id)
    if not job:
        return jsonify({"error": "unknown job"}), 404
    return jsonify(job)


@app.route("/api/kt/themes", methods=["GET"])
def kt_themes_route():
    """Return current themes from DB. Returns {seeded: false} if not yet seeded."""
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        # Only return themes from the latest seed (highest last_updated timestamp)
        latest_ts = cx.execute("SELECT MAX(last_updated) FROM kt_themes").fetchone()
        latest_ts = latest_ts[0] if latest_ts and latest_ts[0] else 0
        rows = cx.execute("SELECT * FROM kt_themes WHERE last_updated=? ORDER BY article_count DESC", (latest_ts,)).fetchall()
        meta_rows = cx.execute("SELECT key, value FROM kt_meta").fetchall()
    if not rows:
        return jsonify({"seeded": False, "themes": []})
    meta = {r["key"]: r["value"] for r in meta_rows}
    themes = []
    for r in rows:
        t = dict(r)
        for field in ("keywords", "key_facts", "subtopics"):
            try: t[field] = json.loads(t[field])
            except: t[field] = []
        try: t["subtopic_details"] = json.loads(t["subtopic_details"])
        except: t["subtopic_details"] = {}
        themes.append(t)
    return jsonify({"seeded": True, "themes": themes, "meta": meta})


@app.route("/api/kt/status", methods=["GET"])
def kt_status():
    """Return seeding state, counts, pending evolution suggestion."""
    with sqlite3.connect(DB_PATH) as cx:
        theme_count = cx.execute("SELECT COUNT(*) FROM kt_themes").fetchone()[0]
        tagged_count = cx.execute("SELECT COUNT(DISTINCT article_id) FROM article_theme_tags").fetchone()[0]
        total_arts = cx.execute("SELECT COUNT(*) FROM articles WHERE title!=''").fetchone()[0]
        meta_rows = cx.execute("SELECT key, value FROM kt_meta").fetchall()
    meta = {r[0]: r[1] for r in meta_rows}
    pending_evolution = json.loads(meta.get("pending_evolution", "null"))
    return jsonify({
        "seeded": theme_count > 0,
        "theme_count": theme_count,
        "tagged_articles": tagged_count,
        "total_articles": total_arts,
        "untagged_articles": total_arts - tagged_count,
        "last_seeded_at": meta.get("last_seeded_at"),
        "pending_evolution": pending_evolution,
    })


@app.route("/api/kt/tag-new", methods=["POST"])
def kt_tag_new():
    """Tag articles with no theme assignment yet. Haiku batches of 25.
    Runs at most once per calendar day to avoid double-billing at the 11:35 sync."""
    # Once-per-day gate
    today_str = datetime.now().strftime('%Y-%m-%d')
    with sqlite3.connect(DB_PATH) as _tgx:
        _tg_last = _tgx.execute("SELECT value FROM kt_meta WHERE key='kt_tag_last_run'").fetchone()
    if _tg_last and _tg_last[0] == today_str:
        log.info(f"kt/tag-new: already ran today ({today_str}) — skipping")
        return jsonify({"ok": True, "tagged": 0, "message": "already ran today"})

    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        theme_rows = cx.execute("SELECT name FROM kt_themes").fetchall()
        if not theme_rows:
            return jsonify({"ok": False, "error": "not seeded"}), 400
        theme_names = [r["name"] for r in theme_rows]
        untagged = cx.execute(
            "SELECT a.id, a.title, a.topic, a.tags FROM articles a "
            "WHERE a.title != '' "
            "AND NOT EXISTS (SELECT 1 FROM article_theme_tags att WHERE att.article_id = a.id) "
            "ORDER BY a.saved_at DESC LIMIT 100"
        ).fetchall()
    if not untagged:
        return jsonify({"ok": True, "tagged": 0, "message": "nothing to tag"})

    def _run():
        import re as _re
        ts = now_ts()
        theme_list = json.dumps(theme_names)
        tagged_total = 0
        batch_size = 25
        arts = [dict(r) for r in untagged]
        for i in range(0, len(arts), batch_size):
            batch = arts[i:i + batch_size]
            batch_str = json.dumps([
                {"id": a["id"], "title": a["title"], "topic": a.get("topic", ""),
                 "tags": (json.loads(a["tags"]) if a.get("tags") else [])}
                for a in batch
            ])
            prompt = (
                "Given these 10 theme names: " + theme_list + "\n"
                "Assign each article to 1-2 themes. Use closest if none fit.\n"
                'Respond ONLY with a JSON array: [{"id":"abc","themes":["Theme One"]}]\n\n'
                "ARTICLES:\n" + batch_str
            )
            try:
                resp = call_anthropic({
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt}]
                }, timeout=30)
                raw = resp["content"][0]["text"].strip()
                m = _re.search(r'\[\s*\{[\s\S]*?\}\s*\]', raw)
                if not m:
                    log.warning("kt/tag-new: could not parse batch response")
                    continue
                assignments = json.loads(m.group(0))
                with sqlite3.connect(DB_PATH) as cx:
                    for asgn in assignments:
                        aid = asgn.get("id", "")
                        for tname in asgn.get("themes", []):
                            if tname in theme_names:
                                cx.execute(
                                    "INSERT OR IGNORE INTO article_theme_tags (article_id, theme_name, tagged_at) VALUES (?,?,?)",
                                    (aid, tname, ts)
                                )
                    for tname in theme_names:
                        cnt = cx.execute(
                            "SELECT COUNT(*) FROM article_theme_tags WHERE theme_name=?", (tname,)
                        ).fetchone()[0]
                        cx.execute("UPDATE kt_themes SET article_count=?, last_updated=? WHERE name=?",
                                   (cnt, ts, tname))
                tagged_total += len(assignments)
                log.info(f"kt/tag-new: batch {i // batch_size + 1} tagged {len(assignments)}")
            except Exception as e:
                log.warning(f"kt/tag-new: batch error: {e}")
        log.info(f"kt/tag-new: done -- {tagged_total} articles tagged")
        with sqlite3.connect(DB_PATH) as _rx:
            _rx.execute("INSERT OR REPLACE INTO kt_meta (key, value) VALUES ('kt_tag_last_run', ?)", (today_str,))

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok": True, "queued": len(untagged)})


@app.route("/api/kt/evolve", methods=["POST"])
def kt_evolve():
    """Check if any theme should be replaced. Writes suggestion to kt_meta as pending_evolution."""
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        themes = cx.execute("SELECT name, article_count FROM kt_themes ORDER BY article_count ASC").fetchall()
        if not themes:
            return jsonify({"ok": False, "error": "not seeded"}), 400
        potential = cx.execute(
            "SELECT theme_name, COUNT(*) as cnt FROM article_theme_tags "
            "WHERE theme_name LIKE 'potential:%' GROUP BY theme_name ORDER BY cnt DESC"
        ).fetchall()

    weakest = [dict(t) for t in themes[:3]]
    candidates = [dict(p) for p in potential if p["cnt"] >= 15]

    if not candidates:
        return jsonify({"ok": True, "suggestion": None,
                        "message": "No replacement candidate has 15+ articles yet"})

    suggestion = {
        "replace": weakest[0]["name"],
        "replace_count": weakest[0]["article_count"],
        "with": candidates[0]["theme_name"].replace("potential:", ""),
        "with_count": candidates[0]["cnt"],
        "detected_at": now_ts(),
    }
    with sqlite3.connect(DB_PATH) as cx:
        cx.execute("INSERT OR REPLACE INTO kt_meta (key, value) VALUES ('pending_evolution', ?)",
                   (json.dumps(suggestion),))
    log.info(f"kt/evolve: suggest replacing '{suggestion['replace']}' with '{suggestion['with']}'")
    return jsonify({"ok": True, "suggestion": suggestion})



@app.route("/api/kt/brief/context-debug", methods=["POST"])
def kt_brief_context_debug():
    """
    Debug endpoint: show which articles _build_article_context would select for a brief.
    POST body: {articles: [...], brief_type: "full"}
    Returns bucket breakdown with scores so you can inspect selection quality.
    """
    import datetime as _dt
    data = request.json or {}
    articles = data.get("articles", [])
    brief_type = data.get("brief_type", "full")

    BUCKETS = 2 if brief_type == "short" else 4
    PER_BUCKET = 15
    SOURCE_CAP = 5

    def get_ts_days(a):
        pd = (a.get("pub_date") or "").strip()
        if pd and pd not in ("null", ""):
            try:
                return _dt.date.fromisoformat(pd[:10]).toordinal()
            except Exception:
                pass
        sa = a.get("saved_at") or 0
        try:
            return int(sa) // 86400000
        except Exception:
            return 0

    def ordinal_to_date(n):
        try:
            return _dt.date.fromordinal(n).isoformat()
        except Exception:
            return "unknown"

    candidates = [a for a in articles if a.get("summary")]
    if not candidates:
        return jsonify({"error": "no articles with summaries"}), 400

    candidates_sorted = sorted(candidates, key=get_ts_days)
    ts_min = get_ts_days(candidates_sorted[0])
    ts_max = get_ts_days(candidates_sorted[-1])
    span = max(ts_max - ts_min, 1)
    bucket_size = span / BUCKETS

    def get_bucket(a):
        b = int((get_ts_days(a) - ts_min) / bucket_size)
        return min(b, BUCKETS - 1)

    def score_article(a):
        status_bonus = 1000 if a.get("status") == "full_text" else 0
        return status_bonus + len(a.get("summary") or "")

    buckets = [[] for _ in range(BUCKETS)]
    for a in candidates_sorted:
        buckets[get_bucket(a)].append(a)

    result_buckets = []
    all_selected_ids = set()

    for b_idx, bucket in enumerate(buckets):
        ranked = sorted(bucket, key=score_article, reverse=True)
        source_counts = {}
        selected = []
        skipped_source_cap = []

        for a in ranked:
            src = a.get("source", "")
            score = score_article(a)
            if source_counts.get(src, 0) >= SOURCE_CAP:
                skipped_source_cap.append({
                    "title": a.get("title", "")[:80],
                    "source": src,
                    "score": score,
                    "reason": f"source cap ({SOURCE_CAP}) reached for {src}"
                })
                continue
            source_counts[src] = source_counts.get(src, 0) + 1
            selected.append(a)
            all_selected_ids.add(a.get("id"))
            if len(selected) >= PER_BUCKET:
                break

        # Date range of this bucket
        bucket_start = ordinal_to_date(int(ts_min + b_idx * bucket_size))
        bucket_end = ordinal_to_date(int(ts_min + (b_idx + 1) * bucket_size) - 1)

        result_buckets.append({
            "bucket": b_idx + 1,
            "date_range": f"{bucket_start} to {bucket_end}",
            "total_in_bucket": len(bucket),
            "selected_count": len(selected),
            "source_counts": source_counts,
            "selected": [
                {
                    "title": a.get("title", "")[:80],
                    "source": a.get("source", ""),
                    "pub_date": a.get("pub_date", ""),
                    "status": a.get("status", ""),
                    "score": score_article(a),
                    "summary_len": len(a.get("summary") or "")
                }
                for a in selected
            ],
            "skipped_source_cap": skipped_source_cap[:10]  # first 10 skipped
        })

    return jsonify({
        "brief_type": brief_type,
        "total_candidates": len(candidates),
        "total_selected": len(all_selected_ids),
        "buckets": BUCKETS,
        "reporting_period": f"{ordinal_to_date(ts_min)} to {ordinal_to_date(ts_max)}",
        "bucket_breakdown": result_buckets
    })


@app.route("/api/health-check", methods=["POST"])
def health_check():
    """Proxy health-check Haiku call from frontend (keeps API key server-side)."""
    body = request.get_json(force=True)
    stats = body.get("stats", {})
    system_prompt = (
        "You are a health monitor for Meridian, a personal news aggregator. "
        "Analyse the provided stats JSON and return ONLY valid JSON (no markdown, no preamble) with this exact shape:\n"
        '{"score":<int 1-10>,"summary":"<2-3 sentence overview>",'
        '"issues":[{"severity":"warn or info","rank":<int, 1=most critical to overall Meridian health>,'
        '"label":"<short label>","text":"<detail>",'
        '"effort":"quick or moderate or involved",'
        '"prompt":"<actionable prompt to fix>"}]}\n'
        "Rules:\n"
        "- rank: order issues by impact on overall Meridian health (1 = fix this first). "
        "  A source being completely dead outranks a trend decline. A scraper failure outranks a backlog.\n"
        "- effort: quick = under 5 min (e.g. check a setting, re-login), "
        "  moderate = 15-30 min (e.g. debug a scraper, update a cookie), "
        "  involved = significant work (e.g. rebuild a pipeline, new source).\n"
        "Source notes:\n"
        "- Bloomberg has NO automated scraper by design (bot detection too strong). "
        "Articles are added manually via a Chrome extension. "
        "Gaps in Bloomberg ingestion are NORMAL and expected -- "
        "do NOT flag Bloomberg zero-days or trend declines as issues.\n"
        "Key things to check:\n"
        "1. ingestion14d: look at daily totals and bySource counts (exclude Bloomberg). Flag any day with 0 articles total, "
        "   or any source missing for 2+ consecutive days. Note weekend dips only if severe (0 articles). Exclude Bloomberg.\n"
        "2. zeroDaysLast7: days per source with 0 articles in the last 7 days -- flag if 2+ days for a source (exclude Bloomberg).\n"
        "3. trend: compare prev7avg vs last7avg per source. Flag if last7avg dropped >40pct vs prev7avg (exclude Bloomberg).\n"
        "4. sources[].daysSinceLatest: flag if >3 days for FT/Economist, >7 for FA. Ignore Bloomberg.\n"
        "5. sources[].backlog: flag if >10 unenriched articles.\n"
        "Be specific: name the dates and sources. warn=needs action now, info=informational. Only include genuine issues. IMPORTANT: Keep your entire JSON response under 600 tokens. Summary: max 2 sentences. Each issue text: max 15 words. Max 4 issues."
    )
    try:
        result = call_anthropic({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 1800,
            "system": system_prompt,
            "messages": [{"role": "user", "content": "Stats: " + json.dumps(stats)}]
        })
        text = result.get("content", [{}])[0].get("text", "{}")
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:]).rstrip("`").strip()
        return jsonify({"ok": True, "text": text})
    except Exception as e:
        err_str = str(e)
        log.error(f"Health check error: {err_str}")
        if "credit balance" in err_str.lower() or "400" in err_str:
            return jsonify({"ok": False, "error": "Anthropic API credits required — top up at console.anthropic.com"}), 402
        return jsonify({"ok": False, "error": err_str}), 500


if __name__ == "__main__":
    init_db()
    interval = float(os.environ.get("SYNC_INTERVAL_HOURS","6"))
    threading.Thread(target=scheduler_loop, args=(interval,), daemon=True).start()
    log.info(f"Scheduler started — auto-sync every {interval}h")
    log.info("Meridian server starting on http://localhost:4242")
    app.run(host="0.0.0.0", port=4242, debug=False)
