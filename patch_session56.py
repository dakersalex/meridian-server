import ast

with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    content = f.read()

old = '''    def _norm_date(raw):
        import re as _re
        if not raw: return ""
        raw = raw.strip()
        if _re.match(r"\\d{4}-\\d{2}-\\d{2}", raw): return raw
        m = _re.match(r"(\\d{1,2})\\s+([A-Za-z]+)\\s+(\\d{4})", raw)
        if m:
            mo = _SUG_MONTHS.get(m.group(2).lower())
            if mo: return f"{m.group(3)}-{mo:02d}-{int(m.group(1)):02d}"
        m = _re.match(r"([A-Za-z]+)\\s+(\\d{1,2}),?\\s+(\\d{4})", raw)
        if m:
            mo = _SUG_MONTHS.get(m.group(1).lower())
            if mo: return f"{m.group(3)}-{mo:02d}-{int(m.group(2)):02d}"
        m = _re.match(r"([A-Za-z]+)\\s+(\\d{4})$", raw)
        if m:
            mo = _SUG_MONTHS.get(m.group(1).lower())
            if mo: return f"{m.group(2)}-{mo:02d}-01"
        return raw'''

new = '''    def _norm_date(raw):
        import re as _re
        from datetime import datetime as _dt
        if not raw: return ""
        raw = raw.strip()
        if _re.match(r"\\d{4}-\\d{2}-\\d{2}", raw): return raw[:10]
        # DD Month YYYY or DD Mon YYYY (zero-padded or not)
        m = _re.match(r"(\\d{1,2})\\s+([A-Za-z]+)\\s+(\\d{4})", raw)
        if m:
            mo = _SUG_MONTHS.get(m.group(2).lower()[:3])
            if mo: return f"{m.group(3)}-{mo:02d}-{int(m.group(1)):02d}"
        # Month DD, YYYY or Month DD YYYY
        m = _re.match(r"([A-Za-z]+)\\s+(\\d{1,2}),?\\s+(\\d{4})", raw)
        if m:
            mo = _SUG_MONTHS.get(m.group(1).lower()[:3])
            if mo: return f"{m.group(3)}-{mo:02d}-{int(m.group(2)):02d}"
        # Month YYYY
        m = _re.match(r"([A-Za-z]+)\\s+(\\d{4})$", raw)
        if m:
            mo = _SUG_MONTHS.get(m.group(1).lower()[:3])
            if mo: return f"{m.group(2)}-{mo:02d}-01"
        # Relative dates — fall back to today
        if any(x in raw.lower() for x in ["ago", "yesterday", "today", "hour", "day", "week"]):
            return _dt.now().strftime("%Y-%m-%d")
        # ISO with timezone e.g. 2026-04-17T10:00:00Z
        m = _re.match(r"(\\d{4}-\\d{2}-\\d{2})T", raw)
        if m: return m.group(1)
        return raw'''

assert old in content, "Pattern not found"
content = content.replace(old, new, 1)

ast.parse(content)
print("Syntax OK")
with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(content)
print("Done")
