#!/usr/bin/env python3
"""Diagnose the Economist bookmarks page HTML structure to fix title extraction."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from server import BASE_DIR, log
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

SAVED_URL = "https://www.economist.com/for-you/bookmarks"

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        str(BASE_DIR / "economist_profile"),
        headless=False,
        args=["--disable-blink-features=AutomationControlled"]
    )
    page = browser.new_page()
    print("Loading bookmarks page...")
    page.goto(SAVED_URL, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(4000)
    print(f"URL: {page.url}")

    soup = BeautifulSoup(page.content(), "html.parser")

    # Find all links with date patterns
    import re
    links = []
    for a in soup.select("a[href*='/20']"):
        href = a.get("href", "")
        if not re.search(r'/\d{4}/\d{2}/\d{2}/', href):
            continue
        url = ("https://www.economist.com" + href if href.startswith("/") else href).split("?")[0]

        # Print the anchor's own text AND surrounding context
        anchor_text = a.get_text(strip=True)

        # Try: look for a sibling or nearby element with the actual headline
        # Print the parent chain HTML snippet for diagnosis
        parent = a.parent
        snippet = str(parent)[:300] if parent else ""

        print(f"\nURL: {url}")
        print(f"  anchor_text: {anchor_text[:80]}")
        print(f"  parent snippet: {snippet[:200]}")

        if len(links) >= 5:
            break
        links.append(url)

    browser.close()
