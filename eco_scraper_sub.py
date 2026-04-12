#!/usr/bin/env python3
"""
eco_scraper_sub.py — Economist bookmarks scraper subprocess.
- Runs headless Chrome via CDP (no visible window, no Flask event loop conflict)
- Clicks Load More repeatedly, checking only the newly revealed bottom batch
- Stops when ALL articles in the latest batch are already in the DB
- Returns only articles NOT already in DB

Args: <cdp_profile_dir> <cdp_port> <output_json_path> <known_ids_json_path>
  known_ids_json_path: JSON file containing list of article IDs already in DB
Output JSON: {"articles": [...], "error": null}
"""
import sys, json, time, subprocess, re, hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright

CDP_PROFILE   = Path(sys.argv[1])
CDP_PORT      = int(sys.argv[2])
OUT_PATH      = sys.argv[3]
KNOWN_IDS_PATH = sys.argv[4]
CHROME_BIN    = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BOOKMARKS_URL = "https://www.economist.com/for-you/bookmarks"

JUNK_URL_PATHS = ("/podcasts/", "/newsletters/", "/events/", "/films/", "/interactive/")
JUNK_PREFIXES  = (
    "The War Room newsletter:", "Blighty newsletter:", "The US in Brief:",
    "Espresso:", "The World in Brief:", "The Economist explains:",
    "Graphic detail:", "KAL's cartoon",
)
SECTION_LABELS = {
    'Finance & economics','Middle East & Africa','Science & technology','Business',
    'United States','Europe','Charlemagne','Schumpeter','Buttonwood','Free exchange',
    'Free Exchange','Lexington','Leaders','Briefing','By Invitation','Bagehot',
    'The Telegram','Well informed','Graphic detail','Christmas Specials','International',
    'Special report','The Americas','Asia','Britain','China','Culture','Obituary',
    'Schools brief','Technology Quarterly','The world this week','The World Ahead',
    'Letters','Index',
}

# Load known IDs from DB
with open(KNOWN_IDS_PATH) as f:
    known_ids = set(json.load(f))

def make_id(url):
    return hashlib.sha1(f"The Economist:{url}".encode()).hexdigest()[:16]

def extract_pub_date(url):
    m = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""

def now_ts():
    return int(time.time() * 1000)

def extract_articles_from_page(page):
    """Extract all article {id, url, title} currently visible on the page."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(page.content(), "html.parser")
    main = soup.find("main") or soup

    seen = set()
    articles = []

    for a in main.select("a[href*='/20']"):
        href = a.get("href", "")
        if not re.search(r'/\d{4}/\d{2}/\d{2}/', href):
            continue
        url = ("https://www.economist.com" + href if href.startswith("/") else href).split("?")[0]
        if any(p in url for p in JUNK_URL_PATHS):
            continue
        art_id = make_id(url)
        if art_id in seen:
            continue
        seen.add(art_id)

        # Extract title
        title = ""
        parent = a.parent
        if parent and parent.name in ('h3', 'h2'):
            t = a.get_text(strip=True)
            if t and len(t) > 15 and t not in SECTION_LABELS:
                title = t
        if not title:
            for ancestor in [a.parent, a.parent.parent if a.parent else None]:
                if ancestor is None:
                    continue
                cls = ' '.join(ancestor.get('class', []))
                if 'headline' in cls.lower():
                    t = ancestor.get_text(strip=True)
                    if t and len(t) > 15 and t not in SECTION_LABELS:
                        title = t
                        break
        if not title:
            t = a.get_text(strip=True)
            if t and len(t) > 20 and t not in SECTION_LABELS:
                title = t
        if not title:
            slug = url.rstrip('/').split('/')[-1].replace('-', ' ')
            if len(slug) > 20:
                title = slug.title()
        if not title or len(title) < 10:
            continue
        if any(title.startswith(p) for p in JUNK_PREFIXES):
            continue

        articles.append({"id": art_id, "url": url, "title": title})

    return articles

articles_to_save = []
error = None

# Clear stale lock
lock = CDP_PROFILE / "SingletonLock"
if lock.exists():
    lock.unlink()

chrome_proc = subprocess.Popen([
    CHROME_BIN,
    f"--remote-debugging-port={CDP_PORT}",
    f"--user-data-dir={CDP_PROFILE}",
    "--headless=new",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-default-apps",
    "--disable-gpu",
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(5)

try:
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://localhost:{CDP_PORT}")
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()

        print(f"Navigating to {BOOKMARKS_URL}...", file=sys.stderr)
        page.goto(BOOKMARKS_URL, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(3000)

        if "login" in page.url or "myaccount" in page.url:
            error = "Login required — eco_chrome_profile session expired"
        else:
            load_more_clicks = 0
            max_clicks = 50  # safety cap — covers ~500 articles

            while True:
                # Get all articles currently on page
                all_visible = extract_articles_from_page(page)
                total_visible = len(all_visible)
                print(f"Load More clicks: {load_more_clicks} | Visible articles: {total_visible}", file=sys.stderr)

                if load_more_clicks == 0:
                    # First load — treat all visible as the "new batch"
                    new_batch = all_visible
                else:
                    # After Load More — the new batch is the bottom ~10
                    new_batch = all_visible[prev_count:]

                # Check if ALL articles in new batch are already in DB
                new_batch_new = [a for a in new_batch if a["id"] not in known_ids]
                new_batch_existing = [a for a in new_batch if a["id"] in known_ids]

                print(f"  New batch: {len(new_batch)} articles — {len(new_batch_new)} new, {len(new_batch_existing)} existing", file=sys.stderr)

                # Collect new articles from this batch
                for art in new_batch_new:
                    articles_to_save.append({
                        "id": art["id"],
                        "source": "The Economist",
                        "url": art["url"],
                        "title": art["title"],
                        "body": "",
                        "summary": "",
                        "topic": "",
                        "tags": "[]",
                        "saved_at": now_ts(),
                        "fetched_at": now_ts(),
                        "status": "title_only",
                        "pub_date": extract_pub_date(art["url"]),
                        "auto_saved": 0,
                    })

                # Stop if all articles in new batch are already in DB
                if load_more_clicks > 0 and len(new_batch_existing) == len(new_batch) and len(new_batch) > 0:
                    print(f"All {len(new_batch)} articles in last batch already in DB — stopping", file=sys.stderr)
                    break

                if load_more_clicks >= max_clicks:
                    print(f"Reached max clicks ({max_clicks}) — stopping", file=sys.stderr)
                    break

                # Try to click Load More
                prev_count = total_visible
                try:
                    load_more = page.locator("button:has-text('Load More'), a:has-text('Load More')").first
                    if load_more.is_visible(timeout=3000):
                        load_more.click()
                        page.wait_for_timeout(3000)  # wait for new articles to render
                        load_more_clicks += 1
                    else:
                        print("No Load More button visible — end of bookmarks", file=sys.stderr)
                        break
                except Exception as e:
                    print(f"Load More not found: {e}", file=sys.stderr)
                    break

        try: page.close()
        except: pass
        try: browser.disconnect()
        except: pass

except Exception as e:
    error = str(e)
    print(f"Fatal error: {e}", file=sys.stderr)
finally:
    chrome_proc.terminate()

print(f"eco_scraper_sub: {len(articles_to_save)} new articles found", file=sys.stderr)
with open(OUT_PATH, 'w') as f:
    json.dump({"articles": articles_to_save, "error": error}, f)
