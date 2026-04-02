"""
Re-fetch FA articles and store RAW text as body (not AI fullSummary).
Then run AI enrichment which produces summary/tags/topic separately.
This matches how FT/Economist articles are stored.
"""
from playwright.sync_api import sync_playwright
import sqlite3, json, time, urllib.request, re as _re
from bs4 import BeautifulSoup

DB = '/Users/alexdakers/meridian-server/meridian.db'
CREDS = json.loads(open('/Users/alexdakers/meridian-server/credentials.json').read())
API_KEY = CREDS['anthropic_api_key']

# Get FA articles where raw text is likely available but not stored
# (stored body < 8000 chars — AI summaries top out ~3000, real articles are longer)
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
rows = conn.execute("""
    SELECT id, url, title, pub_date, body
    FROM articles
    WHERE source = 'Foreign Affairs' AND url != ''
    ORDER BY saved_at DESC
""").fetchall()
conn.close()
articles = [dict(r) for r in rows]
print(f"Total FA articles to process: {len(articles)}")

def call_haiku(prompt):
    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=payload,
        headers={"Content-Type": "application/json", "x-api-key": API_KEY,
                 "anthropic-version": "2023-06-01"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

success = skip = fail = 0

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        '/Users/alexdakers/meridian-server/fa_profile',
        headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
    )
    page = browser.new_page()

    for i, art in enumerate(articles):
        try:
            page.goto(art['url'], wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(2500)
            soup = BeautifulSoup(page.content(), 'html.parser')

            paras = (soup.select('div.article__body-content p') or
                     soup.select('div.article__body p') or
                     soup.select('div.article-body p'))
            raw_text = ' '.join(p.get_text(strip=True) for p in paras if len(p.get_text(strip=True)) > 40)

            if not raw_text or len(raw_text) < 500:
                print(f"[{i+1}/{len(articles)}] SKIP (no raw text): {art['title'][:55]}")
                skip += 1
                continue

            # Only re-process if raw text is substantially longer than stored body
            if len(raw_text) <= len(art.get('body', '')) * 1.2:
                print(f"[{i+1}/{len(articles)}] SKIP (already good, {len(art.get('body',''))} stored vs {len(raw_text)} raw): {art['title'][:40]}")
                skip += 1
                continue

            # pub_date
            pub_date = art.get('pub_date', '') or ''
            meta = soup.select_one("meta[property='article:published_time']")
            if meta and meta.get('content'):
                m = _re.match(r'(\d{4}-\d{2}-\d{2})', meta['content'])
                pub_date = m.group(1) if m else pub_date

            # AI enrichment — summary/tags/topic only (not fullSummary stored as body)
            prompt = f"""You are a research assistant. Analyse this article and respond ONLY with a JSON object (no markdown):
{{
  "summary": "2-3 sentence summary of the main argument",
  "tags": ["tag1", "tag2", "tag3"],
  "topic": "pick from: Markets, Economics, Geopolitics, Technology, Politics, Business, Energy, Finance, Society, Science"
}}

Article title: {art['title']}
Article text:
{raw_text[:6000]}"""

            data = call_haiku(prompt)
            enriched = json.loads(data['content'][0]['text'].replace('```json','').replace('```','').strip())

            # Store RAW text as body (not AI prose) — same pattern as FT/Economist
            conn2 = sqlite3.connect(DB)
            conn2.execute("""
                UPDATE articles
                SET body=?, summary=?, tags=?, topic=?, pub_date=?, status='full_text'
                WHERE id=?
            """, (
                raw_text[:12000],
                enriched.get('summary', ''),
                json.dumps(enriched.get('tags', [])),
                enriched.get('topic', ''),
                pub_date,
                art['id']
            ))
            conn2.commit()
            conn2.close()

            success += 1
            print(f"[{i+1}/{len(articles)}] ✅ {len(raw_text):6d} chars — {art['title'][:55]}")
            time.sleep(1.2)

        except Exception as e:
            fail += 1
            print(f"[{i+1}/{len(articles)}] ❌ {art['title'][:50]}: {e}")
            time.sleep(1)

    browser.close()

print(f"\n=== Done: {success} updated, {skip} skipped, {fail} failed of {len(articles)} total ===")

# Final stats
conn = sqlite3.connect(DB)
rows = conn.execute("SELECT COUNT(*), AVG(LENGTH(body)), MIN(LENGTH(body)), MAX(LENGTH(body)) FROM articles WHERE source='Foreign Affairs'").fetchone()
conn.close()
print(f"FA body stats: count={rows[0]}, avg={int(rows[1] or 0)}, min={rows[2]}, max={rows[3]}")
