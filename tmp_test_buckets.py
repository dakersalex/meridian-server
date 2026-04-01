import sys, importlib, sqlite3
sys.path.insert(0, '/Users/alexdakers/meridian-server')
import brief_pdf; importlib.reload(brief_pdf)
from brief_pdf import _build_article_context

conn = sqlite3.connect('/Users/alexdakers/meridian-server/meridian.db')
conn.row_factory = sqlite3.Row
rows = conn.execute("""
    SELECT id, source, title, summary, body, status, pub_date, saved_at
    FROM articles
    WHERE (title LIKE '%Iran%' OR title LIKE '%Hormuz%' OR title LIKE '%Houthi%'
           OR title LIKE '%Gulf%' OR title LIKE '%oil price%' OR tags LIKE '%iran%')
    AND summary != ''
    ORDER BY saved_at DESC
    LIMIT 227
""").fetchall()
conn.close()

articles = [dict(r) for r in rows]
print(f'Input: {len(articles)} articles')

ctx = _build_article_context(articles, 'full')

parts = ctx.split('\n\n---\n\n')
print(f'Output: {len(parts)} articles selected')

# Show the pub_date range of each quartile
import datetime as _dt

def get_ts(a):
    pd = (a.get('pub_date') or '').strip()
    if pd and pd not in ('null', ''):
        try:
            return pd[:10]
        except: pass
    sa = a.get('saved_at') or 0
    return str(_dt.date.fromordinal(int(sa)//86400000 + 1))

# Re-run bucketing to show dates
candidates = [a for a in articles if a.get('summary')]

def get_ts_days(a):
    import datetime as _dt
    pd = (a.get('pub_date') or '').strip()
    if pd and pd not in ('null', ''):
        try:
            return _dt.date.fromisoformat(pd[:10]).toordinal()
        except: pass
    sa = a.get('saved_at') or 0
    try: return int(sa) // 86400000
    except: return 0

cands = sorted(candidates, key=get_ts_days)
n = len(cands)
BUCKETS = 4
for i in range(BUCKETS):
    start = (i * n) // BUCKETS
    end = ((i + 1) * n) // BUCKETS
    bucket = cands[start:end]
    dates = [a.get('pub_date','')[:10] for a in bucket if a.get('pub_date')]
    dates = [d for d in dates if d]
    date_range = f"{min(dates) if dates else '?'} → {max(dates) if dates else '?'}"
    full_text = sum(1 for a in bucket if a.get('status') == 'full_text')
    print(f'  Q{i+1}: {len(bucket)} articles, {full_text} full_text, dates: {date_range}')

print(f'\nSelected {len(parts)}/60 total')
print('COMPILE OK' if len(parts) > 0 else 'ERROR: no articles')
