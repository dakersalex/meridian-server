#!/usr/bin/env python3
"""
eco_weekly_sub.py — Economist weekly edition scraper subprocess.
Fetches archive page to find 2 most recent editions, then scrapes all articles
from each edition page (title + standfirst). No prior-save filtering — scores ALL.

Args: <profile_dir> <output_json>
"""
import sys, json, subprocess, time, os, re
from playwright.sync_api import sync_playwright

PROFILE = sys.argv[1]
OUT     = sys.argv[2]
PORT    = 9224
CHROME  = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
ARCHIVE = "https://www.economist.com/weeklyedition/archive"

JUNK_URL = ('/podcasts/', '/newsletters/', '/events/', '/films/', '/interactive/',
            '/weeklyedition', '/for-you', '/the-world-this-week', '/graphic-detail/2')
JUNK_TITLES = ('The world this week', 'The weekly cartoon', "KAL's cartoon",
               'This week', 'Letters to', 'A selection of correspondence',
               'The Economist', 'Weekly edition')

lock = os.path.join(PROFILE, 'SingletonLock')
if os.path.exists(lock):
    os.remove(lock)
    print("Removed lock", file=sys.stderr)

all_articles = {}  # url -> article dict
edition_urls = []
error = None

chrome = subprocess.Popen([
    CHROME,
    f"--remote-debugging-port={PORT}",
    f"--user-data-dir={PROFILE}",
    "--no-first-run", "--no-default-browser-check",
    "--window-position=-3000,-3000", "--window-size=1280,900",
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(5)

def scrape_edition(page, edition_url):
    m = re.search(r'weeklyedition/([0-9-]+)', edition_url)
    edition_str = m.group(1) if m else '?'
    arts = {}

    items = page.evaluate("""() => {
        const results = [];
        const seen = new Set();
        document.querySelectorAll('a[href]').forEach(a => {
            const href = a.href || '';
            if (!/\\/20[0-9]{2}\\/[0-9]{2}\\/[0-9]{2}\\//.test(href)) return;
            const url = href.split('?')[0];
            const text = a.innerText.trim();
            if (text.length < 10 || seen.has(url)) return;
            seen.add(url);
            let el = a.parentElement;
            let sf = '';
            for (let i = 0; i < 8; i++) {
                if (!el) break;
                const ps = el.querySelectorAll('p');
                for (const p of ps) {
                    const t = p.innerText.trim();
                    if (t.length > 20 && t.length < 300 && t !== text) { sf = t; break; }
                }
                if (sf) break;
                el = el.parentElement;
            }
            results.push({title: text, url, standfirst: sf.slice(0, 200)});
        });
        return results;
    }""")

    for item in items:
        url   = item['url']
        title = item['title']
        # Skip junk URLs
        if any(j in url for j in JUNK_URL):
            continue
        # Skip junk titles
        if any(title.startswith(t) for t in JUNK_TITLES):
            continue
        if len(title) < 15:
            continue
        arts[url] = {
            'title': title,
            'url': url,
            'standfirst': item.get('standfirst', ''),
            'edition': edition_str
        }

    print(f"Edition {edition_str}: {len(arts)} articles", file=sys.stderr)
    return arts

try:
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(f"http://localhost:{PORT}")
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()

        # 1. Archive page → get 2 most recent edition URLs
        page = ctx.new_page()
        print("Loading archive...", file=sys.stderr)
        page.goto(ARCHIVE, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(4000)

        edition_urls = page.evaluate("""() => {
            const links = [];
            document.querySelectorAll('a[href*="/weeklyedition/20"]').forEach(a => {
                const href = a.href.split('?')[0];
                if (!links.includes(href)) links.push(href);
            });
            return links.slice(0, 1);
        }""")
        page.close()
        print(f"Edition URLs: {edition_urls}", file=sys.stderr)

        if not edition_urls:
            error = "No edition URLs found on archive page"
        else:
            # 2. Scrape each edition
            for eurl in edition_urls:
                page = ctx.new_page()
                print(f"Loading edition: {eurl}", file=sys.stderr)
                page.goto(eurl, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(5000)

                final_url = page.url
                if 'login' in final_url or 'myaccount' in final_url:
                    print(f"Blocked on {eurl}", file=sys.stderr)
                    page.close()
                    continue

                arts = scrape_edition(page, eurl)
                all_articles.update(arts)
                page.close()

        browser.close()

except Exception as e:
    error = str(e)
    print(f"ERROR: {e}", file=sys.stderr)
finally:
    chrome.terminate()

articles_list = list(all_articles.values())
print(f"Total: {len(articles_list)} unique articles from {len(edition_urls)} editions", file=sys.stderr)

with open(OUT, 'w') as f:
    json.dump({
        "articles": articles_list,
        "edition_urls": edition_urls,
        "error": error
    }, f)
