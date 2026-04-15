from playwright.sync_api import sync_playwright
from pathlib import Path

profile_dir = Path("/Users/alexdakers/meridian-server/eco_playwright_profile")
print(f"Profile exists: {profile_dir.exists()}")

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        str(profile_dir), headless=True,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
    )
    page = browser.new_page()

    for url in ["https://www.economist.com/for-you/feed", "https://www.economist.com/for-you/topics"]:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(4000)
        final_url = page.url
        title = page.title()
        blocked = "cloudflare" in title.lower() or "just a moment" in title.lower() or "403" in title or "access denied" in title.lower()
        content_len = len(page.content())
        print(f"\n{url}")
        print(f"  Final URL: {final_url}")
        print(f"  Title: {title[:60]}")
        print(f"  Blocked: {blocked}")
        print(f"  Content length: {content_len}")

    browser.close()
