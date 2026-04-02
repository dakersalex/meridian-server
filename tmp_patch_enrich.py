with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    src = f.read()

# The problem: enrich_article_with_ai replaces body with fullSummary
# Fix: keep raw body text, only update summary/tags/topic/pub_date
OLD = '''        art["summary"]  = parsed.get("summary", art.get("summary",""))
        art["body"]     = parsed.get("fullSummary", art.get("body",""))
        art["tags"]     = json.dumps(parsed.get("tags", []))
        art["topic"]    = parsed.get("topic", art.get("topic",""))
        # Only use Claude's pub_date if we don't already have one from URL extraction
        if not art.get("pub_date"):
            art["pub_date"] = parsed.get("pub_date", "")
        art["status"]   = "full_text"'''

NEW = '''        art["summary"]  = parsed.get("summary", art.get("summary",""))
        # Do NOT overwrite body with fullSummary — preserve raw scraped text as body
        # fullSummary is stored only if body is currently empty
        if not art.get("body") or len(art.get("body","")) < 200:
            art["body"] = parsed.get("fullSummary", art.get("body",""))
        art["tags"]     = json.dumps(parsed.get("tags", []))
        art["topic"]    = parsed.get("topic", art.get("topic",""))
        # Only use Claude's pub_date if we don't already have one from URL extraction
        if not art.get("pub_date"):
            art["pub_date"] = parsed.get("pub_date", "")
        art["status"]   = "full_text"'''

if OLD in src:
    src = src.replace(OLD, NEW)
    print("enrich_article_with_ai fix: OK")
else:
    print("enrich_article_with_ai fix: FAILED")

with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(src)
