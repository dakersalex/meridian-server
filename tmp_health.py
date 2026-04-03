import sqlite3, json
from collections import defaultdict

conn = sqlite3.connect('/Users/alexdakers/meridian-server/meridian.db')
conn.row_factory = sqlite3.Row

# Check agent_log schema first
cols = [r[1] for r in conn.execute("PRAGMA table_info(agent_log)").fetchall()]

with open('/Users/alexdakers/meridian-server/tmp_feed_review.txt', 'w') as f:
    f.write(f"agent_log columns: {cols}\n\n")

    # ── 1. Agent log analysis ─────────────────────────────────────────────────
    agent_rows = conn.execute("""
        SELECT al.title, al.score, al.reason, al.saved_at,
               a.source as src
        FROM agent_log al
        LEFT JOIN articles a ON al.article_id = a.id
        ORDER BY al.saved_at DESC LIMIT 100
    """).fetchall()

    source_scores = defaultdict(list)
    for r in agent_rows:
        src = r['src'] or 'unknown'
        source_scores[src].append(r['score'])

    f.write("╔══════════════════════════════════════════════════════════════╗\n")
    f.write("  FEED AUTO-SAVE ANALYSIS (last 100 agent log entries)\n")
    f.write("╚══════════════════════════════════════════════════════════════╝\n\n")

    f.write("── BY SOURCE ─────────────────────────────────────────────────\n")
    f.write(f"{'Source':<30} {'Count':>6} {'Avg Score':>10} {'Min':>5} {'Max':>5}\n")
    f.write("-"*60 + "\n")
    for src, scores in sorted(source_scores.items(), key=lambda x: -len(x[1])):
        avg = sum(scores)/len(scores)
        f.write(f"{src:<30} {len(scores):>6} {avg:>10.1f} {min(scores):>5} {max(scores):>5}\n")

    f.write("\n── SCORE DISTRIBUTION ────────────────────────────────────────\n")
    all_scores = [r['score'] for r in agent_rows]
    for threshold in [10, 9, 8]:
        count = sum(1 for s in all_scores if s == threshold)
        f.write(f"  Score {threshold}: {count} articles\n")

    f.write("\n── ALL AUTO-SAVED SOURCES IN FEED ────────────────────────────\n")
    feed_sources = conn.execute("""
        SELECT source, COUNT(*) cnt
        FROM articles WHERE auto_saved=1
        GROUP BY source ORDER BY cnt DESC
    """).fetchall()
    for r in feed_sources:
        f.write(f"  {r['source']:<35} {r['cnt']:>4} articles\n")

    f.write("\n── RECENT NON-CORE AUTO-SAVES (not FT/Eco/FA/BBG) ───────────\n")
    non_core = conn.execute("""
        SELECT a.source, a.title, al.score, al.reason
        FROM agent_log al
        JOIN articles a ON al.article_id = a.id
        WHERE a.source NOT IN ('Financial Times','The Economist','Foreign Affairs','Bloomberg')
        ORDER BY al.saved_at DESC LIMIT 25
    """).fetchall()
    for r in non_core:
        f.write(f"\n  [{r['score']}] [{r['source'][:18]}] {r['title'][:65]}\n")
        f.write(f"       {(r['reason'] or '')[:90]}\n")

    # ── 2. Bloomberg ──────────────────────────────────────────────────────────
    f.write("\n\n╔══════════════════════════════════════════════════════════════╗\n")
    f.write("  BLOOMBERG ANALYSIS\n")
    f.write("╚══════════════════════════════════════════════════════════════╝\n\n")

    bbg = conn.execute("""
        SELECT title, status, auto_saved, pub_date, LENGTH(body) as blen, saved_at
        FROM articles WHERE source='Bloomberg'
        ORDER BY saved_at DESC
    """).fetchall()

    auto_bbg = [r for r in bbg if r['auto_saved']]
    manual_bbg = [r for r in bbg if not r['auto_saved']]

    f.write(f"  Total Bloomberg:          {len(bbg)}\n")
    f.write(f"  Auto-saved (agent):       {len(auto_bbg)}\n")
    f.write(f"  Your manual saves:        {len(manual_bbg)}\n\n")

    f.write("── HOW BLOOMBERG CURRENTLY WORKS ─────────────────────────────\n")
    f.write("  NO automated Playwright scraper — Bloomberg blocks headless browsers.\n")
    f.write("  Bloomberg articles arrive via:\n")
    f.write("    a) Agent web search (Sonnet scores, auto-saves if >=8)\n")
    f.write("    b) Manual + Add Article\n")
    f.write("  Your saved Bloomberg articles in the Bloomberg app are NOT\n")
    f.write("  automatically synced — there is no bloomberg_scraper equivalent.\n\n")

    import os
    has_profile = os.path.exists('/Users/alexdakers/meridian-server/bloomberg_profile')
    f.write(f"  bloomberg_profile/ exists: {has_profile}\n\n")

    f.write("── YOUR MANUAL BBG SAVES (auto_saved=0) ──────────────────────\n")
    for r in manual_bbg:
        f.write(f"  [{r['blen']:5,}ch] {r['title'][:70]}\n")

    f.write("\n── RECENT AUTO BBG (agent picks) ─────────────────────────────\n")
    for r in auto_bbg[:10]:
        f.write(f"  [{r['blen']:5,}ch] {r['title'][:70]}\n")

print("DONE")
