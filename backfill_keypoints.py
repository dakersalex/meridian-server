#!/usr/bin/env python3
"""
Re-enrich articles that have body text but no key_points.
Uses direct Haiku calls (fast, cheap) rather than Batch API for immediate results.
Processes in batches of 10 with rate limiting.
"""
import sqlite3, json, urllib.request, time, logging
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB = BASE_DIR / "meridian.db"
CREDS = json.loads((BASE_DIR / "credentials.json").read_text())
API_KEY = CREDS.get("anthropic_api_key", "")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger()

def call_anthropic(payload, timeout=60):
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=data,
        headers={"Content-Type": "application/json", "x-api-key": API_KEY,
                 "anthropic-version": "2023-06-01"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())

conn = sqlite3.connect(str(DB))
conn.row_factory = sqlite3.Row

# Find articles with body text but no key_points
rows = conn.execute("""
    SELECT id, title, source, body, summary
    FROM articles 
    WHERE LENGTH(body) > 200 
    AND (key_points IS NULL OR key_points = '[]' OR key_points = '')
    AND status IN ('full_text', 'enriched')
    ORDER BY saved_at DESC
""").fetchall()

log.info(f"Found {len(rows)} articles needing key_points backfill")

updated = 0
errors = 0

for i, row in enumerate(rows):
    title = row['title']
    body = row['body'][:8000]
    
    prompt = f"""Analyse this article and respond ONLY with a JSON object (no markdown):
{{
  "keyPoints": ["1-2 sentence point capturing a key argument or finding — write 4-6 points"],
  "highlights": ["exact quote from the article (15-40 words) that captures a crucial insight — pick 3-5 passages"]
}}

Article title: {title}
Source: {row['source']}

Article text:
{body}"""

    try:
        result = call_anthropic({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 800,
            "messages": [{"role": "user", "content": prompt}]
        })
        text = result["content"][0]["text"]
        text = text.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(text)
        
        kp = json.dumps(parsed.get("keyPoints", []))
        hl = json.dumps(parsed.get("highlights", []))
        
        conn.execute("UPDATE articles SET key_points=?, highlights=? WHERE id=?",
                     (kp, hl, row['id']))
        conn.commit()
        updated += 1
        
        if updated % 20 == 0:
            log.info(f"  Progress: {updated}/{len(rows)} done")
        
        time.sleep(0.5)  # Rate limiting
        
    except Exception as e:
        errors += 1
        log.warning(f"  Error for '{title[:40]}': {e}")
        time.sleep(2)

conn.close()
log.info(f"Backfill complete: {updated} updated, {errors} errors out of {len(rows)} total")
