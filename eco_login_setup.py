"""
One-time Economist login helper.
Opens your real Chrome with the eco_chrome_profile, navigates to the
Economist login page, and waits for you to log in manually.
Once you're logged in and can see your bookmarks, press Enter here
and the session will be saved for future scraper runs.
"""
import subprocess, time, sys
from pathlib import Path

BASE_DIR = Path('/Users/alexdakers/meridian-server')
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
CDP_PORT = 9222
CDP_PROFILE = BASE_DIR / 'eco_chrome_profile'
CDP_PROFILE.mkdir(exist_ok=True)

print("=" * 55)
print("  Economist one-time login")
print("=" * 55)
print()
print("Opening Chrome with eco_chrome_profile...")
print("Please:")
print("  1. Log into The Economist with your credentials")
print("  2. Navigate to economist.com/for-you/bookmarks")
print("  3. Confirm you can see your saved articles")
print("  4. Come back here and press Enter")
print()

chrome_args = [
    CHROME,
    f'--remote-debugging-port={CDP_PORT}',
    f'--user-data-dir={CDP_PROFILE}',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-default-apps',
    'https://economist.com/for-you/bookmarks',
]

proc = subprocess.Popen(chrome_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)

input("Press Enter once you've logged in and can see your bookmarks... ")

print()
print("Verifying session...")

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    try:
        browser = p.chromium.connect_over_cdp(f'http://localhost:{CDP_PORT}')
        contexts = browser.contexts
        if not contexts:
            print("No browser contexts found — is Chrome still open?")
            sys.exit(1)
        page = contexts[0].pages[0] if contexts[0].pages else contexts[0].new_page()

        url = page.url
        title = page.title()
        content = page.content()

        cf_blocked = 'Just a moment' in title
        login_wall = 'login' in url.lower() or 'sign in' in title.lower()
        links = page.query_selector_all('a[href*="/202"]')
        article_count = len(links)

        print(f"  URL: {url[:80]}")
        print(f"  Title: {title}")
        print(f"  Cloudflare blocked: {cf_blocked}")
        print(f"  Login wall: {login_wall}")
        print(f"  Article links visible: {article_count}")

        if cf_blocked:
            print("\n❌ Still Cloudflare blocked — unexpected with real Chrome")
        elif login_wall:
            print("\n⚠️  Still showing login — please try logging in again")
        elif article_count > 0:
            print(f"\n✅ Session verified — {article_count} article links found")
            print("   eco_chrome_profile is ready for the scraper.")
        else:
            print("\n⚠️  Logged in but no articles visible — check the page manually")

    except Exception as e:
        print(f"Error connecting: {e}")

print()
input("Press Enter to close Chrome and finish... ")
proc.terminate()
print("Done. eco_chrome_profile session saved.")
