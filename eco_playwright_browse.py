"""
Create fresh eco_playwright_profile for Economist feed scraping.
Opens a visible browser — browse normally to build legitimate history.
Run this script whenever you want to open the Economist in this profile.
Once Cloudflare stops blocking (usually 2-3 days of normal use), the
AI pick scraper will use this profile headlessly with --window-position=-3000,-3000.
"""
from playwright.sync_api import sync_playwright
import os, time

BASE = '/Users/alexdakers/meridian-server'
PROFILE = os.path.join(BASE, 'eco_playwright_profile')

print(f"Opening Economist in eco_playwright_profile...")
print(f"Profile: {PROFILE}")
print("Browse normally — read some articles, scroll around.")
print("Close the window when done.")

with sync_playwright() as pw:
    browser = pw.chromium.launch_persistent_context(
        PROFILE,
        headless=False,
        args=["--no-sandbox", "--window-size=1280,900"]
    )
    page = browser.new_page()
    page.goto("https://www.economist.com",
              wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2000)
    print(f"Page: {page.title()}")
    print("Window open — browse freely. Close the window when done.")

    # Keep running until the browser window is closed
    try:
        page.wait_for_event("close", timeout=0)
    except:
        pass

    browser.close()

print("Session saved. Run this script again to continue building history.")
