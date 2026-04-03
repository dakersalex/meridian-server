import sqlite3

conn = sqlite3.connect('/Users/alexdakers/meridian-server/meridian.db')

rows = conn.execute("""
    SELECT title, url, LENGTH(body) as blen, status, body
    FROM articles WHERE source='Financial Times'
    ORDER BY blen ASC
""").fetchall()

total = len(rows)
short = [r for r in rows if r[2] < 3000]
good  = [r for r in rows if r[2] >= 3000]

ai_prefixes = ('the article','this article','the ft','examines','argues','discusses','explores','the author','the piece','this piece','critiques','analyzes','assesses')
ai_summary = [r for r in short if r[4] and r[4].strip().lower()[:30].startswith(ai_prefixes)]
no_body    = [r for r in short if not r[4] or r[2] == 0]
real_short = [r for r in short if r not in ai_summary and r not in no_body]

avg_short = int(sum(r[2] for r in short)/len(short)) if short else 0

with open('/Users/alexdakers/meridian-server/tmp_status.txt', 'w') as f:
    f.write(f"FT BODY LENGTH BREAKDOWN ({total} articles)\n")
    f.write(f"  Short (<3k): {len(short)}  Good (>=3k): {len(good)}\n")
    f.write(f"  Avg short bodies: {avg_short:,} chars\n\n")
    f.write(f"SHORT BREAKDOWN:\n")
    f.write(f"  AI summaries (detectable): {len(ai_summary)}\n")
    f.write(f"  Empty/no body:             {len(no_body)}\n")
    f.write(f"  Possibly real/short:       {len(real_short)}\n\n")

    f.write("AI SUMMARY ARTICLES:\n")
    for t, u, b, s, body in ai_summary:
        f.write(f"  {b:5,}ch  {t[:70]}\n")
        f.write(f"          [{(body or '')[:90]}]\n")

    f.write("\nEMPTY BODY:\n")
    for t, u, b, s, body in no_body:
        f.write(f"  {b:5,}ch  [{s}] {'URL:'+u[:40] if u else 'NO URL'}  {t[:55]}\n")

    f.write("\nREAL/SHORT (may be paywalled or genuinely short):\n")
    for t, u, b, s, body in real_short:
        f.write(f"  {b:5,}ch  {t[:70]}\n")
        f.write(f"          [{(body or '')[:90]}]\n")

conn.close()
print("DONE")
