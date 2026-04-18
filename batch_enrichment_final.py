#!/usr/bin/env python3
"""
Batch enrichment proof of concept for Meridian
Processes title_only articles using Claude Batch API for 50% cost savings
"""

import sqlite3
import json
import time
import requests
import os
from datetime import datetime
from pathlib import Path

# Config - use same pattern as server.py
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "meridian.db"
CREDS = BASE_DIR / "credentials.json"

def load_creds():
    """Load credentials from same file as server.py"""
    if not CREDS.exists():
        print(f"❌ Credentials file not found: {CREDS}")
        return {}
    return json.loads(CREDS.read_text())

# Get API key
creds = load_creds()
ANTHROPIC_API_KEY = creds.get("anthropic_api_key", "")
if not ANTHROPIC_API_KEY:
    print("❌ anthropic_api_key not found in credentials.json")
    exit(1)

BASE_URL = "https://api.anthropic.com"
HEADERS = {
    "anthropic-version": "2023-06-01",
    "content-type": "application/json",
    "x-api-key": ANTHROPIC_API_KEY
}

def get_title_only_articles():
    """Get articles needing enrichment"""
    con = sqlite3.connect(str(DB_PATH))
    cur = con.cursor()
    
    articles = cur.execute("""
        SELECT id, title, source, url, pub_date 
        FROM articles 
        WHERE status = 'title_only' 
        ORDER BY saved_at DESC 
        LIMIT 50
    """).fetchall()
    
    con.close()
    
    result = []
    for row in articles:
        result.append({
            "id": row[0],
            "title": row[1],
            "source": row[2], 
            "url": row[3],
            "pub_date": row[4]
        })
    
    print(f"📋 Found {len(result)} articles needing enrichment")
    for art in result[:5]:  # Show first 5
        print(f"   • {art['id']}: {art['title'][:60]}... ({art['source']})")
    if len(result) > 5:
        print(f"   • ... and {len(result) - 5} more")
    
    return result

def create_batch_requests(articles):
    """Convert articles to batch API format"""
    requests_data = []
    
    for article in articles:
        # Same enrichment system prompt from server.py
        system_prompt = """You are a research assistant analyzing news articles. Extract key information to help readers understand the article's significance.

Respond with EXACTLY this JSON structure (no additional text):
{
  "summary": "2-3 sentence summary of the main points",
  "key_themes": ["theme1", "theme2", "theme3"],
  "significance": "Why this matters (1-2 sentences)"
}"""

        user_prompt = f"""Analyze this article:

Title: {article['title']}
Source: {article['source']}
URL: {article['url']}
Date: {article['pub_date']}

Based on the title, source, and context, provide the analysis."""

        # Format for Batch API - use working model alias
        request = {
            "custom_id": f"enrich_{article['id']}",
            "params": {
                "model": "claude-sonnet-4-6",  # Working alias that auto-updates to latest
                "max_tokens": 500,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            }
        }
        
        requests_data.append(request)
    
    return requests_data

def submit_batch(requests_data):
    """Submit batch to Anthropic API"""
    print(f"📦 Creating batch with {len(requests_data)} requests...")
    
    # Create batch payload - correct format per docs
    payload = {
        "requests": requests_data
    }
    
    # Submit batch to correct endpoint
    response = requests.post(
        f"{BASE_URL}/v1/messages/batches",
        headers=HEADERS,
        json=payload
    )
    
    if response.status_code != 200:
        print(f"❌ Batch submission failed: {response.status_code}")
        print(response.text)
        return None
    
    batch_data = response.json()
    batch_id = batch_data.get("id")
    
    print(f"✅ Batch submitted: {batch_id}")
    print(f"📊 Status: {batch_data.get('processing_status')}")
    print(f"⏱️  Created: {batch_data.get('created_at')}")
    print(f"💰 50% cost savings vs real-time API calls")
    print(f"🎯 Model: claude-sonnet-4-6 (auto-updates to latest Sonnet 4.6)")
    
    return batch_id

def check_batch_status(batch_id):
    """Check if batch is complete"""
    response = requests.get(
        f"{BASE_URL}/v1/messages/batches/{batch_id}",
        headers=HEADERS
    )
    
    if response.status_code != 200:
        print(f"❌ Status check failed: {response.status_code}")
        return None
    
    return response.json()

def wait_for_completion(batch_id, max_wait_minutes=60):
    """Poll batch until completion"""
    print(f"⏳ Waiting for batch completion (max {max_wait_minutes} minutes)...")
    
    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60
    
    while True:
        status_data = check_batch_status(batch_id)
        if not status_data:
            return None
        
        status = status_data.get("processing_status")
        request_counts = status_data.get("request_counts", {})
        
        print(f"📊 Status: {status}")
        if request_counts:
            total = request_counts.get("total", 0)
            completed = request_counts.get("succeeded", 0)
            failed = request_counts.get("errored", 0)
            processing = request_counts.get("processing", 0)
            print(f"   Progress: {completed}/{total} completed, {processing} processing, {failed} failed")
        
        if status == "ended":
            print("✅ Batch completed successfully!")
            return status_data
        elif status == "failed":
            print("❌ Batch failed")
            return status_data
        elif status in ["cancelling", "cancelled"]:
            print("⚠️ Batch cancelled")
            return status_data
        
        # Check timeout
        elapsed = time.time() - start_time
        if elapsed > max_wait_seconds:
            print(f"⏰ Timeout after {max_wait_minutes} minutes")
            print("💡 Batch may still be processing - run again later to check results")
            return status_data
        
        time.sleep(30)  # Check every 30 seconds

def download_results(batch_id):
    """Download and parse batch results"""
    # Get batch info to find results URL
    batch_data = check_batch_status(batch_id)
    if not batch_data:
        return None
    
    results_url = batch_data.get("results_url")
    if not results_url:
        print("❌ No results URL found")
        return None
    
    # Download results from results URL
    response = requests.get(results_url, headers=HEADERS)
    
    if response.status_code != 200:
        print(f"❌ Download failed: {response.status_code}")
        return None
    
    # Parse JSONL results
    results = []
    for line in response.text.strip().split('\n'):
        if line:
            results.append(json.loads(line))
    
    print(f"📥 Downloaded {len(results)} results")
    
    return results

def update_articles(results):
    """Update database with enrichment results"""
    con = sqlite3.connect(str(DB_PATH))
    cur = con.cursor()
    
    updated_count = 0
    failed_count = 0
    
    for result in results:
        custom_id = result.get("custom_id", "")
        article_id = custom_id.replace("enrich_", "")
        
        if result.get("result") and result["result"].get("type") == "message":
            # Extract response content
            content = result["result"]["content"][0]["text"]
            
            try:
                # Parse JSON response
                enrichment_data = json.loads(content)
                
                summary = enrichment_data.get("summary", "")
                key_themes = enrichment_data.get("key_themes", [])
                significance = enrichment_data.get("significance", "")
                
                # Update database
                cur.execute("""
                    UPDATE articles 
                    SET status = 'enriched',
                        summary = ?,
                        key_themes = ?,
                        significance = ?,
                        enriched_at = ?
                    WHERE id = ?
                """, (summary, json.dumps(key_themes), significance, 
                     datetime.now().isoformat(), article_id))
                
                updated_count += 1
                print(f"✅ Updated article {article_id}")
                
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON for article {article_id}: {e}")
                print(f"   Raw content: {content[:200]}...")
                failed_count += 1
                
        else:
            error_info = result.get("error", {})
            error_msg = error_info.get("message", "Unknown error")
            print(f"❌ API error for article {article_id}: {error_msg}")
            failed_count += 1
    
    con.commit()
    con.close()
    
    print(f"\n📊 Batch enrichment complete:")
    print(f"   ✅ Updated: {updated_count}")
    print(f"   ❌ Failed: {failed_count}")
    
    return updated_count

def main():
    """Main batch enrichment workflow"""
    print("🚀 Starting batch enrichment proof of concept...")
    print(f"📂 Database: {DB_PATH}")
    print(f"🔑 Credentials: {CREDS}")
    print(f"🎯 Model: claude-sonnet-4-6 (alias auto-updates to latest Sonnet 4.6)")
    
    # Get articles to enrich
    articles = get_title_only_articles()
    if not articles:
        print("✨ No articles need enrichment")
        return
    
    # Create batch requests
    requests_data = create_batch_requests(articles)
    
    # Submit batch
    batch_id = submit_batch(requests_data)
    if not batch_id:
        print("❌ Failed to submit batch")
        return
    
    # Wait for completion
    final_status = wait_for_completion(batch_id)
    if not final_status or final_status.get("processing_status") != "ended":
        print("❌ Batch did not complete successfully")
        print(f"💡 Batch ID: {batch_id} - save this to check status later")
        return
    
    # Download and process results
    results = download_results(batch_id)
    if not results:
        print("❌ Failed to download results")
        return
    
    # Update database
    updated_count = update_articles(results)
    
    print(f"\n🎉 Batch enrichment complete! Updated {updated_count} articles")
    print("💰 Cost savings: 50% compared to real-time API calls")
    print("🔄 Run vps_push.py to sync enriched articles to VPS")

if __name__ == "__main__":
    main()
