#!/usr/bin/env python3
"""
Reprocess the successful batch results with correct parsing and schema
"""

import sqlite3
import json
import requests
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "meridian.db"
CREDS = BASE_DIR / "credentials.json"

# Get credentials
creds = json.loads(CREDS.read_text())
ANTHROPIC_API_KEY = creds.get("anthropic_api_key", "")

# Download the successful results
batch_id = "msgbatch_018DNxhbr7z5rHkLGzkcSQjh"
headers = {
    "anthropic-version": "2023-06-01",
    "x-api-key": ANTHROPIC_API_KEY
}

print("🔄 Reprocessing successful batch results...")

# Get batch info
response = requests.get(f"https://api.anthropic.com/v1/messages/batches/{batch_id}", headers=headers)
data = response.json()
results_url = data.get("results_url")

if not results_url:
    print("❌ No results URL found")
    exit(1)

# Download results
results_resp = requests.get(results_url, headers=headers)
if results_resp.status_code != 200:
    print(f"❌ Download failed: {results_resp.status_code}")
    exit(1)

# Parse results
results = []
for line in results_resp.text.strip().split('\n'):
    if line:
        results.append(json.loads(line))

print(f"📥 Processing {len(results)} results...")

# Check available columns
con = sqlite3.connect(str(DB_PATH))
cur = con.cursor()

# Get schema
columns = cur.execute("PRAGMA table_info(articles)").fetchall()
available_columns = [col[1] for col in columns]
print(f"📋 Available columns: {available_columns}")

updated_count = 0
failed_count = 0

for result in results:
    custom_id = result.get("custom_id", "")
    article_id = custom_id.replace("enrich_", "")
    
    if result.get("result") and result["result"].get("type") == "succeeded":
        # Correct path: result.message.content[0].text
        content = result["result"]["message"]["content"][0]["text"]
        
        # Remove markdown wrapper if present
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        
        try:
            # Parse JSON response
            enrichment_data = json.loads(content)
            
            summary = enrichment_data.get("summary", "")
            key_themes = enrichment_data.get("key_themes", [])
            significance = enrichment_data.get("significance", "")
            
            # Combine into summary field (existing schema)
            full_summary = summary
            if key_themes:
                full_summary += f"\n\nKey themes: {', '.join(key_themes)}"
            if significance:
                full_summary += f"\n\nSignificance: {significance}"
            
            # Update database using existing schema
            cur.execute("""
                UPDATE articles 
                SET status = 'enriched',
                    summary = ?,
                    fetched_at = ?
                WHERE id = ?
            """, (full_summary, int(datetime.now().timestamp() * 1000), article_id))
            
            updated_count += 1
            print(f"✅ Updated article {article_id}")
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON for article {article_id}: {e}")
            print(f"   Raw content: {content[:200]}...")
            failed_count += 1
            
    else:
        print(f"❌ Unexpected result type for article {article_id}")
        failed_count += 1

con.commit()
con.close()

print(f"\n🎉 Batch reprocessing complete:")
print(f"   ✅ Updated: {updated_count}")
print(f"   ❌ Failed: {failed_count}")
print("💰 Cost savings achieved: 50% vs real-time API calls")

if updated_count > 0:
    print("\n🔄 Next steps:")
    print("   • Run vps_push.py to sync enriched articles to VPS")
    print("   • Deploy changes and restart Flask")
