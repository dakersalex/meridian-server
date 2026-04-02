"""
Test Economist article fetching to diagnose selector issue.
Fetch one article and inspect DOM structure.
"""
from playwright.sync_api import sync_playwright
import sqlite3
from bs4 import BeautifulSoup

# Get a real Economist article URL
conn = sqlite3.connect('/Users/alexdakers/meridian-server/meridian.db')
rows = conn.execute("""
    SELECT url, title, LENGTH(body) as blen, body
    FROM articles
    WHERE source='The Economist' AND url != '' AND LENGTH(body) > 500
    LIMIT 1
""").fetchone()
conn.close()

url, title, blen, stored_body = rows
print(f"Testing: {title[:60]}")
print(f"Stored body: {blen} chars — preview: {stored_body[:150]}\n")

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        '/Users/alexdakers/meridian-server/economist_profile',
        headless=False,
        args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
    )
    page = browser.new_page()
    page.goto(url, wait_until='domcontentloaded', timeout=25000)
    page.wait_for_timeout(3000)

    soup = BeautifulSoup(page.content(), 'html.parser')

    # Test all our selectors
    sel1 = soup.select('p[data-component="paragraph"]')
    sel2 = soup.select('div[class*="article__body"] p')
    sel3 = soup.select('div[class*="body__"] p')
    sel4 = soup.select('section.rich-text p')

    print(f"p[data-component=paragraph]:  {len(sel1)} paragraphs")
    print(f"div[class*=article__body] p:  {len(sel2)} paragraphs")
    print(f"div[class*=body__] p:         {len(sel3)} paragraphs")
    print(f"section.rich-text p:          {len(sel4)} paragraphs")

    # Find actual article text using broader search
    all_substantial = [p for p in soup.select('p') if len(p.get_text(strip=True)) > 60]
    print(f"\nAll substantial p tags:       {len(all_substantial)}")

    # What class does the article body use?
    if sel1:
        text = ' '.join(p.get_text(strip=True) for p in sel1 if len(p.get_text(strip=True)) > 40)
        print(f"\ndata-component=paragraph text: {len(text)} chars")
        print(f"Preview: {text[:300]}")
    elif all_substantial:
        # Find the parent with most paragraphs
        parent_counts = {}
        for p in all_substantial:
            parent = p.parent
            key = parent.name + '.' + ' '.join(parent.get('class', []))[:50]
            parent_counts[key] = parent_counts.get(key, 0) + 1
        print(f"\nParagraph parent classes:")
        for k, v in sorted(parent_counts.items(), key=lambda x: -x[1])[:8]:
            print(f"  {v:3d}x  {k}")

    browser.close()
