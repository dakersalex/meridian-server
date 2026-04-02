from playwright.sync_api import sync_playwright
import sqlite3, json
from bs4 import BeautifulSoup

# Get the SHORTEST FA articles to understand why they're truncated
conn = sqlite3.connect('/Users/alexdakers/meridian-server/meridian.db')
rows = conn.execute(
    "SELECT url, title, LENGTH(body), body FROM articles "
    "WHERE source='Foreign Affairs' AND url!='' AND LENGTH(body) BETWEEN 1000 AND 3000 "
    "ORDER BY LENGTH(body) LIMIT 4"
).fetchall()
conn.close()

results = {'test_articles': []}

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        '/Users/alexdakers/meridian-server/fa_profile',
        headless=True,
        args=['--no-sandbox']
    )
    page = browser.new_page()

    for url, title, stored_len, stored_body in rows[:3]:
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(3000)
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # Use the correct selector we found
            paras = (soup.select('div.article__body-content p') or
                     soup.select('div.article__body p') or
                     soup.select('div.article-body p') or
                     soup.select('main p'))
            body = ' '.join(p.get_text(strip=True) for p in paras if len(p.get_text(strip=True)) > 40)

            # Check for gate/paywall elements
            gate_els = soup.select('[class*="gate"], [class*="paywall"], [class*="limit"], [class*="wall"], [class*="lock"]')
            gate_classes = [' '.join(el.get('class',[])) for el in gate_els[:5]]

            # Check if there's a "read more" / truncation indicator
            read_more = soup.select('[class*="read-more"], [class*="truncat"], [class*="teaser"]')
            read_more_text = [el.get_text(strip=True)[:80] for el in read_more[:3]]

            results['test_articles'].append({
                'title': title[:60],
                'stored_len': stored_len,
                'fetched_len': len(body),
                'stored_preview': stored_body[:200],
                'fetched_preview': body[:300],
                'gate_classes': gate_classes,
                'read_more': read_more_text,
                'page_title': page.title()[:80],
            })
        except Exception as e:
            results['test_articles'].append({'url': url[-50:], 'error': str(e)})

    browser.close()

with open('/Users/alexdakers/meridian-server/tmp_fa_result.txt', 'w') as f:
    f.write(json.dumps(results, indent=2))
print("DONE")
