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

    # 1. Check saved articles page — are we logged in? What do we see?
    print("=== SAVED ARTICLES PAGE ===")
    page.goto(BASE + "/my-foreign-affairs/saved-articles", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)
    print("URL after nav:", page.url)
    soup = BeautifulSoup(page.content(), "html.parser")
    links = [a.get("href","") for a in soup.select("a[href]") if "/my-foreign-affairs" not in a.get("href","") and a.get("href","").startswith("/")]
    article_links = [l for l in links if len([p for p in l.split("/") if p]) == 2]
    print(f"Article-shaped links found: {len(article_links)}")
    for l in article_links[:8]:
        print(" ", l)

    # 2. Check current issue page
    print("\n=== CURRENT ISSUE (most-recent) ===")
    page.goto(BASE + "/issues", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2000)
    soup2 = BeautifulSoup(page.content(), "html.parser")
    # Find issue links
    issue_links = [a.get("href","") for a in soup2.select("a[href]") if "/issues/20" in a.get("href","")]
    print("Issue links found:", issue_links[:10])

    # 3. Check most-read page
    print("\n=== MOST READ PAGE ===")
    page.goto(BASE + "/most-read", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2000)
    soup3 = BeautifulSoup(page.content(), "html.parser")
    mr_links = [a.get("href","") for a in soup3.select("a[href]") if a.get("href","").startswith("/") and len([p for p in a.get("href","").split("/") if p]) == 2]
    print(f"Article-shaped links: {len(mr_links)}")
    for l in mr_links[:8]:
        print(" ", l)

    browser.close()
