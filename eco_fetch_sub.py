#!/usr/bin/env python3
"""
eco_fetch_sub.py — Fetch full text for Economist articles via CDP subprocess.
Uses real Chrome (not headless) with off-screen window position.
--headless=new breaks Economist JS rendering so we avoid it.

Args: <cdp_profile_dir> <cdp_port> <input_json> <output_json>
Input:  [{"id":..., "url":..., "title":...}]
Output: [{"id":..., "title":..., "body":..., "pub_date":...}]
"""
import sys, json, time, subprocess, re
from pathlib import Path
from playwright.sync_api import sync_playwright

CDP_PROFILE = Path(sys.argv[1])
CDP_PORT    = int(sys.argv[2])
IN_PATH     = sys.argv[3]
OUT_PATH    = sys.argv[4]
CHROME_BIN  = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

with open(IN_PATH) as f:
    articles = json.load(f)

results = []
if not articles:
    with open(OUT_PATH, 'w') as f:
        json.dump(results, f)
    sys.exit(0)

lock = CDP_PROFILE / "SingletonLock"
if lock.exists():
    lock.unlink()

# Real Chrome, off-screen window — headless=new breaks Economist JS rendering
chrome_proc = subprocess.Popen([
    CHROME_BIN,
    "--remote-debugging-port=" + str(CDP_PORT),
    "--user-data-dir=" + str(CDP_PROFILE),
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-default-apps",
    "--window-position=-3000,-3000",
    "--window-size=1280,900",
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(5)

def extract_pub_date(url):
    m = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
    return (m.group(1) + "-" + m.group(2) + "-" + m.group(3)) if m else ""

def fetch_text(page, url):
    try:
        resp = page.goto(url, wait_until="domcontentloaded", timeout=30000)
        status = resp.status if resp else 0
        if status == 404:
            print("  404 " + url[-60:], file=sys.stderr)
            return "", extract_pub_date(url)

        # Wait for JS to render
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            page.wait_for_timeout(4000)

        pub_date = extract_pub_date(url)

        # Try selectors in order of specificity
        selectors = [
            '[data-component="paragraph"]',
            'div[itemprop="articleBody"] p',
            'div.article__body p',
            'section.article__body p',
            'div[class*="article-body"] p',
            'div[class*="body__"] p',
        ]
        for sel in selectors:
            els = page.query_selector_all(sel)
            if els:
                text = " ".join(
                    e.inner_text().strip() for e in els
                    if len(e.inner_text().strip()) > 30
                )
                if len(text) > 200:
                    print("  OK [" + sel[:30] + "] " + str(len(text)) + "c " + url[-50:], file=sys.stderr)
                    return text[:12000], pub_date

        # Broad fallback
        article_el = page.query_selector("article")
        if article_el:
            text = " ".join(
                l.strip() for l in article_el.inner_text().split('\n')
                if len(l.strip()) > 50
            )
            if len(text) > 200:
                print("  OK [article] " + str(len(text)) + "c " + url[-50:], file=sys.stderr)
                return text[:12000], pub_date

        title = page.title()
        if "Just a moment" in title:
            print("  CLOUDFLARE " + url[-60:], file=sys.stderr)
        else:
            print("  EMPTY (title=" + title[:40] + ") " + url[-50:], file=sys.stderr)
        return "", pub_date

    except Exception as e:
        print("  ERROR " + url[-60:] + ": " + str(e), file=sys.stderr)
        return "", extract_pub_date(url)

try:
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:" + str(CDP_PORT))
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()

        for art in articles:
            body, pub_date = fetch_text(page, art["url"])
            results.append({
                "id": art["id"],
                "title": art["title"],
                "body": body,
                "pub_date": pub_date,
            })

        try: page.close()
        except: pass
        try: browser.close()
        except: pass

except Exception as e:
    print("eco_fetch_sub fatal: " + str(e), file=sys.stderr)
finally:
    chrome_proc.terminate()

with open(OUT_PATH, 'w') as f:
    json.dump(results, f)

fetched = sum(1 for r in results if r.get("body"))
print("eco_fetch_sub: " + str(fetched) + "/" + str(len(results)) + " fetched", file=sys.stderr)
