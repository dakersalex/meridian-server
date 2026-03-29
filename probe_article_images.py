#!/usr/bin/env python3
"""
Probe real FT/Economist articles to capture actual images/charts
so we can see what the image extraction pipeline would produce.
Saves screenshots of all figure elements to /tmp/probe_images/
"""
import sys, os, re, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from server import BASE_DIR
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path('/tmp/probe_images')
OUTPUT_DIR.mkdir(exist_ok=True)

TEST_ARTICLES = [
    ("The Economist", "https://www.economist.com/finance-and-economics/2024/10/24/investors-should-not-fear-a-stockmarket-crash"),
    ("The Economist", "https://www.economist.com/business/2024/12/08/from-apple-to-starbucks-western-firms-china-dreams-are-dying"),
]

def probe(profile_dir, url, source, label):
    print(f"\n{'='*60}")
    print(f"{source}: {url[-60:]}")
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            str(profile_dir), headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = browser.new_page()
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(4000)

        # Find all figure elements with images inside
        figures = page.locator("figure").all()
        print(f"Found {len(figures)} <figure> elements")

        saved = []
        for i, fig in enumerate(figures):
            try:
                # Check size — skip tiny ones (icons, thumbnails)
                box = fig.bounding_box()
                if not box or box['width'] < 200 or box['height'] < 100:
                    print(f"  Fig {i+1}: too small ({box}), skipping")
                    continue

                # Check if it has a figcaption (suggests it's a proper graphic)
                caption = ""
                try:
                    cap_el = fig.locator("figcaption").first
                    caption = cap_el.text_content() or ""
                    caption = caption.strip()[:80]
                except:
                    pass

                # Screenshot the figure
                path = OUTPUT_DIR / f"{label}_fig{i+1}.png"
                fig.screenshot(path=str(path))
                saved.append({"index": i+1, "width": int(box['width']), "height": int(box['height']), "caption": caption, "path": str(path)})
                print(f"  Fig {i+1}: {int(box['width'])}x{int(box['height'])}px — caption: '{caption[:60]}'")
            except Exception as e:
                print(f"  Fig {i+1}: error — {e}")

        # Also check for standalone SVGs (Economist uses these for charts)
        svgs = page.locator("svg").all()
        large_svgs = []
        for i, svg in enumerate(svgs):
            try:
                box = svg.bounding_box()
                if box and box['width'] > 250 and box['height'] > 150:
                    large_svgs.append(box)
                    path = OUTPUT_DIR / f"{label}_svg{i+1}.png"
                    svg.screenshot(path=str(path))
                    print(f"  SVG {i+1}: {int(box['width'])}x{int(box['height'])}px — saved")
            except:
                pass

        print(f"Saved {len(saved)} figures, {len(large_svgs)} SVGs to {OUTPUT_DIR}")
        browser.close()
        return saved

# Test Economist
eco_profile = BASE_DIR / "economist_profile"
if eco_profile.exists():
    for i, (src, url) in enumerate(TEST_ARTICLES):
        probe(eco_profile, url, src, f"eco_{i+1}")
else:
    print("No economist_profile found")

print("\nDone — check /tmp/probe_images/ for captured images")
