"""
FT re-enrichment with updated selectors for FT's current markup.
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
    SELECT id, url, title, pub_date, LENGTH(body) as blen
    FROM articles
    WHERE source = 'Financial Times' AND url != ''
    AND (
        LENGTH(body) = 0
        OR (LENGTH(body) < 3000 AND (
            body LIKE 'The article%' OR body LIKE 'This article%'
            OR body LIKE 'The FT%' OR body LIKE 'Examines%'
            OR body LIKE 'Argues%' OR body LIKE 'Discusses%'
            OR body LIKE 'Explores%' OR body LIKE 'The author%'
            OR body LIKE 'The piece%' OR body LIKE 'Critiques%'
            OR body LIKE 'Analyzes%' OR body LIKE 'Assesses%'
        ))
    )
    ORDER BY LENGTH(body) ASC
""").fetchall()
conn.close()
articles = [dict(r) for r in rows]
print(f"Targeting {len(articles)} FT articles\n")

def call_haiku(prompt):
    payload = json.dumps({"model": "claude-haiku-4-5-20251001", "max_tokens": 600,
        "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=payload,
        headers={"Content-Type": "application/json", "x-api-key": API_KEY,
                 "anthropic-version": "2023-06-01"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

improved = skipped = failed = 0

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        '/Users/alexdakers/meridian-server/ft_profile',
        headless=False,
        args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
    )
    page = browser.new_page()

    # Warm up via saved articles page
    print("Warming FT session...")
    page.goto('https://www.ft.com/myft/saved-articles', wait_until='domcontentloaded', timeout=25000)
    page.wait_for_timeout(3000)
    print(f"Session: {page.title()[:50]}\n")

    for i, art in enumerate(articles):
        print(f"[{i+1}/{len(articles)}] {art['blen']}ch | {art['title'][:60]}")
        try:
            page.goto(art['url'], wait_until='domcontentloaded', timeout=25000)
            page.wait_for_timeout(2500)
            soup = BeautifulSoup(page.content(), 'html.parser')

            # Updated FT selectors for current markup
            paras = (
                soup.select('div.n-content-body p') or
                soup.select("div[class*='n-content-body'] p") or
                soup.select("div[class*='article__content'] p") or
                soup.select("div[class*='article-body'] p")
            )
            raw_text = ' '.join(p.get_text(strip=True) for p in paras
                                if len(p.get_text(strip=True)) > 40)

            if not raw_text or len(raw_text) < 300:
                print(f"  ⚠️  No text ({len(raw_text)} chars)")
                skipped += 1
                time.sleep(0.5)
                continue

            pub_date = art.get('pub_date', '') or ''
            if not pub_date:
                time_el = soup.select_one('time[datetime]')
                if time_el and time_el.get('datetime'):
                    m = _re.match(r'(\d{4}-\d{2}-\d{2})', time_el['datetime'])
                    if m: pub_date = m.group(1)

            prompt = f"""Analyse this FT article, respond ONLY with JSON:
{{"summary": "2-3 sentence summary", "tags": ["tag1","tag2","tag3"], "topic": "Markets/Economics/Geopolitics/Technology/Politics/Business/Energy/Finance/Society/Science"}}
Title: {art['title']}
Text: {raw_text[:4000]}"""

            data = call_haiku(prompt)
            enriched = json.loads(data['content'][0]['text'].replace('```json','').replace('```','').strip())

            conn2 = sqlite3.connect(DB)
            conn2.execute("UPDATE articles SET body=?, summary=?, tags=?, topic=?, pub_date=?, status='full_text' WHERE id=?",
                (raw_text[:12000], enriched.get('summary',''), json.dumps(enriched.get('tags',[])),
                 enriched.get('topic','Finance'), pub_date, art['id']))
            conn2.commit()
            conn2.close()

            improved += 1
            print(f"  ✅ {len(raw_text):,} chars")
            time.sleep(1.0)

        except Exception as e:
            print(f"  ❌ {e}")
            failed += 1

    browser.close()

print(f"\n=== Done: {improved} improved, {skipped} skipped, {failed} failed ===")
conn = sqlite3.connect(DB)
sizes = [r[0] for r in conn.execute("SELECT LENGTH(body) FROM articles WHERE source='Financial Times'").fetchall()]
conn.close()
avg = int(sum(sizes)/len(sizes)) if sizes else 0
full = sum(1 for s in sizes if s >= 3000)
print(f"FT: {len(sizes)} total | {full} full(>=3k) | avg {avg:,} chars")
