
path = '/Users/alexdakers/meridian-server/brief_pdf.py'
with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

old = '''def _build_article_context(articles, brief_type):
    """
    Select articles for brief context using temporal bucketing.

    Divides articles into equal-count quartiles (not equal calendar time) and
    selects the best articles from each, ensuring the brief covers the whole
    arc of a story - not just the most recent reporting.

    Full brief:  4 buckets x 15 articles = up to 60
    Short brief: 2 buckets x 15 articles = up to 30

    Within each bucket, articles are ranked by:
      1. full_text status first (have summaries + body excerpts)
      2. Summary length (longer = more analytical substance)
    Per-source cap of 5 per bucket ensures source diversity.
    """
    import datetime as _dt

    BUCKETS = 2 if brief_type == 'short' else 4
    PER_BUCKET = 15
    SOURCE_CAP = 5
    BODY_EXCERPT = 400

    def get_ts_days(a):
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
            return 0

    candidates = [a for a in articles if a.get('summary')]
    if not candidates:
        return '' 

    # Sort by publication date (oldest first)
    candidates_sorted = sorted(candidates, key=get_ts_days)

    # Split into equal-count quartiles (not equal calendar time).
    # With 227 articles and 4 buckets, each bucket gets ~56-57 articles.
    # This guarantees the brief draws from every phase of the story equally,
    # even if reporting density is uneven across time.
    n = len(candidates_sorted)
    buckets = []
    for i in range(BUCKETS):
        start = (i * n) // BUCKETS
        end = ((i + 1) * n) // BUCKETS
        buckets.append(candidates_sorted[start:end])

    def score_article(a):
        status_bonus = 1000 if a.get('status') == 'full_text' else 0
        return status_bonus + len(a.get('summary') or '')

    selected = []
    for bucket in buckets:
        ranked = sorted(bucket, key=score_article, reverse=True)
        source_counts = {}
        bucket_selected = []
        for a in ranked:
            src = a.get('source', '')
            if source_counts.get(src, 0) >= SOURCE_CAP:
                continue
            source_counts[src] = source_counts.get(src, 0) + 1
            bucket_selected.append(a)
            if len(bucket_selected) >= PER_BUCKET:
                break
        selected.extend(bucket_selected)

    log.info(
        f\'Article context: {len(candidates)} candidates, {BUCKETS} buckets \' +
        f\'({[len(b) for b in buckets]}), selected {len(selected)}\'
    )

    parts = []
    for a in selected:
        snippet = \'SOURCE: \' + a.get(\'source\', \'\') + \'\\nTITLE: \' + a.get(\'title\', \'\') + \'\\n\'
        snippet += \'SUMMARY: \' + a.get(\'summary\', \'\')
        body = (a.get(\'body\') or \'\').strip()
        if body and len(body) > 100:
            excerpt = body[:BODY_EXCERPT].rsplit(\' \', 1)[0]
            snippet += \'\\nEXCERPT: \' + excerpt + \'…\'
        parts.append(snippet)
    return \'\\n\\n---\\n\\n\'.join(parts)'''

new = '''def _build_article_context(articles, brief_type):
    """
    Select articles for brief context using score-based selection with a
    soft temporal anchor.

    ALL articles are used as candidates (no artificial cap based on brief type —
    short vs full briefs receive the same input; the difference is in what the
    model is asked to produce, not what it sees).

    If the theme has >150 articles, take the top 150 by weighted score to
    avoid context quality degradation at very large corpus sizes.

    Selection logic:
      1. Score every article: full_text bonus (1000) + summary length +
         recency multiplier (×1.5 last 7 days, ×1.2 last 30 days, ×1.0 older)
      2. Reserve anchor slots from the oldest third of the corpus:
         ~10% of candidate count, min 3, max 10. These guarantee narrative
         foundation even if older articles score lower than recent ones.
      3. Fill remaining slots with top-scoring non-anchor articles.

    No per-source cap — source representation is proportional to volume and
    quality of coverage, which is the correct behaviour.
    """
    import datetime as _dt

    MAX_ARTICLES = 150
    BODY_EXCERPT = 400

    def get_ts_days(a):
        pd = (a.get('pub_date') or '').strip()
        if pd and pd not in ('null', ''):
            try:
                return _dt.date.fromisoformat(pd[:10]).toordinal()
            except Exception:
                pass
            for fmt in ('%d %B %Y', '%d %b %Y', '%B %Y', '%b %Y',
                        '%B %d, %Y', '%b %d, %Y'):
                try:
                    return _dt.datetime.strptime(pd.strip(), fmt).date().toordinal()
                except Exception:
                    pass
        sa = a.get('saved_at') or 0
        try:
            return int(sa) // 86400000
        except Exception:
            return 0

    candidates = [a for a in articles if a.get('summary')]
    if not candidates:
        return ''

    today_ord = _dt.date.today().toordinal()

    def score_article(a):
        base = (1000 if a.get('status') == 'full_text' else 0) + len(a.get('summary') or '')
        days_ago = today_ord - get_ts_days(a)
        if days_ago <= 7:
            multiplier = 1.5
        elif days_ago <= 30:
            multiplier = 1.2
        else:
            multiplier = 1.0
        return base * multiplier

    # Sort oldest-first for anchor identification
    candidates_sorted = sorted(candidates, key=get_ts_days)
    n = len(candidates_sorted)

    # Anchor slots: oldest third of corpus, proportional count
    anchor_count = max(3, min(10, round(n * 0.1)))
    oldest_third_end = n // 3
    oldest_third = candidates_sorted[:oldest_third_end]
    anchor_articles = sorted(oldest_third, key=score_article, reverse=True)[:anchor_count]
    anchor_ids = {id(a) for a in anchor_articles}

    # Remaining candidates scored and sorted
    remaining = [a for a in candidates if id(a) not in anchor_ids]
    remaining_scored = sorted(remaining, key=score_article, reverse=True)

    # Total cap: use all articles up to MAX_ARTICLES
    remaining_slots = max(0, MAX_ARTICLES - len(anchor_articles))
    selected_remaining = remaining_scored[:remaining_slots]

    # Combine: anchors first (oldest→newest), then remaining by score (newest bias)
    selected = sorted(anchor_articles, key=get_ts_days) + selected_remaining

    log.info(
        f'Article context: {n} candidates, {len(anchor_articles)} anchor + '
        f'{len(selected_remaining)} scored = {len(selected)} total '
        f'(brief_type={brief_type})'
    )

    parts = []
    for a in selected:
        pub = a.get('pub_date', '')
        snippet = f"SOURCE: {a.get('source', '')} | DATE: {pub}\\nTITLE: {a.get('title', '')}\\n"
        snippet += 'SUMMARY: ' + a.get('summary', '')
        body = (a.get('body') or '').strip()
        if body and len(body) > 100:
            excerpt = body[:BODY_EXCERPT].rsplit(' ', 1)[0]
            snippet += '\\nEXCERPT: ' + excerpt + '…'
        parts.append(snippet)
    return '\\n\\n---\\n\\n'.join(parts)'''

if old in src:
    src = src.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(src)
    print('PATCHED OK')
else:
    print('NOT FOUND')
