#!/usr/bin/env python3
"""
eco_scraper_sub.py — Economist bookmarks scraper subprocess.
Uses real Chrome WITHOUT --headless (headless breaks Economist JS rendering).
Window moved off-screen (-3000,-3000) to avoid disrupting the desktop.
Clicks Load More until page stops growing, then returns all new articles.

Args: <cdp_profile_dir> <cdp_port> <output_json> <known_ids_json>
Output: {"articles": [...], "error": null}
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
    'Finance & economics', 'Middle East & Africa', 'Science & technology', 'Business',
    'United States', 'Europe', 'Charlemagne', 'Schumpeter', 'Buttonwood', 'Free exchange',
    'Free Exchange', 'Lexington', 'Leaders', 'Briefing', 'By Invitation', 'Bagehot',
    'The Telegram', 'Well informed', 'Graphic detail', 'Christmas Specials', 'International',
    'Special report', 'The Americas', 'Asia', 'Britain', 'China', 'Culture', 'Obituary',
    'Schools brief', 'Technology Quarterly', 'The world this week', 'The World Ahead',
    'Letters', 'Index',
}

with open(KNOWN_IDS_PATH) as f:
    known_ids = set(json.load(f))

DATE_PAT = re.compile(r'([A-Z][a-z]{2})\s+(\d{1,2})(?:st|nd|rd|th)?\s+(\d{4})')
MONTH_MAP = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,
             'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}

def parse_date_text(text):
    """Parse 'Apr 9th 2026' style date to YYYY-MM-DD."""
    m = DATE_PAT.search(text)
    if m:
        mon, day, yr = m.group(1), int(m.group(2)), m.group(3)
        if mon in MONTH_MAP:
            return "%s-%02d-%02d" % (yr, MONTH_MAP[mon], day)
    return ""

def make_id(url):
    return hashlib.sha1(("The Economist:" + url).encode()).hexdigest()[:16]

def extract_pub_date(url):
    m = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
    return (m.group(1) + "-" + m.group(2) + "-" + m.group(3)) if m else ""

def now_ts():
    return int(time.time() * 1000)

def extract_all_articles(page):
    """Extract all article {id, url, title} currently visible on the page."""
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
        if any(title.startswith(pf) for pf in JUNK_PREFIXES):
            continue

        # Extract pub_date from grandparent text (e.g. "Apr 9th 2026")
        # This is more accurate than the URL date (URL uses edition date, not article date)
        pub_date = ""
        for ancestor in [a.parent, a.parent.parent if a.parent else None,
                         a.parent.parent.parent if a.parent and a.parent.parent else None]:
            if ancestor is None:
                continue
            txt = ancestor.get_text(separator=" ", strip=True)
            pub_date = parse_date_text(txt)
            if pub_date:
                break

        articles.append({"id": art_id, "url": url, "title": title, "pub_date": pub_date})

    return articles


articles_to_save = []
error = None

lock = CDP_PROFILE / "SingletonLock"
if lock.exists():
    lock.unlink()

# Real Chrome (not headless) — headless=new breaks Economist JS rendering
# Off-screen window avoids disrupting the desktop
chrome_proc = subprocess.Popen([
    CHROME_BIN,
    "--remote-debugging-port=" + str(CDP_PORT),
    "--user-data-dir=" + str(CDP_PROFILE),
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-default-apps",
    "--window-position=-3000,-3000",
    "--window-size=1280,900",
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(5)

try:
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:" + str(CDP_PORT))
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()

        print("Navigating to bookmarks...", file=sys.stderr)
        page.goto(BOOKMARKS_URL, wait_until="domcontentloaded", timeout=45000)
        try:
            page.wait_for_selector("a[href*='/20']", timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(3000)

        if "login" in page.url or "myaccount" in page.url:
            error = "Login required — eco_chrome_profile session expired"
        else:
            all_visible = extract_all_articles(page)
            print("Initial load: " + str(len(all_visible)) + " articles visible", file=sys.stderr)

            load_more_clicks = 0
            max_clicks = 60

            while True:
                prev_count = len(all_visible)

                try:
                    load_more = page.locator("button:has-text('Load More'), a:has-text('Load More')").first
                    if not load_more.is_visible(timeout=3000):
                        print("No Load More button — end of bookmarks", file=sys.stderr)
                        break

                    # Scroll into view then click — important for off-screen window
                    load_more.scroll_into_view_if_needed()
                    page.wait_for_timeout(500)
                    load_more.click()
                    page.wait_for_timeout(4000)  # fixed wait — reliable for off-screen rendering
                    load_more_clicks += 1

                except Exception as e:
                    print("Load More error: " + str(e), file=sys.stderr)
                    break

                all_visible = extract_all_articles(page)
                new_count = len(all_visible)
                gained = new_count - prev_count
                print("Click " + str(load_more_clicks) + ": " + str(new_count) + " articles (+" + str(gained) + ")", file=sys.stderr)

                if new_count <= prev_count:
                    print("Load More added nothing — end of bookmarks", file=sys.stderr)
                    break

                if load_more_clicks >= max_clicks:
                    print("Reached max " + str(max_clicks) + " clicks — stopping", file=sys.stderr)
                    break

            print("Total visible: " + str(len(all_visible)) + ", known: " + str(len(known_ids)), file=sys.stderr)

            for art in all_visible:
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
                        "pub_date": art.get("pub_date", ""),
                        "auto_saved": 0,
                    })

        try: page.close()
        except: pass
        try: browser.close()
        except: pass

except Exception as e:
    error = str(e)
    print("Fatal: " + str(e), file=sys.stderr)
finally:
    chrome_proc.terminate()

print("eco_scraper_sub: " + str(len(articles_to_save)) + " new articles", file=sys.stderr)
with open(OUT_PATH, 'w') as f:
    json.dump({"articles": articles_to_save, "error": error}, f)
