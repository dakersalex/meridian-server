from playwright.sync_api import sync_playwright
import sqlite3
from bs4 import BeautifulSoup

conn = sqlite3.connect('/Users/alexdakers/meridian-server/meridian.db')
# Get a mid-range FA article
rows = conn.execute(
    "SELECT url, title, body FROM articles WHERE source='Foreign Affairs' "
    "AND LENGTH(body) BETWEEN 2400 AND 2900 LIMIT 2"
).fetchall()
conn.close()

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        '/Users/alexdakers/meridian-server/fa_profile',
        headless=True, args=['--no-sandbox']
    )
    page = browser.new_page()
    for url, title, stored_body in rows:
        page.goto(url, wait_until='domcontentloaded', timeout=25000)
        page.wait_for_timeout(2500)
        soup = BeautifulSoup(page.content(), 'html.parser')
        paras = soup.select('div.article__body-content p') or soup.select('div.article__body p')
        raw_text = ' '.join(p.get_text(strip=True) for p in paras if len(p.get_text(strip=True)) > 40)
        print(f"Title: {title[:60]}")
        print(f"Stored body: {len(stored_body)} chars")
        print(f"Raw fetched text: {len(raw_text)} chars")
        print(f"Raw preview: {raw_text[:200]}")
        print("---")
    browser.close()
