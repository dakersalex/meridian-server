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
    page.goto(BASE + "/my-foreign-affairs/saved-articles", wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(4000)
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(2000)

    print("Final URL:", page.url)
    soup = BeautifulSoup(page.content(), "html.parser")

    # Count h3 elements and their links
    h3s = soup.select("h3")
    print(f"h3 elements found: {len(h3s)}")
    for h3 in h3s[:10]:
        a = h3.find("a", href=True)
        print(f"  h3 text='{h3.get_text(strip=True)[:50]}' link={a.get('href','none')[:60] if a else 'no link'}")

    # Also check card selector
    cards = soup.select("[class*='card']")
    print(f"\nCard elements: {len(cards)}")
    for card in cards[:5]:
        a = card.find("a", href=True)
        h = card.find(["h2","h3","h4"])
        print(f"  title='{h.get_text(strip=True)[:50] if h else 'none'}' link={a.get('href','')[:60] if a else 'none'}")

    browser.close()
