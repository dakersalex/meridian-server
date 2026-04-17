#!/usr/bin/env python3
"""
Test: launch_persistent_context with REAL Chrome binary (not Playwright's bundled Chromium)
Same approach as FT but using the system Chrome to avoid profile compatibility issues.
"""
import sys, json, re
from pathlib import Path
from playwright.sync_api import sync_playwright

CDP_PROFILE = Path("/Users/alexdakers/meridian-server/eco_chrome_profile")
CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
OUT = "/Users/alexdakers/meridian-server/logs/eco_test_result.json"
BOOKMARKS_URL = "https://www.economist.com/for-you/bookmarks"

lock = CDP_PROFILE / "SingletonLock"
if lock.exists():
    lock.unlink()
    print("Removed lock file", file=sys.stderr)

result = {"success": False, "url": "", "title": "", "article_count": 0,
          "blocked": False, "articles_sample": [], "error": None}

try:
    with sync_playwright() as pw:
        print("Launching with real Chrome binary...", file=sys.stderr)
        browser = pw.chromium.launch_persistent_context(
            str(CDP_PROFILE),
            executable_path=CHROME_BIN,
            headless=False,
            args=[
                "--no-sandbox",
                "--window-position=-3000,-3000",
                "--window-size=1280,900",
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-default-apps",
            ]
        )
        page = browser.new_page()
        print("Navigating...", file=sys.stderr)
        page.goto(BOOKMARKS_URL, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(5000)

        final_url = page.url
        page_title = page.title()
        print(f"URL: {final_url}", file=sys.stderr)
        print(f"Title: {page_title}", file=sys.stderr)

        blocked = any(x in final_url for x in ["challenge", "login", "myaccount", "cloudflare"])
        blocked = blocked or "Just a moment" in page_title or "Sign in" in page_title

        result["url"] = final_url
        result["title"] = page_title
        result["blocked"] = blocked

        if not blocked:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(page.content(), "html.parser")
            links = soup.select("a[href*='/20']")
            articles = []
            seen = set()
            for a in links:
                href = a.get("href", "")
                if not re.search(r'/\d{4}/\d{2}/\d{2}/', href):
                    continue
                url = ("https://www.economist.com" + href if href.startswith("/") else href).split("?")[0]
                if url in seen: continue
                seen.add(url)
                title = a.get_text(strip=True)
                if len(title) > 15:
                    articles.append({"url": url, "title": title[:80]})

            result["article_count"] = len(articles)
            result["articles_sample"] = articles[:5]
            result["success"] = len(articles) > 0
            print(f"Articles found: {len(articles)}", file=sys.stderr)
        else:
            print("BLOCKED / redirected", file=sys.stderr)

        try: browser.close()
        except: pass

except Exception as e:
    result["error"] = str(e)
    print(f"ERROR: {e}", file=sys.stderr)

with open(OUT, 'w') as f:
    json.dump(result, f, indent=2)

print(f"Done: success={result['success']} blocked={result['blocked']} articles={result['article_count']}", file=sys.stderr)
