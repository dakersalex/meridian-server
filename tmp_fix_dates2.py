"""Fix get_ts_days in brief_pdf.py to handle human date formats like '26 March 2026'."""
from pathlib import Path

p = Path('/Users/alexdakers/meridian-server/brief_pdf.py')
lines = p.read_text().splitlines(keepends=True)

# Lines 380-390 (1-indexed) = indices 379-389
start, end = 379, 390

new_fn = """    def get_ts_days(a):
        pd = (a.get('pub_date') or '').strip()
        if pd and pd not in ('null', ''):
            # ISO format: YYYY-MM-DD
            try:
                return _dt.date.fromisoformat(pd[:10]).toordinal()
            except Exception:
                pass
            # Human formats: '26 March 2026', 'March 2026', '26 Mar 2026' etc.
            for fmt in ('%d %B %Y', '%d %b %Y', '%B %Y', '%b %Y',
                        '%B %d, %Y', '%b %d, %Y'):
                try:
                    return _dt.datetime.strptime(pd.strip(), fmt).date().toordinal()
                except Exception:
                    pass
        # Fall back to saved_at (millisecond epoch)
        sa = a.get('saved_at') or 0
        try:
            return int(sa) // 86400000
        except Exception:
            return 0
"""

new_lines = new_fn.splitlines(keepends=True)
result = lines[:start] + new_lines + lines[end:]
p.write_text(''.join(result))
print(f"Replaced lines {start+1}-{end}. New total: {len(result)}")
