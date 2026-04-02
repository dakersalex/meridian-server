import sqlite3, json

conn = sqlite3.connect('/Users/alexdakers/meridian-server/meridian.db')

# Full body length distribution for Economist
rows = conn.execute("""
    SELECT LENGTH(body) as blen, status, title, body
    FROM articles WHERE source='The Economist'
    ORDER BY blen ASC
""").fetchall()

sizes = [r[0] for r in rows]
total = len(sizes)

buckets = {
    'empty_0':        sum(1 for s in sizes if s == 0),
    'tiny_1_500':     sum(1 for s in sizes if 1 <= s < 500),
    'short_500_2k':   sum(1 for s in sizes if 500 <= s < 2000),
    'med_2k_5k':      sum(1 for s in sizes if 2000 <= s < 5000),
    'good_5k_10k':    sum(1 for s in sizes if 5000 <= s < 10000),
    'full_10k_plus':  sum(1 for s in sizes if s >= 10000),
}

with open('/Users/alexdakers/meridian-server/tmp_eco_health.txt', 'w') as f:
    f.write(f"Economist body length distribution ({total} articles)\n")
    f.write("="*55 + "\n")
    for k, v in buckets.items():
        bar = '█' * (v // 2)
        f.write(f"  {k:<20} {v:>4}  ({round(v/total*100):>2}%)  {bar}\n")
    f.write(f"\n  Avg: {int(sum(sizes)/total):,} | Min: {min(sizes):,} | Max: {max(sizes):,}\n\n")

    # Sample the short ones — are they AI summaries or real text?
    f.write("Sample of SHORT bodies (500-2000 chars) — first 200 chars each:\n")
    f.write("-"*55 + "\n")
    short_samples = [(r[2], r[0], r[3]) for r in rows if 500 <= r[0] < 2000][:8]
    for title, blen, body in short_samples:
        f.write(f"\n  [{blen}ch] {title[:60]}\n")
        f.write(f"  Preview: {(body or '')[:200]}\n")

    # Sample the MEDIUM ones (2k-5k) — real or AI?
    f.write("\n\nSample of MEDIUM bodies (2000-5000 chars):\n")
    f.write("-"*55 + "\n")
    med_samples = [(r[2], r[0], r[3]) for r in rows if 2000 <= r[0] < 5000][:6]
    for title, blen, body in med_samples:
        f.write(f"\n  [{blen}ch] {title[:60]}\n")
        f.write(f"  Preview: {(body or '')[:200]}\n")

    # What does a GOOD one look like?
    f.write("\n\nSample of FULL bodies (>5000 chars):\n")
    f.write("-"*55 + "\n")
    good_samples = [(r[2], r[0], r[3]) for r in rows if r[0] >= 5000][:3]
    for title, blen, body in good_samples:
        f.write(f"\n  [{blen}ch] {title[:60]}\n")
        f.write(f"  Preview: {(body or '')[:200]}\n")

print("DONE")
