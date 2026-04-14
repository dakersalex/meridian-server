from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from pathlib import Path

BASE = "https://www.foreignaffairs.com"
profile_dir = Path("/Users/alexdakers/meridian-server/fa_profile")

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        str(profile_dir), headless=True,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
    )
    page = browser.new_page()

    # --- SAVED ARTICLES ---
    print("=== SAVED ARTICLES — raw HTML sample ===")
    page.goto(BASE + "/my-foreign-affairs/saved-articles", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(4000)
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(2000)
    soup = BeautifulSoup(page.content(), "html.parser")

    # Try common article card selectors
    for sel in ["article", "[class*='article']", "[class*='card']", "[class*='teaser']", "[class*='listing']", "h2 a", "h3 a"]:
        els = soup.select(sel)
        if els:
            print(f"  selector '{sel}': {len(els)} hits")
            # Show first hit's text + href
            first = els[0]
            href = first.get("href","") if first.name == "a" else (first.find("a") or {}).get("href","")
            text = first.get_text(strip=True)[:80]
            print(f"    first: href={href} text={text[:60]}")

    print()

    # --- MOST READ ---
    print("=== MOST READ — raw HTML sample ===")
    page.goto(BASE + "/most-read", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)
    soup2 = BeautifulSoup(page.content(), "html.parser")

    for sel in ["article", "[class*='article']", "[class*='card']", "[class*='teaser']", "[class*='listing']", "h2 a", "h3 a"]:
        els = soup2.select(sel)
        if els:
            print(f"  selector '{sel}': {len(els)} hits")
            first = els[0]
            href = first.get("href","") if first.name == "a" else (first.find("a") or {}).get("href","")
            text = first.get_text(strip=True)[:80]
            print(f"    first: href={href} text={text[:60]}")

    print()

    # --- ISSUE PAGE ---
    print("=== ISSUE 105/2 — raw HTML sample ===")
    page.goto(BASE + "/issues/2026/105/2", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)
    soup3 = BeautifulSoup(page.content(), "html.parser")

    for sel in ["article", "[class*='article']", "[class*='card']", "[class*='teaser']", "[class*='listing']", "h2 a", "h3 a"]:
        els = soup3.select(sel)
        if els:
            print(f"  selector '{sel}': {len(els)} hits")
            first = els[0]
            href = first.get("href","") if first.name == "a" else (first.find("a") or {}).get("href","")
            text = first.get_text(strip=True)[:80]
            print(f"    first: href={href} text={text[:60]}")

    browser.close()
