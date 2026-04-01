"""
Add GET /api/kt/brief/context-debug?theme_idx=0 endpoint to server.py.
Returns the full article selection breakdown: buckets, scores, selected articles.
"""
from pathlib import Path

p = Path('/Users/alexdakers/meridian-server/server.py')
src = p.read_text()

NEW_ROUTE = '''

@app.route("/api/kt/brief/context-debug", methods=["POST"])
def kt_brief_context_debug():
    """
    Debug endpoint: show which articles _build_article_context would select for a brief.
    POST body: {articles: [...], brief_type: "full"}
    Returns bucket breakdown with scores so you can inspect selection quality.
    """
    import datetime as _dt
    data = request.json or {}
    articles = data.get("articles", [])
    brief_type = data.get("brief_type", "full")

    BUCKETS = 2 if brief_type == "short" else 4
    PER_BUCKET = 15
    SOURCE_CAP = 5

    def get_ts_days(a):
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
            return 0

    def ordinal_to_date(n):
        try:
            return _dt.date.fromordinal(n).isoformat()
        except Exception:
            return "unknown"

    candidates = [a for a in articles if a.get("summary")]
    if not candidates:
        return jsonify({"error": "no articles with summaries"}), 400

    candidates_sorted = sorted(candidates, key=get_ts_days)
    ts_min = get_ts_days(candidates_sorted[0])
    ts_max = get_ts_days(candidates_sorted[-1])
    span = max(ts_max - ts_min, 1)
    bucket_size = span / BUCKETS

    def get_bucket(a):
        b = int((get_ts_days(a) - ts_min) / bucket_size)
        return min(b, BUCKETS - 1)

    def score_article(a):
        status_bonus = 1000 if a.get("status") == "full_text" else 0
        return status_bonus + len(a.get("summary") or "")

    buckets = [[] for _ in range(BUCKETS)]
    for a in candidates_sorted:
        buckets[get_bucket(a)].append(a)

    result_buckets = []
    all_selected_ids = set()

    for b_idx, bucket in enumerate(buckets):
        ranked = sorted(bucket, key=score_article, reverse=True)
        source_counts = {}
        selected = []
        skipped_source_cap = []

        for a in ranked:
            src = a.get("source", "")
            score = score_article(a)
            if source_counts.get(src, 0) >= SOURCE_CAP:
                skipped_source_cap.append({
                    "title": a.get("title", "")[:80],
                    "source": src,
                    "score": score,
                    "reason": f"source cap ({SOURCE_CAP}) reached for {src}"
                })
                continue
            source_counts[src] = source_counts.get(src, 0) + 1
            selected.append(a)
            all_selected_ids.add(a.get("id"))
            if len(selected) >= PER_BUCKET:
                break

        # Date range of this bucket
        bucket_start = ordinal_to_date(int(ts_min + b_idx * bucket_size))
        bucket_end = ordinal_to_date(int(ts_min + (b_idx + 1) * bucket_size) - 1)

        result_buckets.append({
            "bucket": b_idx + 1,
            "date_range": f"{bucket_start} to {bucket_end}",
            "total_in_bucket": len(bucket),
            "selected_count": len(selected),
            "source_counts": source_counts,
            "selected": [
                {
                    "title": a.get("title", "")[:80],
                    "source": a.get("source", ""),
                    "pub_date": a.get("pub_date", ""),
                    "status": a.get("status", ""),
                    "score": score_article(a),
                    "summary_len": len(a.get("summary") or "")
                }
                for a in selected
            ],
            "skipped_source_cap": skipped_source_cap[:10]  # first 10 skipped
        })

    return jsonify({
        "brief_type": brief_type,
        "total_candidates": len(candidates),
        "total_selected": len(all_selected_ids),
        "buckets": BUCKETS,
        "reporting_period": f"{ordinal_to_date(ts_min)} to {ordinal_to_date(ts_max)}",
        "bucket_breakdown": result_buckets
    })

'''

# Insert before the if __name__ == '__main__' block, or before the last route
anchor = '\nif __name__ == "__main__":'
if anchor in src:
    src = src.replace(anchor, NEW_ROUTE + anchor, 1)
    p.write_text(src)
    print("Inserted before __main__ OK")
else:
    # Fallback: append before end of file
    src = src.rstrip() + NEW_ROUTE
    p.write_text(src)
    print("Appended to end OK")
