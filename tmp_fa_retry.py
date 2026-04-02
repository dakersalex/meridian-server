"""
Second targeted retry: FA articles still under 4000 chars.
Longer page waits (3.5s + scroll) to handle CF cookie refresh.
"""
from playwright.sync_api import sync_playwright
import sqlite3, json, time, urllib.request, re as _re
from bs4 import BeautifulSoup

DB = '/Users/alexdakers/meridian-server/meridian.db'
CREDS = json.loads(open('/Users/alexdakers/meridian-server/credentials.json').read())
API_KEY = CREDS['anthropic_api_key']

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
rows = conn.execute("""
    SELECT id, url, title, pub_date, LENGTH(body) as body_len
    FROM articles
    WHERE source = 'Foreign Affairs' AND url != '' AND LENGTH(body) < 4000
    ORDER BY LENGTH(body) ASC
""").fetchall()
conn.close()
articles = [dict(r) for r in rows]
print(f"Targeting {len(articles)} articles still under 4000 chars\n")

def call_haiku(prompt):
    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 800,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=payload,
        headers={"Content-Type": "application/json", "x-api-key": API_KEY,
                 "anthropic-version": "2023-06-01"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

improved = paywalled = 0

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        '/Users/alexdakers/meridian-server/fa_profile',
        headless=False,
        args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
    )
    page = browser.new_page()

    # Warm up — visit homepage + one article to refresh all CF cookies
    print("Warming up CF session...")
    page.goto('https://www.foreignaffairs.com', wait_until='domcontentloaded', timeout=20000)
    page.wait_for_timeout(4000)
    page.goto('https://www.foreignaffairs.com/iran', wait_until='domcontentloaded', timeout=20000)
    page.wait_for_timeout(3000)
    print(f"Warm-up done. Starting articles...\n")

    for i, art in enumerate(articles):
        print(f"[{i+1}/{len(articles)}] {art['body_len']}ch | {art['title'][:60]}")
        try:
            page.goto(art['url'], wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(3500)  # longer wait

            # Scroll to bottom to trigger any lazy-loaded content
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1500)
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(500)

            soup = BeautifulSoup(page.content(), 'html.parser')
            paras = (soup.select('div.article__body-content p') or
                     soup.select('div.article__body p') or
                     soup.select('div.article-body p'))
            raw_text = ' '.join(p.get_text(strip=True) for p in paras
                                if len(p.get_text(strip=True)) > 40)

            if not raw_text or len(raw_text) < 800:
                print(f"  ⛔ Paywalled/empty ({len(raw_text)} chars)")
                paywalled += 1
                time.sleep(1)
                continue

            print(f"  → Got {len(raw_text)} chars")

            # pub_date
            pub_date = art.get('pub_date', '') or ''
            meta = soup.select_one("meta[property='article:published_time']")
            if meta and meta.get('content'):
                m = _re.match(r'(\d{4}-\d{2}-\d{2})', meta['content'])
                if m: pub_date = m.group(1)

            # AI enrichment
            prompt = f"""Analyse this Foreign Affairs article and respond ONLY with JSON (no markdown):
{{"summary": "2-3 sentence summary of the main argument", "tags": ["tag1","tag2","tag3"], "topic": "Geopolitics"}}

Title: {art['title']}
Text: {raw_text[:5000]}"""

            data = call_haiku(prompt)
            enriched = json.loads(data['content'][0]['text'].replace('```json','').replace('```','').strip())

            conn2 = sqlite3.connect(DB)
            conn2.execute("""
                UPDATE articles
                SET body=?, summary=?, tags=?, topic=?, pub_date=?, status='full_text'
                WHERE id=?
            """, (
                raw_text[:12000],
                enriched.get('summary', ''),
                json.dumps(enriched.get('tags', [])),
                enriched.get('topic', 'Geopolitics'),
                pub_date,
                art['id']
            ))
            conn2.commit()
            conn2.close()

            improved += 1
            print(f"  ✅ Saved {len(raw_text)} chars")
            time.sleep(2)

        except Exception as e:
            print(f"  ❌ {e}")
            paywalled += 1
            time.sleep(1)

    browser.close()

print(f"\n=== Done: {improved} improved, {paywalled} still paywalled ===")

# Final stats
conn = sqlite3.connect(DB)
rows = conn.execute("SELECT LENGTH(body) FROM articles WHERE source='Foreign Affairs'").fetchall()
conn.close()
sizes = [r[0] for r in rows]
big = sum(1 for s in sizes if s >= 5000)
med = sum(1 for s in sizes if 1000 <= s < 5000)
tiny = sum(1 for s in sizes if s < 1000)
avg = int(sum(sizes)/len(sizes)) if sizes else 0
print(f"FA final: {len(sizes)} total | {big} full(>=5k) | {med} medium | {tiny} short | avg {avg} chars")
