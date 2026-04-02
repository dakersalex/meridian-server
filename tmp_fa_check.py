import sqlite3

conn = sqlite3.connect('/Users/alexdakers/meridian-server/meridian.db')

rows = conn.execute("""
    SELECT title, LENGTH(body) as blen, status
    FROM articles WHERE source='Foreign Affairs'
    ORDER BY blen DESC
""").fetchall()

total = len(rows)
big = sum(1 for _, b, _ in rows if b >= 5000)
medium = sum(1 for _, b, _ in rows if 1000 <= b < 5000)
tiny = sum(1 for _, b, _ in rows if b < 1000)
avg = int(sum(b for _, b, _ in rows) / total) if total else 0

short = [(t, b) for t, b, _ in rows if b < 4000]

with open('/Users/alexdakers/meridian-server/tmp_fa_result.txt', 'w') as f:
    f.write(f"TOTALS: {total} articles | {big} full(>=5k) | {medium} medium(1-5k) | {tiny} short(<1k) | avg {avg} chars\n\n")
    f.write(f"Still under 4000 chars ({len(short)}):\n")
    for title, blen in short:
        f.write(f"  {blen:5d}  {title[:70]}\n")
print("WRITTEN")
