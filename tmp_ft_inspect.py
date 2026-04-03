from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# Test the ft_profile session state
with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        '/Users/alexdakers/meridian-server/ft_profile',
        headless=False,  # visible so we can see what's happening
        args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
    )
    page = browser.new_page()
    
    # Try the saved articles page first to warm up session
    print("Loading FT saved articles page...")
    page.goto('https://www.ft.com/myft/saved-articles', wait_until='domcontentloaded', timeout=25000)
    page.wait_for_timeout(4000)
    print(f"Saved page title: {page.title()}")
    print(f"URL: {page.url}")
    
    # Now try an article
    test_url = 'https://www.ft.com/content/d2c3ea11-a462-47ea-aed4-825e9ba55d87'
    print(f"\nLoading article...")
    page.goto(test_url, wait_until='domcontentloaded', timeout=25000)
    page.wait_for_timeout(3000)
    print(f"Article title: {page.title()[:60]}")
    print(f"URL: {page.url[:70]}")
    
    soup = BeautifulSoup(page.content(), 'html.parser')
    all_p = [p for p in soup.select('p') if len(p.get_text(strip=True)) > 60]
    print(f"Substantial paragraphs: {len(all_p)}")
    
    if all_p:
        parents = {}
        for p in all_p:
            key = ' '.join(p.parent.get('class', []))[:50] or p.parent.name
            parents[key] = parents.get(key, 0) + 1
        for k, v in sorted(parents.items(), key=lambda x: -x[1])[:5]:
            print(f"  {v}x  {k}")
        print(f"First: {all_p[0].get_text(strip=True)[:120]}")
    
    browser.close()
