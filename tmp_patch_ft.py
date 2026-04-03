with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    src = f.read()

OLD = '''        # FT article body selectors
        body_el = soup.select_one("div.article__content, div[class*='article-body'], div[class*='body-text']")
        text = ""
        if body_el:
            paragraphs = body_el.find_all("p")
            text = " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30)'''

NEW = '''        # FT article body selectors — updated for FT's current markup (o3/n-content classes)
        paragraphs = (
            soup.select("div.n-content-body p") or
            soup.select("div[class*='n-content-body'] p") or
            soup.select("div[class*='article__content'] p") or
            soup.select("div[class*='article-body'] p") or
            soup.select("div[class*='body-text'] p")
        )
        text = " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30)'''

if OLD in src:
    src = src.replace(OLD, NEW)
    print("FT selector patch: OK")
else:
    print("FT selector patch: FAILED")
    # Show context
    idx = src.find("FT article body selectors")
    print(repr(src[idx:idx+300]))

with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(src)
