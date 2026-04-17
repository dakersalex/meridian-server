#!/usr/bin/env python3
"""
Test scraping all 3 Economist sources via CDP:
1. /for-you/topics
2. /for-you/feed  
3. /weeklyedition/archive (to find latest edition URL)
"""
import sys, json, subprocess, time, re
from pathlib import Path
from playwright.sync_api import sync_playwright

PROFILE = str(Path("/Users/alexdakers/meridian-server/eco_chrome_profile"))
PORT = 9224
OUT = "/Users/alexdakers/meridian-server/logs/eco_sources_test.json"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

lock = Path(PROFILE) / "SingletonLock"
if lock.exists():
    lock.unlink()

SOURCES = [
    "https://www.economist.com/for-you/topics",
    "https://www.economist.com/for-you/feed",
    "https://www.economist.com/weeklyedition/archive",
]

results = {}
error = None

chrome = subprocess.Popen([
    CHROME,
    f"--remote-debugging-port={PORT}",
    f"--user-data-dir={PROFILE}",
    "--no-first-run", "--no-default-browser-check",
    "--window-position=-3000,-3000", "--window-size=1280,900",
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(5)

try:
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(f"http://localhost:{PORT}")
        context = browser.contexts[0] if browser.contexts else browser.new_context()

        for url in SOURCES:
            page = context.new_page()
            print(f"Visiting {url}...", file=sys.stderr)
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(4000)

            final_url = page.url
            title = page.title()
            blocked = any(x in final_url for x in ["login", "myaccount"]) or "moment" in title.lower()
            print(f"  -> {final_url} | blocked={blocked}", file=sys.stderr)

            if not blocked:
                articles = page.evaluate("""() => {
                    const results = [];
                    const seen = new Set();
                    // Match any year
                    document.querySelectorAll('a[href]').forEach(a => {
                        const href = a.href || '';
                        if (!/\\/20[0-9]{2}\\//.test(href)) return;
                        if (href.includes('/weeklyedition') || href.includes('/for-you')) return;
                        const url = href.split('?')[0];
                        const text = a.innerText.trim();
                        if (text.length > 15 && !seen.has(url)) {
                            seen.add(url);
                            results.push({title: text, url});
                        }
                    });
                    return results;
                }""")
                
                # For archive page, also find the latest edition link
                if "archive" in url:
                    edition_links = page.evaluate("""() => {
                        const links = [];
                        document.querySelectorAll('a[href*="/weeklyedition/20"]').forEach(a => {
                            links.push(a.href.split('?')[0]);
                        });
                        return links.slice(0, 5);
                    }""")
                    results[url] = {
                        "blocked": False,
                        "article_count": len(articles),
                        "articles_sample": articles[:3],
                        "edition_links": edition_links
                    }
                else:
                    results[url] = {
                        "blocked": False,
                        "article_count": len(articles),
                        "articles_sample": articles[:3],
                    }
                print(f"  -> {len(articles)} articles", file=sys.stderr)
            else:
                results[url] = {"blocked": True, "article_count": 0}

            page.close()

        browser.close()

except Exception as e:
    error = str(e)
    print(f"ERROR: {e}", file=sys.stderr)
finally:
    chrome.terminate()

with open(OUT, 'w') as f:
    json.dump({"results": results, "error": error}, f, indent=2)
print("Done", file=sys.stderr)
