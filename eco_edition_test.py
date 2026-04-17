#!/usr/bin/env python3
"""
Test: can eco_chrome_profile access the weekly edition page and see full article list?
Checks for paywalled content vs full access.
"""
import sys, json, subprocess, time, re
from pathlib import Path
from playwright.sync_api import sync_playwright

PROFILE = str(Path("/Users/alexdakers/meridian-server/eco_chrome_profile"))
PORT = 9224
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
OUT = "/Users/alexdakers/meridian-server/logs/eco_edition_test.json"

# Use the latest known edition
URLS_TO_TEST = [
    "https://www.economist.com/weeklyedition/archive",
    "https://www.economist.com/weeklyedition/2026-04-18",
]

lock = Path(PROFILE) / "SingletonLock"
if lock.exists():
    lock.unlink()

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

        for url in URLS_TO_TEST:
            page = context.new_page()
            print(f"\nTesting: {url}", file=sys.stderr)
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)

            final_url = page.url
            title = page.title()
            print(f"  Final URL: {final_url}", file=sys.stderr)
            print(f"  Title: {title}", file=sys.stderr)

            blocked = any(x in final_url for x in ["login", "myaccount", "register"])
            cf_blocked = "moment" in title.lower() or "just a moment" in title.lower()

            # Get full page text to check for paywall indicators
            page_text = page.evaluate("() => document.body.innerText")
            has_paywall = any(x in page_text.lower() for x in [
                "subscribe to continue", "subscribe now", "sign in to read",
                "already a subscriber", "get full access", "paywall"
            ])

            # Extract all article links
            articles = page.evaluate("""() => {
                const results = [];
                const seen = new Set();
                document.querySelectorAll('a[href]').forEach(a => {
                    const href = a.href || '';
                    // Match article URLs with year/month/day pattern
                    if (!/\\/20[0-9]{2}\\/[0-9]{2}\\/[0-9]{2}\\//.test(href)) return;
                    if (href.includes('/weeklyedition') || href.includes('/for-you')) return;
                    const url = href.split('?')[0];
                    const text = a.innerText.trim();
                    if (text.length > 15 && !seen.has(url)) {
                        seen.add(url);
                        // Walk up to find standfirst
                        let el = a.parentElement;
                        let standfirst = '';
                        for (let i = 0; i < 6; i++) {
                            if (!el) break;
                            const ps = el.querySelectorAll('p');
                            for (const p of ps) {
                                const t = p.innerText.trim();
                                if (t.length > 20 && t.length < 300 && t !== text) {
                                    standfirst = t;
                                    break;
                                }
                            }
                            if (standfirst) break;
                            el = el.parentElement;
                        }
                        results.push({title: text, url, standfirst: standfirst.slice(0, 150)});
                    }
                });
                return results;
            }""")

            # Also check for edition links on archive page
            edition_links = []
            if "archive" in url:
                edition_links = page.evaluate("""() => {
                    const links = [];
                    document.querySelectorAll('a[href*="/weeklyedition/20"]').forEach(a => {
                        const href = a.href.split('?')[0];
                        if (!links.includes(href)) links.push(href);
                    });
                    return links.slice(0, 6);
                }""")

            print(f"  Blocked: {blocked}, CF: {cf_blocked}, Paywall: {has_paywall}", file=sys.stderr)
            print(f"  Articles found: {len(articles)}", file=sys.stderr)
            for a in articles[:5]:
                print(f"    - {a['title'][:60]}", file=sys.stderr)
                if a.get('standfirst'):
                    print(f"      standfirst: {a['standfirst'][:80]}", file=sys.stderr)

            results[url] = {
                "blocked": blocked or cf_blocked,
                "has_paywall_text": has_paywall,
                "article_count": len(articles),
                "articles_sample": articles[:8],
                "edition_links": edition_links,
                "final_url": final_url,
                "title": title,
            }
            page.close()

        browser.close()

except Exception as e:
    error = str(e)
    print(f"ERROR: {e}", file=sys.stderr)
finally:
    chrome.terminate()

with open(OUT, 'w') as f:
    json.dump({"results": results, "error": error}, f, indent=2)
print("\nDone", file=sys.stderr)
