with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    src = f.read()

OLD = '''def fetch_fa_article_text(page, url):
    """Fetch full text and pub_date of a Foreign Affairs article using logged-in browser page."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
        page.wait_for_timeout(3000)
        soup = BeautifulSoup(page.content(), "html.parser")
        # FA selectors — try multiple patterns
        paragraphs = (
            soup.select("div.article-body p") or
            soup.select("div[class*='body'] p") or
            soup.select("div[class*='article'] p") or
            soup.select("main p")
        )
        text = " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40)
        # pub_date from meta tag — normalise to YYYY-MM-DD for consistent JS parsing
        pub_date = ""
        meta = soup.select_one("meta[property='article:published_time'], meta[name='pubdate']")
        if meta and meta.get("content"):
            raw = meta["content"]
            # Extract just the date part from ISO strings like 2026-03-05T00:00:00-05:00
            m = re.match(r'(\\d{4}-\\d{2}-\\d{2})', raw)
            pub_date = m.group(1) if m else raw
        return text, pub_date
    except Exception as e:
        log.warning(f"FA fetch text error for {url}: {e}")
        return "", ""'''

NEW = '''def fetch_fa_article_text(page, url):
    """Fetch full text and pub_date of a Foreign Affairs article using logged-in browser page."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
        page.wait_for_timeout(3000)
        soup = BeautifulSoup(page.content(), "html.parser")
        # FA uses article__body-content (confirmed via Playwright inspection April 2026)
        paragraphs = (
            soup.select("div.article__body-content p") or
            soup.select("div.article__body p") or
            soup.select("div.article-body p") or
            soup.select("main p")
        )
        text = " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40)
        # pub_date from meta tag — normalise to YYYY-MM-DD for consistent JS parsing
        pub_date = ""
        meta = soup.select_one("meta[property='article:published_time'], meta[name='pubdate']")
        if meta and meta.get("content"):
            raw = meta["content"]
            # Extract just the date part from ISO strings like 2026-03-05T00:00:00-05:00
            m = re.match(r'(\\d{4}-\\d{2}-\\d{2})', raw)
            pub_date = m.group(1) if m else raw
        return text, pub_date
    except Exception as e:
        log.warning(f"FA fetch text error for {url}: {e}")
        return "", ""'''

if OLD in src:
    src = src.replace(OLD, NEW)
    print("FA selector patch: OK")
else:
    print("FA selector patch: FAILED — string not found")

with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(src)
