"""
Re-fetch all Economist articles using Playwright + correct selector.
Stores raw article text as body (not AI summary).
Re-runs AI enrichment for summary/tags/topic only.
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
    WHERE source = 'The Economist'
      AND url != ''
      AND LENGTH(body) < 6000
    ORDER BY saved_at DESC
""").fetchall()
conn.close()
articles = [dict(r) for r in rows]
print(f"Targeting {len(articles)} Economist articles with short/AI-summary bodies\n")

def call_haiku(prompt):
    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 600,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=payload,
        headers={"Content-Type": "application/json", "x-api-key": API_KEY,
                 "anthropic-version": "2023-06-01"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

improved = skipped = failed = 0

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        '/Users/alexdakers/meridian-server/economist_profile',
        headless=False,
        args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
    )
    page = browser.new_page()

    # Warm up
    print("Warming up Economist session...")
    page.goto('https://www.economist.com', wait_until='domcontentloaded', timeout=25000)
    page.wait_for_timeout(3000)
    print(f"Ready: {page.title()[:50]}\n")

    for i, art in enumerate(articles):
        print(f"[{i+1}/{len(articles)}] {art['body_len']}ch | {art['title'][:60]}")
        try:
            page.goto(art['url'], wait_until='domcontentloaded', timeout=25000)
            page.wait_for_timeout(2500)
            soup = BeautifulSoup(page.content(), 'html.parser')

            # Primary selector confirmed working
            paras = soup.select('p[data-component="paragraph"]')
            raw_text = ' '.join(p.get_text(strip=True) for p in paras
                                if len(p.get_text(strip=True)) > 30)

            # Fallback selectors
            if not raw_text or len(raw_text) < 300:
                paras = soup.select('div[class*="article__body"] p') or soup.select('div[class*="body__"] p')
                raw_text = ' '.join(p.get_text(strip=True) for p in paras
                                    if len(p.get_text(strip=True)) > 30)

            if not raw_text or len(raw_text) < 300:
                print(f"  ⚠️  No text ({len(raw_text)} chars) — skipping")
                skipped += 1
                time.sleep(0.5)
                continue

            # pub_date from URL (most reliable for Economist)
            pub_date = art.get('pub_date', '') or ''
            m = _re.search(r'/(\d{4})/(\d{2})/(\d{2})/', art['url'])
            if m:
                pub_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

            # AI enrichment — summary/tags/topic only, body = raw_text
            prompt = f"""Analyse this Economist article, respond ONLY with JSON:
{{"summary": "2-3 sentence summary of the main argument", "tags": ["tag1","tag2","tag3"], "topic": "one of: Markets, Economics, Geopolitics, Technology, Politics, Business, Energy, Finance, Society, Science"}}

Title: {art['title']}
Text: {raw_text[:4000]}"""

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
                enriched.get('topic', 'Economics'),
                pub_date,
                art['id']
            ))
            conn2.commit()
            conn2.close()

            improved += 1
            print(f"  ✅ {len(raw_text):6,} chars saved")
            time.sleep(1.2)

        except Exception as e:
            print(f"  ❌ {e}")
            failed += 1
            time.sleep(1)

    browser.close()

print(f"\n=== Done: {improved} improved, {skipped} skipped, {failed} failed of {len(articles)} ===")

# Final stats
conn = sqlite3.connect(DB)
sizes = [r[0] for r in conn.execute("SELECT LENGTH(body) FROM articles WHERE source='The Economist'").fetchall()]
conn.close()
buckets = {'<500': sum(1 for s in sizes if s < 500),
           '500-2k': sum(1 for s in sizes if 500 <= s < 2000),
           '2k-5k': sum(1 for s in sizes if 2000 <= s < 5000),
           '5k-10k': sum(1 for s in sizes if 5000 <= s < 10000),
           '10k+': sum(1 for s in sizes if s >= 10000)}
avg = int(sum(sizes)/len(sizes)) if sizes else 0
print(f"Economist final: {len(sizes)} total | avg {avg:,} chars")
for k, v in buckets.items():
    print(f"  {k}: {v}")
