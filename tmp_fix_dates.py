"""Fix get_ts_days in both _build_article_context and kt_brief_context_debug
to handle messy date formats like '26 March 2026', 'March 2025', 'March 2026' etc.
"""
from pathlib import Path

p = Path('/Users/alexdakers/meridian-server/brief_pdf.py')
src = p.read_text()

OLD = """    def get_ts_days(a):
        pd = (a.get("pub_date") or "").strip()
        if pd and pd not in ("null", ""):
            try:
                return _dt.date.fromisoformat(pd[:10]).toordinal()
            except Exception:
                pass
        sa = a.get("saved_at") or 0
        try:
            return int(sa) // 86400000
        except Exception:
            return 0"""

NEW = """    def get_ts_days(a):
        pd = (a.get("pub_date") or "").strip()
        if pd and pd not in ("null", ""):
            # Try ISO format first: YYYY-MM-DD
            try:
                return _dt.date.fromisoformat(pd[:10]).toordinal()
            except Exception:
                pass
            # Try human formats: '26 March 2026', 'March 2026', 'Mar 2026' etc.
            for fmt in ("%d %B %Y", "%d %b %Y", "%B %Y", "%b %Y",
                        "%B %d, %Y", "%b %d, %Y"):
                try:
                    return _dt.datetime.strptime(pd.strip(), fmt).date().toordinal()
                except Exception:
                    pass
        # Fall back to saved_at (millisecond epoch -> days)
        sa = a.get("saved_at") or 0
        try:
            return int(sa) // 86400000
        except Exception:
            return 0"""

assert OLD in src, "OLD not found in brief_pdf.py"
src = src.replace(OLD, NEW, 1)
p.write_text(src)
print("brief_pdf.py patched OK")
