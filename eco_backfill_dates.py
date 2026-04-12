#!/usr/bin/env python3
"""
Backfill pub_dates for all Economist articles by re-scraping the bookmarks page.
The bookmarks page shows the correct article date (e.g. "Apr 9th 2026")
which differs from the URL date (edition date).

Runs the full Load More loop to get all articles + their dates,
then updates the DB for any article where the scraped date differs from stored.
"""
import subprocess, time, re, sqlite3
from pathlib import Path
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

CDP_PROFILE = Path('/Users/alexdakers/meridian-server/eco_chrome_profile')
CDP_PORT = 9223
CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DB_PATH = '/Users/alexdakers/meridian-server/meridian.db'

DATE_PAT = re.compile(r'([A-Z][a-z]{2})\s+(\d{1,2})(?:st|nd|rd|th)?\s+(\d{4})')
MONTH_MAP = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,
             'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}
JUNK_URL_PATHS = ("/podcasts/", "/newsletters/", "/events/", "/films/", "/interactive/")

def parse_date_text(text):
    m = DATE_PAT.search(text)
    if m:
        mon, day, yr = m.group(1), int(m.group(2)), m.group(3)
        if mon in MONTH_MAP:
            return "%s-%02d-%02d" % (yr, MONTH_MAP[mon], day)
    return ""

def make_id(url):
    import hashlib
    return hashlib.sha1(("The Economist:" + url).encode()).hexdigest()[:16]

lock = CDP_PROFILE / "SingletonLock"
if lock.exists():
    lock.unlink()

proc = subprocess.Popen([
    CHROME_BIN,
    "--remote-debugging-port=" + str(CDP_PORT),
    "--user-data-dir=" + str(CDP_PROFILE),
    "--no-first-run", "--no-default-browser-check", "--disable-default-apps",
    "--window-position=-3000,-3000", "--window-size=1280,900",
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(5)

url_to_date = {}

try:
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:" + str(CDP_PORT))
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        page = ctx.new_page()

        page.goto("https://www.economist.com/for-you/bookmarks",
                  wait_until="domcontentloaded", timeout=45000)
        page.wait_for_selector("a[href*='/20']", timeout=15000)
        page.wait_for_timeout(3000)

        clicks = 0
        while True:
            prev_count = len(url_to_date)

            # Extract all visible articles + dates
            soup = BeautifulSoup(page.content(), "html.parser")
            main = soup.find("main") or soup

            for a in main.select("a[href*='/20']"):
                href = a.get("href", "")
                if not re.search(r'/\d{4}/\d{2}/\d{2}/', href):
                    continue
                url = ("https://www.economist.com" + href if href.startswith("/") else href).split("?")[0]
                if any(p in url for p in JUNK_URL_PATHS):
                    continue
                if url in url_to_date:
                    continue

                # Get date from grandparent text
                pub_date = ""
                for ancestor in [a.parent,
                                  a.parent.parent if a.parent else None,
                                  a.parent.parent.parent if a.parent and a.parent.parent else None]:
                    if ancestor is None:
                        continue
                    txt = ancestor.get_text(separator=" ", strip=True)
                    pub_date = parse_date_text(txt)
                    if pub_date:
                        break

                url_to_date[url] = pub_date

            print("After click " + str(clicks) + ": " + str(len(url_to_date)) + " articles with dates")

            # Load More
            try:
                btn = page.locator("button:has-text('Load More'), a:has-text('Load More')").first
                if not btn.is_visible(timeout=3000):
                    print("No Load More — done")
                    break
                btn.scroll_into_view_if_needed()
                page.wait_for_timeout(500)
                btn.click()
                page.wait_for_timeout(4000)
                clicks += 1
            except Exception:
                print("Load More not found — done")
                break

            if len(url_to_date) <= prev_count:
                print("No new articles — done")
                break

        browser.close()
except Exception as e:
    print("Error: " + str(e))
finally:
    proc.terminate()

print("\nScraped " + str(len(url_to_date)) + " articles with dates")

# Now update DB
c = sqlite3.connect(DB_PATH)
updated = 0
no_change = 0
not_in_db = 0

for url, scraped_date in url_to_date.items():
    if not scraped_date:
        continue
    art_id = make_id(url)
    row = c.execute("SELECT id, pub_date FROM articles WHERE id=? AND source='The Economist'", (art_id,)).fetchone()
    if not row:
        not_in_db += 1
        continue
    stored_date = row[1] or ""
    if stored_date != scraped_date:
        c.execute("UPDATE articles SET pub_date=? WHERE id=?", (scraped_date, art_id))
        print("  UPDATED: " + url[-60:] + "  " + stored_date + " -> " + scraped_date)
        updated += 1
    else:
        no_change += 1

c.commit()
c.close()

print("\nDone: " + str(updated) + " updated, " + str(no_change) + " unchanged, " + str(not_in_db) + " not in DB")
