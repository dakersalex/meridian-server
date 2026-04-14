from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from pathlib import Path

BASE = "https://www.foreignaffairs.com"
profile_dir = Path("/Users/alexdakers/meridian-server/fa_profile")

results = []

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        str(profile_dir), headless=True,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
    )
    page = browser.new_page()
    page.goto(BASE + "/issues/2026/105/2", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)

    soup = BeautifulSoup(page.content(), "html.parser")
    hrefs = set()
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if href.startswith("/") and len(href) > 5:
            parts = [p for p in href.split("?")[0].split("/") if p]
            hrefs.add((len(parts), href[:80]))

    browser.close()

# Show unique href patterns by segment count
from collections import Counter
counts = Counter(n for n, h in hrefs)
print("Segment count distribution:", dict(sorted(counts.items())))
print()
# Show sample hrefs for each segment count
by_len = {}
for n, h in hrefs:
    by_len.setdefault(n, []).append(h)
for n in sorted(by_len):
    print(f"=== {n} segments ===")
    for h in list(by_len[n])[:5]:
        print(" ", h)
