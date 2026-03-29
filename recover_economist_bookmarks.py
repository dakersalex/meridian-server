#!/usr/bin/env python3
"""
One-off script to recover all Economist bookmarks after accidental deletion.
Scrapes the full bookmarks page ignoring the 'stop on existing' logic,
re-saves all articles found with correct title extraction.
Run once after Flask is restarted.
"""
import sys, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from server import (
    init_db, make_id, now_ts, upsert_article, article_exists,
    extract_pub_date_from_url, log, DB_PATH, BASE_DIR
)
import sqlite3

try:
    from playwright.sync_api import sync_playwright
    from bs4 import BeautifulSoup
except ImportError:
    print("playwright/bs4 not installed")
    sys.exit(1)

SAVED_URL = "https://www.economist.com/for-you/bookmarks"

JUNK_URL_PATHS = ("/podcasts/", "/newsletters/", "/events/", "/films/")
JUNK_PREFIXES  = ("The War Room newsletter:", "Blighty newsletter:", "The US in Brief:",
                  "Espresso:", "The World in Brief:", "The Economist explains:",
                  "Graphic detail:", "KAL's cartoon")

SECTION_LABELS = {
    'Finance & economics', 'Middle East & Africa', 'Science & technology',
    'Business', 'United States', 'Europe', 'Charlemagne', 'Schumpeter',
    'Buttonwood', 'Free exchange', 'Free Exchange', 'Lexington', 'Leaders',
    'Briefing', 'By Invitation', 'Bagehot', 'The Telegram', 'Well informed',
    'Graphic detail', 'Christmas Specials', 'International', 'Special report',
    'The Americas', 'Asia', 'Britain', 'China', 'Culture', 'Obituary',
    'Schools brief', 'Technology Quarterly', 'The world this week',
    'The World Ahead', 'Letters', 'Index',
}

def is_junk_url(url):
    return any(p in url for p in JUNK_URL_PATHS)

def extract_title(a_tag, url):
    """Extract article title from Economist bookmark card.
    Structure: <h3 class='headline_mb-teaser__headline__...'>
                 <a href='/YYYY/MM/DD/slug'>headline text</a>
               </h3>
    The <a> is INSIDE the h3, so its text IS the title."""
    # Strategy 1: anchor text is the title if <a> is inside h3/h2
    parent = a_tag.parent
    if parent and parent.name in ('h3', 'h2'):
        t = a_tag.get_text(strip=True)
        if t and len(t) > 15 and t not in SECTION_LABELS:
            return t
    # Strategy 2: headline class on parent or grandparent
    for ancestor in [a_tag.parent, a_tag.parent.parent if a_tag.parent else None]:
        if ancestor is None: continue
        cls = ' '.join(ancestor.get('class', []))
        if 'headline' in cls.lower():
            t = ancestor.get_text(strip=True)
            if t and len(t) > 15 and t not in SECTION_LABELS:
                return t
    # Strategy 3: anchor text if substantial
    anchor = a_tag.get_text(strip=True)
    if anchor and len(anchor) > 20 and anchor not in SECTION_LABELS:
        return anchor
    # Strategy 4: URL slug as last resort
    slug = url.rstrip('/').split('/')[-1].replace('-', ' ')
    if len(slug) > 20:
        return slug.title()
    return ""

init_db()
recovered = 0
skipped_existing = 0
skipped_junk = 0
skipped_no_title = 0

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        str(BASE_DIR / "economist_profile"),
        headless=False,
        args=["--disable-blink-features=AutomationControlled"]
    )
    page = browser.new_page()
    print("Opening bookmarks page...")
    page.goto(SAVED_URL, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(4000)

    if "login" in page.url or "signin" in page.url:
        print("Login required — waiting 90s...")
        page.wait_for_timeout(90000)
        page.goto(SAVED_URL, wait_until="domcontentloaded", timeout=40000)
        page.wait_for_timeout(4000)

    print(f"Page loaded: {page.url}")

    # Click Load More to get all bookmarks
    for i in range(30):
        try:
            btn = (
                page.locator("button").filter(has_text="Load more").first
                if page.locator("button").filter(has_text="Load more").count() > 0
                else None
            )
            if btn is None:
                print(f"No more 'Load more' after {i} clicks")
                break
            btn.click()
            page.wait_for_timeout(1500)
            print(f"  Clicked Load More ({i+1})")
        except Exception as e:
            print(f"  Load More stopped: {e}")
            break

    soup = BeautifulSoup(page.content(), "html.parser")
    browser.close()

seen_ids = set()
for a in soup.select("a[href*='/20']"):
    href = a.get("href", "")
    if not re.search(r'/\d{4}/\d{2}/\d{2}/', href):
        continue
    url = ("https://www.economist.com" + href if href.startswith("/") else href).split("?")[0]

    if is_junk_url(url):
        skipped_junk += 1
        continue

    art_id = make_id("The Economist", url)
    if art_id in seen_ids:
        continue
    seen_ids.add(art_id)

    # Don't overwrite existing full_text articles
    with sqlite3.connect(DB_PATH) as cx:
        existing = cx.execute("SELECT status FROM articles WHERE id=?", (art_id,)).fetchone()
    if existing and existing[0] == "full_text":
        skipped_existing += 1
        continue

    title = extract_title(a, url)
    if not title or len(title) < 10 or title in SECTION_LABELS:
        # Last resort: try any title prefix from known junk list
        if any(title.startswith(p) for p in JUNK_PREFIXES):
            skipped_junk += 1
        else:
            skipped_no_title += 1
            print(f"  NO TITLE: {url[-60:]}")
        continue

    art = {
        "id": art_id,
        "source": "The Economist",
        "url": url,
        "title": title,
        "body": "", "summary": "", "topic": "", "tags": "[]",
        "saved_at": now_ts(), "fetched_at": now_ts(),
        "status": "title_only",
        "pub_date": extract_pub_date_from_url(url),
        "auto_saved": 0,
    }
    upsert_article(art)
    recovered += 1
    print(f"  SAVED: {title[:70]}")

print(f"\nDone — recovered {recovered}, skipped existing {skipped_existing}, "
      f"no title {skipped_no_title}, junk {skipped_junk}")
print("Run 'Sync All' in Meridian to enrich full text for recovered articles")
