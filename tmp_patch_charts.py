"""
Patch server.py to add Economist chart capture:
1. article_images table in init_db
2. capture_economist_charts() helper function
3. Hook capture into enrich_title_only_articles Economist block
4. Flask routes: GET /api/articles/<aid>/images, POST /api/images/backfill, GET /api/images/backfill/status
"""
from pathlib import Path

p = Path('/Users/alexdakers/meridian-server/server.py')
src = p.read_text(encoding='utf-8')
orig_len = len(src)
changes = []

# ─────────────────────────────────────────────────────────────────────────────
# PATCH 1: Add article_images table to init_db
# ─────────────────────────────────────────────────────────────────────────────
OLD1 = """        cx.execute('CREATE TABLE IF NOT EXISTS kt_meta '
                   '(key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        cx.commit()"""

NEW1 = """        cx.execute('CREATE TABLE IF NOT EXISTS kt_meta '
                   '(key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        # -- Economist chart/map capture --
        cx.execute(\"\"\"CREATE TABLE IF NOT EXISTS article_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id TEXT NOT NULL,
            caption TEXT NOT NULL,
            description TEXT DEFAULT '',
            image_data BLOB NOT NULL,
            width INTEGER DEFAULT 0,
            height INTEGER DEFAULT 0,
            captured_at INTEGER NOT NULL,
            FOREIGN KEY (article_id) REFERENCES articles(id)
        )\"\"\")
        cx.commit()"""

if OLD1 in src:
    src = src.replace(OLD1, NEW1, 1)
    changes.append('PATCH1 OK: article_images table added to init_db')
else:
    changes.append('PATCH1 FAILED: anchor not found')

# ─────────────────────────────────────────────────────────────────────────────
# PATCH 2: Add capture_economist_charts() after fetch_economist_article_text
# ─────────────────────────────────────────────────────────────────────────────
OLD2 = """@app.route('/newsletters')
def get_newsletters():"""

NEW2 = """def capture_economist_charts(page, article_id):
    \"\"\"Capture charts and maps from the current Economist article page.
    Page must already be loaded. Finds all <figure> elements whose <figcaption>
    contains 'Chart:' or 'Map:', screenshots them, generates AI descriptions.
    Saves to article_images table. Skips article if images already captured.
    Returns count of images captured.\"\"\"
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
                if not ("Chart:" in caption_text or "Map:" in caption_text):
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


# ── Backfill job state ────────────────────────────────────────────────────────
_backfill_job = {"running": False, "total": 0, "done": 0, "captured": 0, "error": None, "started_at": None}


@app.route('/newsletters')
def get_newsletters():"""

if OLD2 in src:
    src = src.replace(OLD2, NEW2, 1)
    changes.append('PATCH2 OK: capture_economist_charts() + _backfill_job state added')
else:
    changes.append('PATCH2 FAILED: anchor not found')

# ─────────────────────────────────────────────────────────────────────────────
# PATCH 3: Hook chart capture into enrich_title_only_articles Economist block
# After enrich_article_with_ai(a) and _save_enriched_article(a) for Economist,
# call capture_economist_charts. Find the specific log line after _save_enriched_article
# in the Economist section.
# ─────────────────────────────────────────────────────────────────────────────
OLD3 = """                        enrich_article_with_ai(a)
                        _save_enriched_article(a)
                        enriched += 1
                        log.info(f"Enrich title-only: Economist fetched '{a['title'][:50]}'")
                browser.close()
        except Exception as e:
            log.warning(f"Enrich title-only: Economist Playwright failed: {e}")"""

NEW3 = """                        enrich_article_with_ai(a)
                        _save_enriched_article(a)
                        enriched += 1
                        log.info(f"Enrich title-only: Economist fetched '{a['title'][:50]}'")
                        # Capture charts/maps while page is still open
                        try:
                            capture_economist_charts(page, a["id"])
                        except Exception as _ce:
                            log.warning(f"Enrich title-only: chart capture failed for '{a['title'][:40]}': {_ce}")
                browser.close()
        except Exception as e:
            log.warning(f"Enrich title-only: Economist Playwright failed: {e}")"""

if OLD3 in src:
    src = src.replace(OLD3, NEW3, 1)
    changes.append('PATCH3 OK: chart capture hooked into enrich_title_only Economist block')
else:
    changes.append('PATCH3 FAILED: anchor not found')

# ─────────────────────────────────────────────────────────────────────────────
# PATCH 4: Add Flask routes before the KT routes block
# Insert before "# -- Incremental Key Themes routes --"
# ─────────────────────────────────────────────────────────────────────────────
OLD4 = """# -- Incremental Key Themes routes --

_kt_seed_jobs = {}"""

NEW4 = """# ── Article images routes ─────────────────────────────────────────────────────

@app.route("/api/articles/<aid>/images", methods=["GET"])
def get_article_images(aid):
    \"\"\"Return all captured chart/map images for an article.
    image_data returned as base64 for frontend display.\"\"\"
    import base64 as _b64
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        rows = cx.execute(
            "SELECT id, article_id, caption, description, image_data, width, height, captured_at "
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


@app.route("/api/images/backfill", methods=["POST"])
def images_backfill():
    \"\"\"Async job: capture charts for all existing Economist articles that have
    no images yet. Processes in batches of 10 with 2s sleep between batches
    to avoid Cloudflare rate limits. Poll /api/images/backfill/status.\"\"\"
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
    \"\"\"Poll backfill job progress.\"\"\"
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

_kt_seed_jobs = {}"""

if OLD4 in src:
    src = src.replace(OLD4, NEW4, 1)
    changes.append('PATCH4 OK: Flask routes added (article images + backfill)')
else:
    changes.append('PATCH4 FAILED: anchor not found')

# Write result
p.write_text(src, encoding='utf-8')
print('\\n'.join(changes))
print(f'ORIG LEN: {orig_len}  NEW LEN: {len(src)}  DELTA: {len(src)-orig_len}')
