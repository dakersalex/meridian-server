#!/usr/bin/env python3
"""
eco_fetch_sub.py — Fetch full text for Economist articles via CDP subprocess.
Called by enrich_title_only_articles() to avoid Flask event loop conflict.
Args: <cdp_profile_dir> <cdp_port> <input_json_path> <output_json_path>
Input JSON: [{"id": ..., "url": ..., "title": ...}]
Output JSON: [{"id": ..., "body": ..., "pub_date": ...}]
"""
import sys, json, time, subprocess, re
from pathlib import Path
from playwright.sync_api import sync_playwright

CDP_PROFILE = Path(sys.argv[1])
CDP_PORT = int(sys.argv[2])
IN_PATH = sys.argv[3]
OUT_PATH = sys.argv[4]
CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

with open(IN_PATH) as f:
    articles = json.load(f)

results = []

if not articles:
    with open(OUT_PATH, 'w') as f:
        json.dump(results, f)
    sys.exit(0)

# Clear stale lock
lock = CDP_PROFILE / "SingletonLock"
if lock.exists():
    lock.unlink()

chrome_proc = subprocess.Popen([
    CHROME_BIN,
    f"--remote-debugging-port={CDP_PORT}",
    f"--user-data-dir={CDP_PROFILE}",
    "--no-first-run", "--no-default-browser-check", "--disable-default-apps",
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(5)

def extract_pub_date(url):
    m = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""

def fetch_text(page, url):
    try:
        resp = page.goto(url, wait_until="domcontentloaded", timeout=25000)
        if resp and resp.status == 404:
            return "", ""
        page.wait_for_timeout(2500)
        # Extract paragraphs using Economist's data-component attribute
        paras = page.query_selector_all('[data-component="paragraph"]')
        text = " ".join(p.inner_text() for p in paras if p.inner_text().strip())
        if not text or len(text) < 100:
            # Fallback: article body tag
            body = page.query_selector('article')
            if body:
                text = body.inner_text()
        pub_date = extract_pub_date(url)
        return text[:12000], pub_date
    except Exception as e:
        print(f"  fetch error {url[-50:]}: {e}", file=sys.stderr)
        return "", ""

try:
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://localhost:{CDP_PORT}")
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()

        for art in articles:
            body, pub_date = fetch_text(page, art["url"])
            results.append({
                "id": art["id"],
                "title": art["title"],
                "body": body,
                "pub_date": pub_date
            })
            print(f"  {'OK' if body else 'EMPTY'} {art['title'][:55]}")

        try: page.close()
        except: pass
        try: browser.disconnect()
        except: pass
except Exception as e:
    print(f"eco_fetch_sub error: {e}", file=sys.stderr)
finally:
    chrome_proc.terminate()

with open(OUT_PATH, 'w') as f:
    json.dump(results, f)

print(f"eco_fetch_sub: {len(results)} results")
