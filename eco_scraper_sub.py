#!/usr/bin/env python3
"""
eco_scraper_sub.py — Economist bookmarks scraper subprocess.
Runs headless Chrome via CDP (no visible window, no Flask event loop conflict).

Stopping logic: keep clicking Load More until the total number of visible
articles stops increasing — meaning there is no more content to load.
Then return all articles NOT already in known_ids.

Args: <cdp_profile_dir> <cdp_port> <output_json_path> <known_ids_json_path>
Output JSON: {"articles": [...], "error": null}
"""
import sys, json, time, subprocess, re, hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

CDP_PROFILE    = Path(sys.argv[1])
CDP_PORT       = int(sys.argv[2])
OUT_PATH       = sys.argv[3]
KNOWN_IDS_PATH = sys.argv[4]
CHROME_BIN     = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BOOKMARKS_URL  = "https://www.economist.com/for-you/bookmarks"

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

with open(KNOWN_IDS_PATH) as f:
    known_ids = set(json.load(f))

def make_id(url):
    return hashlib.sha1(f"The Economist:{url}".encode()).hexdigest()[:16]

def extract_pub_date(url):
    m = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""

def now_ts():
    return int(time.time() * 1000)

def extract_all_articles(page):
    """Extract ALL article {id, url, title} currently visible on the page."""
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

        print(f"Navigating to bookmarks...", file=sys.stderr)
        page.goto(BOOKMARKS_URL, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(3000)

        if "login" in page.url or "myaccount" in page.url:
            error = "Login required — eco_chrome_profile session expired"
        else:
            load_more_clicks = 0
            max_clicks = 60  # safety cap

            while True:
                all_visible = extract_all_articles(page)
                prev_count = len(all_visible)
                print(f"Click {load_more_clicks}: {prev_count} articles visible", file=sys.stderr)

                # Try to click Load More
                try:
                    load_more = page.locator("button:has-text('Load More'), a:has-text('Load More')").first
                    if not load_more.is_visible(timeout=3000):
                        print("No Load More button — end of bookmarks", file=sys.stderr)
                        break
                    load_more.click()
                    page.wait_for_timeout(3000)
                    load_more_clicks += 1
                except Exception as e:
                    print(f"Load More not found: {e}", file=sys.stderr)
                    break

                # Check how many articles are now visible
                all_visible_after = extract_all_articles(page)
                new_count = len(all_visible_after)
                print(f"  After click: {new_count} articles (+{new_count - prev_count})", file=sys.stderr)

                # Stop if Load More added nothing new
                if new_count <= prev_count:
                    print("Load More added no new articles — end of bookmarks", file=sys.stderr)
                    break

                if load_more_clicks >= max_clicks:
                    print(f"Reached max clicks ({max_clicks}) — stopping", file=sys.stderr)
                    break

            # Final extraction — get all visible articles not in DB
            all_final = extract_all_articles(page)
            print(f"Total visible: {len(all_final)}, known_ids: {len(known_ids)}", file=sys.stderr)

            for art in all_final:
                if art["id"] not in known_ids:
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

        try: page.close()
        except: pass
        try: browser.disconnect()
        except: pass

except Exception as e:
    error = str(e)
    print(f"Fatal error: {e}", file=sys.stderr)
finally:
    chrome_proc.terminate()

print(f"eco_scraper_sub: {len(articles_to_save)} new articles to save", file=sys.stderr)
with open(OUT_PATH, 'w') as f:
    json.dump({"articles": articles_to_save, "error": error}, f)
