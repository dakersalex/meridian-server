"""
One-time setup: create eco_feed_profile for Economist AI pick feed scraping.
Opens a visible browser window — you have 90 seconds to log in.
"""
from playwright.sync_api import sync_playwright
import os, time

BASE = '/Users/alexdakers/meridian-server'
PROFILE = os.path.join(BASE, 'eco_feed_profile')

print("Opening browser — you have 90 seconds to log in to The Economist.")
print("The browser will close automatically once done.")

with sync_playwright() as pw:
    browser = pw.chromium.launch_persistent_context(
        PROFILE,
        headless=False,
        args=["--no-sandbox", "--window-size=1280,900"]
    )
    page = browser.new_page()
    page.goto("https://www.economist.com/for-you/topics",
              wait_until="domcontentloaded", timeout=30000)

    # Wait up to 90 seconds for the user to log in
    # Poll every 5s to check if we're past the login page
    for i in range(18):
        title = page.title()
        url = page.url
        print(f"  [{i*5}s] {title[:60]} | {url[:60]}")
        if "login" not in url.lower() and "myaccount" not in url.lower():
            print("  Logged in successfully!")
            break
        time.sleep(5)

    # Visit both feed pages to cache sessions
    print("Visiting for-you/topics...")
    page.goto("https://www.economist.com/for-you/topics",
              wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2000)
    print(f"  Topics title: {page.title()[:60]}")

    print("Visiting for-you/feed...")
    page.goto("https://www.economist.com/for-you/feed",
              wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2000)
    print(f"  Feed title: {page.title()[:60]}")

    browser.close()

print(f"\nProfile saved to {PROFILE}")
print("Done.")
