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
print(f"Targeting {len(articles)} articles with new section.rich-text selector\n")

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

improved = failed = 0

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        '/Users/alexdakers/meridian-server/fa_profile',
        headless=True,
        args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
    )
    page = browser.new_page()

    for i, art in enumerate(articles):
        print(f"[{i+1}/{len(articles)}] {art['body_len']}ch | {art['title'][:60]}")
        try:
            page.goto(art['url'], wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(3000)
            soup = BeautifulSoup(page.content(), 'html.parser')

            # Updated selector chain — includes section.rich-text
            paragraphs = (
                soup.select('div.article__body-content p') or
                soup.select('section.rich-text p') or
                soup.select('div.article__body p') or
                soup.select('div.article-body p')
            )
            raw_text = ' '.join(p.get_text(strip=True) for p in paragraphs
                                if len(p.get_text(strip=True)) > 40)

            if not raw_text or len(raw_text) < 500:
                print(f"  ⚠️  Still no text ({len(raw_text)} chars)")
                failed += 1
                continue

            # pub_date
            pub_date = art.get('pub_date', '') or ''
            meta = soup.select_one("meta[property='article:published_time']")
            if meta and meta.get('content'):
                m = _re.match(r'(\d{4}-\d{2}-\d{2})', meta['content'])
                if m: pub_date = m.group(1)

            # AI enrichment
            prompt = f"""Analyse this Foreign Affairs article, respond ONLY with JSON:
{{"summary": "2-3 sentence summary", "tags": ["tag1","tag2","tag3"], "topic": "Geopolitics"}}
Title: {art['title']}
Text: {raw_text[:5000]}"""

            data = call_haiku(prompt)
            enriched = json.loads(data['content'][0]['text'].replace('```json','').replace('```','').strip())

            conn2 = sqlite3.connect(DB)
            conn2.execute("""
                UPDATE articles SET body=?, summary=?, tags=?, topic=?, pub_date=?, status='full_text'
                WHERE id=?
            """, (raw_text[:12000], enriched.get('summary',''),
                  json.dumps(enriched.get('tags',[])), enriched.get('topic','Geopolitics'),
                  pub_date, art['id']))
            conn2.commit()
            conn2.close()

            improved += 1
            print(f"  ✅ {len(raw_text):6d} chars saved")
            time.sleep(1.5)

        except Exception as e:
            print(f"  ❌ {e}")
            failed += 1

    browser.close()

print(f"\n=== Done: {improved} improved, {failed} failed ===")

conn = sqlite3.connect(DB)
sizes = [r[0] for r in conn.execute("SELECT LENGTH(body) FROM articles WHERE source='Foreign Affairs'").fetchall()]
conn.close()
big = sum(1 for s in sizes if s >= 5000)
med = sum(1 for s in sizes if 1000 <= s < 5000)
avg = int(sum(sizes)/len(sizes)) if sizes else 0
print(f"FA final: {len(sizes)} total | {big} full(>=5k) | {med} medium | avg {avg} chars")
