#!/usr/bin/env python3
"""
eco_scraper_sub.py — Economist bookmarks scraper subprocess.
Called by EconomistScraper.scrape() to avoid Flask event loop conflict.
Args: <cdp_profile_dir> <cdp_port> <output_json_path>
Writes JSON: {"articles": [...], "error": null}
"""
import sys, json, time, subprocess, re
from pathlib import Path
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

CDP_PROFILE = Path(sys.argv[1])
CDP_PORT = int(sys.argv[2])
OUT_PATH = sys.argv[3]
CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BOOKMARKS_URL = "https://www.economist.com/for-you/bookmarks"

JUNK_URL_PATHS = ("/podcasts/", "/newsletters/", "/events/", "/films/", "/interactive/")
JUNK_PREFIXES = ("The War Room newsletter:", "Blighty newsletter:", "The US in Brief:",
                 "Espresso:", "The World in Brief:", "The Economist explains:",
                 "Graphic detail:", "KAL's cartoon")
SECTION_LABELS = {
    'Finance & economics','Middle East & Africa','Science & technology','Business',
    'United States','Europe','Charlemagne','Schumpeter','Buttonwood','Free exchange',
    'Free Exchange','Lexington','Leaders','Briefing','By Invitation','Bagehot',
    'The Telegram','Well informed','Graphic detail','Christmas Specials','International',
    'Special report','The Americas','Asia','Britain','China','Culture','Obituary',
    'Schools brief','Technology Quarterly','The world this week','The World Ahead',
    'Letters','Index',
}

def make_id(source, url):
    import hashlib
    return hashlib.sha1(f"{source}:{url}".encode()).hexdigest()[:16]

def extract_pub_date_from_url(url):
    m = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""

def article_exists_local(art_id):
    # Can't query Mac DB from subprocess easily — skip existence check
    # The main scraper will handle deduplication via article_exists()
    return False

def now_ts():
    return int(time.time() * 1000)

articles = []
error = None

# Clear stale lock
lock = CDP_PROFILE / "SingletonLock"
if lock.exists():
    lock.unlink()

chrome_proc = subprocess.Popen([
    CHROME_BIN,
    f"--remote-debugging-port={CDP_PORT}",
    f"--user-data-dir={CDP_PROFILE}",
    "--no-first-run", "--no-default-browser-check", "--disable-default-apps",
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(5)

try:
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://localhost:{CDP_PORT}")
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()

        page.goto(BOOKMARKS_URL, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(4000)

        if "login" in page.url or "signin" in page.url or "myaccount" in page.url:
            error = "Login required — eco_chrome_profile session expired"
        else:
            soup = BeautifulSoup(page.content(), "html.parser")
            _main = soup.find("main") or soup
            consecutive_existing = 0

            def extract_title(a_tag, url):
                parent = a_tag.parent
                if parent and parent.name in ('h3', 'h2'):
                    t = a_tag.get_text(strip=True)
                    if t and len(t) > 15 and t not in SECTION_LABELS:
                        return t
                for ancestor in [a_tag.parent, a_tag.parent.parent if a_tag.parent else None]:
                    if ancestor is None: continue
                    cls = ' '.join(ancestor.get('class', []))
                    if 'headline' in cls.lower():
                        t = ancestor.get_text(strip=True)
                        if t and len(t) > 15 and t not in SECTION_LABELS:
                            return t
                anchor_text = a_tag.get_text(strip=True)
                if anchor_text and len(anchor_text) > 20 and anchor_text not in SECTION_LABELS:
                    return anchor_text
                slug = url.rstrip('/').split('/')[-1].replace('-', ' ')
                if len(slug) > 20:
                    return slug.title()
                return ""

            seen = set()
            for a in _main.select("a[href*='/20']"):
                href = a.get("href", "")
                if not re.search(r'/\d{4}/\d{2}/\d{2}/', href):
                    continue
                url = ("https://www.economist.com" + href if href.startswith("/") else href).split("?")[0]
                if any(p in url for p in JUNK_URL_PATHS):
                    continue
                art_id = make_id("The Economist", url)
                if art_id in seen:
                    continue
                seen.add(art_id)
                consecutive_existing += 1
                if consecutive_existing >= 3:
                    break
                title = extract_title(a, url)
                if not title or len(title) < 10 or title in SECTION_LABELS:
                    continue
                articles.append({
                    "id": art_id, "source": "The Economist", "url": url,
                    "title": title, "body": "", "summary": "", "topic": "", "tags": "[]",
                    "saved_at": now_ts(), "fetched_at": now_ts(),
                    "status": "title_only", "pub_date": extract_pub_date_from_url(url),
                    "auto_saved": 0
                })

        try: page.close()
        except: pass
        try: browser.disconnect()
        except: pass
except Exception as e:
    error = str(e)
finally:
    chrome_proc.terminate()

with open(OUT_PATH, 'w') as f:
    json.dump({"articles": articles, "error": error}, f)

print(f"eco_scraper_sub: {len(articles)} articles, error={error}")
