"""
Patch _build_article_context in brief_pdf.py:
- Split reporting period into 4 equal calendar time buckets
- Select the 15 most detailed articles from each bucket
- "Most detailed" = full_text first, then longest summary, source cap of 5 per bucket
- Falls back gracefully if a bucket has fewer than 15 articles
"""
from pathlib import Path

p = Path('/Users/alexdakers/meridian-server/brief_pdf.py')
src = p.read_text()

OLD = '''def _build_article_context(articles, brief_type):
    MAX_ARTICLES = 30 if brief_type == "short" else 60
    BODY_EXCERPT = 400
    parts = []
    for a in articles[:MAX_ARTICLES]:
        if not a.get("summary"):
            continue
        snippet = f"SOURCE: {a.get('source', '')}\\nTITLE: {a.get('title', '')}\\n"
        snippet += f"SUMMARY: {a.get('summary', '')}"
        body = (a.get("body") or "").strip()
        if body and len(body) > 100:
            excerpt = body[:BODY_EXCERPT].rsplit(" ", 1)[0]
            snippet += f"\\nEXCERPT: {excerpt}\\u2026"
        parts.append(snippet)
    return "\\n\\n---\\n\\n".join(parts)'''

NEW = '''def _build_article_context(articles, brief_type):
    """
    Select articles for brief context using temporal bucketing.

    For full briefs: divide the reporting period into 4 equal calendar-time
    buckets and select the best 15 articles from each (total: up to 60).
    For short briefs: 2 buckets x 15 = 30.

    Within each bucket, articles are ranked by:
      1. full_text status first (have summaries + body excerpts)
      2. Summary length (longer = more substance)
    With a per-source cap of 5 per bucket to ensure source diversity.

    Falls back to simple recency sort if timestamps are missing.
    """
    import datetime

    BUCKETS = 2 if brief_type == "short" else 4
    PER_BUCKET = 15
    SOURCE_CAP = 5
    BODY_EXCERPT = 400

    # Parse timestamps — use pub_date if valid, else saved_at
    def get_ts(a):
        pd = a.get("pub_date") or ""
        if pd and pd not in ("null", ""):
            try:
                # Handle ISO strings and plain dates
                pd_clean = pd[:10]  # YYYY-MM-DD
                return datetime.date.fromisoformat(pd_clean).toordinal()
            except Exception:
                pass
        # Fall back to saved_at (millisecond epoch)
        sa = a.get("saved_at") or 0
        try:
            return int(sa) // 86400000  # convert ms to days
        except Exception:
            return 0

    # Only consider articles with at least a summary
    candidates = [a for a in articles if a.get("summary")]
    if not candidates:
        return ""

    # Sort by timestamp ascending (oldest first) for bucket assignment
    candidates_sorted = sorted(candidates, key=get_ts)

    # Find time range
    ts_min = get_ts(candidates_sorted[0])
    ts_max = get_ts(candidates_sorted[-1])
    span = max(ts_max - ts_min, 1)
    bucket_size = span / BUCKETS

    # Assign each article to a bucket (0-indexed)
    def get_bucket(a):
        ts = get_ts(a)
        b = int((ts - ts_min) / bucket_size)
        return min(b, BUCKETS - 1)  # clamp last article into final bucket

    buckets = [[] for _ in range(BUCKETS)]
    for a in candidates_sorted:
        buckets[get_bucket(a)].append(a)

    # Score articles within each bucket and pick the best PER_BUCKET
    def score_article(a):
        """Higher = better. full_text articles ranked first, then by summary length."""
        status_bonus = 1000 if a.get("status") == "full_text" else 0
        summary_len = len(a.get("summary") or "")
        return status_bonus + summary_len

    selected = []
    for bucket in buckets:
        # Sort by score descending
        ranked = sorted(bucket, key=score_article, reverse=True)
        # Apply per-source cap
        source_counts = {}
        bucket_selected = []
        for a in ranked:
            src = a.get("source", "")
            if source_counts.get(src, 0) >= SOURCE_CAP:
                continue
            source_counts[src] = source_counts.get(src, 0) + 1
            bucket_selected.append(a)
            if len(bucket_selected) >= PER_BUCKET:
                break
        selected.extend(bucket_selected)

    # Build context strings
    parts = []
    for a in selected:
        snippet = f"SOURCE: {a.get('source', '')}\\nTITLE: {a.get('title', '')}\\n"
        snippet += f"SUMMARY: {a.get('summary', '')}"
        body = (a.get("body") or "").strip()
        if body and len(body) > 100:
            excerpt = body[:BODY_EXCERPT].rsplit(" ", 1)[0]
            snippet += f"\\nEXCERPT: {excerpt}\\u2026"
        parts.append(snippet)

    return "\\n\\n---\\n\\n".join(parts)'''

assert OLD in src, "OLD not found — check function signature"
src = src.replace(OLD, NEW, 1)
p.write_text(src)
print("Patched OK")
print(f"New function is {len(NEW.splitlines())} lines")
