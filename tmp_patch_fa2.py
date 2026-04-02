with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    src = f.read()

OLD = '''        paragraphs = (
            soup.select("div.article__body-content p") or
            soup.select("div.article__body p") or
            soup.select("div.article-body p") or
            soup.select("main p")
        )'''

NEW = '''        paragraphs = (
            soup.select("div.article__body-content p") or
            soup.select("section.rich-text p") or
            soup.select("div.article__body p") or
            soup.select("div.article-body p") or
            soup.select("main p")
        )'''

if OLD in src:
    src = src.replace(OLD, NEW)
    print("selector patch: OK")
else:
    print("selector patch: FAILED")

with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(src)
