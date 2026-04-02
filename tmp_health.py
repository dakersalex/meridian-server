import sqlite3

conn = sqlite3.connect('/Users/alexdakers/meridian-server/meridian.db')

sources = ['Financial Times', 'The Economist', 'Foreign Affairs']

with open('/Users/alexdakers/meridian-server/tmp_health.txt', 'w') as f:
    for source in sources:
        rows = conn.execute(
            "SELECT LENGTH(body), LENGTH(summary), status FROM articles WHERE source=?", (source,)
        ).fetchall()

        total = len(rows)
        if not total:
            f.write(f"\n{source}: no articles\n")
            continue

        big    = sum(1 for b,_,_ in rows if b >= 8000)
        med    = sum(1 for b,_,_ in rows if 3000 <= b < 8000)
        short  = sum(1 for b,_,_ in rows if 500 <= b < 3000)
        empty  = sum(1 for b,_,_ in rows if b < 500)
        avg_b  = int(sum(b for b,_,_ in rows) / total)
        avg_s  = int(sum(s for _,s,_ in rows) / total)
        mx     = max(b for b,_,_ in rows)
        mn     = min(b for b,_,_ in rows)
        by_status = {}
        for b, s, st in rows:
            by_status[st] = by_status.get(st, 0) + 1

        f.write(f"\n{'='*55}\n")
        f.write(f"  {source}\n")
        f.write(f"{'='*55}\n")
        f.write(f"  Total:              {total}\n")
        f.write(f"  Full  (>=8k chars): {big}  ({round(big/total*100)}%)\n")
        f.write(f"  Med   (3-8k chars): {med}  ({round(med/total*100)}%)\n")
        f.write(f"  Short (0.5-3k):     {short}  ({round(short/total*100)}%)\n")
        f.write(f"  Empty (<500 chars): {empty}  ({round(empty/total*100)}%)\n")
        f.write(f"  Avg body:           {avg_b:,} chars\n")
        f.write(f"  Avg summary:        {avg_s:,} chars\n")
        f.write(f"  Body range:         {mn:,} – {mx:,} chars\n")
        f.write(f"  By status: {by_status}\n")

        # Worst 8 — lowest body length
        worst = conn.execute(
            "SELECT title, LENGTH(body), status FROM articles WHERE source=? ORDER BY LENGTH(body) ASC LIMIT 8",
            (source,)
        ).fetchall()
        f.write(f"\n  Shortest bodies:\n")
        for title, blen, st in worst:
            f.write(f"    {blen:6,}  [{st}]  {title[:60]}\n")

print("DONE")
