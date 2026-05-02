#!/usr/bin/env python3
"""
P2-9 — Economist weekly AI pick over VPS-ingested articles (option δ).

Replaces the Mac CDP-scrape-based ai_pick_economist_weekly() with a query
over articles already ingested via the Chrome extension's bookmark sync.

Per PHASE_2_PLAN.md § 7:
  "On the VPS, a weekly scheduled job queries articles ingested from
   Economist in the last 7 days, runs the existing `ai_pick` scoring,
   surfaces top N to the Suggested swim lane."

Behaviour:
  - Query: source='The Economist' AND saved_at within last 7 days
    (saved_at is INTEGER milliseconds since epoch — see NOTES.md)
  - Skip articles already scored (present in suggested_articles by url)
  - Score remaining via Sonnet (mirrors server.py:ai_pick_feed_scrape pattern)
  - Insert top-scoring (>= 6, matching Suggested-inbox threshold) into
    suggested_articles. Articles scoring >= 8 should also flow into Feed
    via existing trusted-source promotion logic; this script writes only
    to suggested_articles and leaves Feed promotion to existing pipeline.
  - Idempotent: per-week gate key in kt_meta. Running twice in the
    same ISO-week is a no-op.
  - Logs to /var/log/meridian/economist_weekly.log

Schedule (when installed via deploy/block5_cron_addition.txt): weekly,
clear of existing 02:30 / 03:40 / 09:40 UTC slots.

Invocation:
  /opt/meridian-server/venv/bin/python3 /opt/meridian-server/economist_weekly_pick.py

Dry-run mode (no DB writes, no API calls — just print what would be scored):
  /opt/meridian-server/venv/bin/python3 /opt/meridian-server/economist_weekly_pick.py --dry-run
"""

import os
import sys
import json
import time
import sqlite3
import logging
import argparse
import datetime
from pathlib import Path

# ── Constants ────────────────────────────────────────────────────────────────
DB_PATH = "/opt/meridian-server/meridian.db"
LOG_PATH = "/var/log/meridian/economist_weekly.log"
WINDOW_MS = 7 * 86400 * 1000          # 7 days
SUGGESTED_FLOOR = 6                   # Suggested inbox threshold
TOP_N_HARD_CAP = 25                   # Don't score more than this per run
GATE_KEY_PREFIX = "economist_weekly_pick"
MODEL = "claude-sonnet-4-6"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

# ── Logging ──────────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("economist_weekly")
# Also echo to stderr when run interactively / by cron with MAILTO
_stderr = logging.StreamHandler(sys.stderr)
_stderr.setLevel(logging.INFO)
_stderr.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
log.addHandler(_stderr)


def iso_week_key():
    """Gate key for the current ISO week. Mon–Sun."""
    y, w, _ = datetime.datetime.utcnow().isocalendar()
    return f"{GATE_KEY_PREFIX}_{y}_W{w:02d}"


def already_ran_this_week(conn):
    key = iso_week_key()
    row = conn.execute(
        "SELECT value FROM kt_meta WHERE key=?", (key,)
    ).fetchone()
    return row is not None


def mark_ran_this_week(conn):
    key = iso_week_key()
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")
    conn.execute(
        "INSERT OR REPLACE INTO kt_meta (key, value) VALUES (?, ?)",
        (key, today),
    )


def fetch_candidates(conn):
    """Economist articles saved in last 7 days, not already in suggested_articles."""
    cutoff_ms = int(time.time() * 1000) - WINDOW_MS
    rows = conn.execute(
        """
        SELECT a.id, a.title, a.url, a.summary, a.body, a.pub_date, a.saved_at
        FROM articles a
        WHERE a.source = 'The Economist'
          AND a.saved_at > ?
          AND a.url NOT IN (SELECT url FROM suggested_articles WHERE url IS NOT NULL AND url != '')
          AND COALESCE(a.title, '') != ''
        ORDER BY a.saved_at DESC
        LIMIT ?
        """,
        (cutoff_ms, TOP_N_HARD_CAP),
    ).fetchall()
    return rows


def build_taste_profile(conn):
    ft_row = conn.execute(
        "SELECT value FROM kt_meta WHERE key='ai_pick_followed_topics'"
    ).fetchone()
    tt_row = conn.execute(
        "SELECT value FROM kt_meta WHERE key='ai_pick_taste_titles'"
    ).fetchone()
    followed = json.loads(ft_row[0]) if ft_row else []
    taste = json.loads(tt_row[0]) if tt_row else []
    topics_str = (
        ", ".join(followed)
        if followed
        else "geopolitics, economics, finance, markets"
    )
    taste_str = "\n".join(f"- {t}" for t in taste[:50])
    return topics_str, taste_str


def score_with_sonnet(candidates, topics_str, taste_str):
    """
    Returns a list of (id, score, reason) tuples, length == len(candidates).
    On API failure, logs and returns []. Caller treats empty as "skip this run".
    """
    import urllib.request

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        # Fall back to .env in repo root, same pattern as server.py
        env_path = Path("/opt/meridian-server/.env")
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not api_key:
        log.error("ANTHROPIC_API_KEY not set; cannot score")
        return []

    items_block = "\n\n".join(
        f"[{i}] TITLE: {c[1]}\nPREVIEW: {(c[3] or c[4] or '')[:400]}"
        for i, c in enumerate(candidates)
    )

    prompt = f"""You score Economist articles for a reader whose interests are: {topics_str}.

Recent saved titles (taste signal):
{taste_str}

For each item below, return an integer score 1-10 reflecting how strongly
this reader would want to read it now, and a short (<=15 word) reason.

Items:
{items_block}

Return ONLY a JSON array of {len(candidates)} objects in the same order:
[{{"score": int, "reason": str}}, ...]
No prose, no code fences."""

    body = {
        "model": MODEL,
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": prompt}],
    }
    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=json.dumps(body).encode(),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read())
    except Exception as e:
        log.error(f"Sonnet call failed: {e}")
        return []

    text = ""
    for block in payload.get("content", []):
        if block.get("type") == "text":
            text += block.get("text", "")
    text = text.strip()
    # Tolerate the model wrapping in code fences anyway
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.rsplit("```", 1)[0]
    try:
        scored = json.loads(text)
    except Exception as e:
        log.error(f"Sonnet returned non-JSON: {e}; raw head: {text[:300]}")
        return []

    if not isinstance(scored, list) or len(scored) != len(candidates):
        log.error(
            f"Sonnet score length mismatch: got {len(scored) if isinstance(scored, list) else 'non-list'},"
            f" expected {len(candidates)}"
        )
        return []

    out = []
    for c, s in zip(candidates, scored):
        try:
            score = int(s.get("score", 0))
        except Exception:
            score = 0
        reason = (s.get("reason") or "")[:200]
        out.append((c[0], score, reason))
    return out


def insert_into_suggested(conn, candidates, scored, dry_run=False):
    """Insert >=SUGGESTED_FLOOR into suggested_articles. Returns count inserted."""
    by_id = {c[0]: c for c in candidates}
    now_ms = int(time.time() * 1000)
    today_iso = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    inserted = 0
    for art_id, score, reason in scored:
        if score < SUGGESTED_FLOOR:
            continue
        c = by_id.get(art_id)
        if not c:
            continue
        _, title, url, summary, body, pub_date, _saved_at = c
        preview = (summary or (body or "")[:300] or "")[:500]
        if dry_run:
            log.info(
                f"DRY-RUN would insert: score={score} title={title[:80]!r}"
            )
            inserted += 1
            continue
        try:
            conn.execute(
                """
                INSERT INTO suggested_articles
                  (title, url, source, snapshot_date, score, reason,
                   added_at, status, pub_date, preview)
                VALUES (?, ?, 'The Economist', ?, ?, ?, ?, 'new', ?, ?)
                """,
                (title, url, today_iso, score, reason, now_ms, pub_date or "", preview),
            )
            inserted += 1
        except sqlite3.IntegrityError as e:
            # url unique constraint or similar — already there
            log.warning(f"Skip insert for {url}: {e}")
    return inserted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be scored/inserted without API calls or writes")
    parser.add_argument("--force", action="store_true",
                        help="Bypass weekly idempotency gate")
    args = parser.parse_args()

    log.info(f"=== economist_weekly_pick start (dry_run={args.dry_run} force={args.force}) ===")

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS kt_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        if not args.force and already_ran_this_week(conn):
            log.info(f"Already ran this ISO week ({iso_week_key()}); exiting (idempotent no-op)")
            return 0

        candidates = fetch_candidates(conn)
        log.info(f"Pool size: {len(candidates)} Economist articles in last 7 days, unscored")

        if len(candidates) < 5:
            log.warning(
                f"Pool too thin ({len(candidates)} < 5); skipping scoring this run."
                " Investigate ingestion if this persists for 2 consecutive weeks."
            )
            if not args.dry_run and not args.force:
                mark_ran_this_week(conn)
            return 0

        topics_str, taste_str = build_taste_profile(conn)

        if args.dry_run:
            log.info(
                "DRY-RUN: would call Sonnet to score "
                f"{len(candidates)} candidates with topics={topics_str!r}"
            )
            for i, c in enumerate(candidates):
                log.info(f"  [{i}] {c[1][:90]}  ({c[2]})")
            return 0

        scored = score_with_sonnet(candidates, topics_str, taste_str)
        if not scored:
            log.error("Scoring returned empty; aborting before any writes")
            return 1

        # Log score distribution for ops visibility
        buckets = {}
        for _, s, _ in scored:
            buckets[s] = buckets.get(s, 0) + 1
        log.info(f"Score distribution: {sorted(buckets.items())}")

        inserted = insert_into_suggested(conn, candidates, scored, dry_run=False)
        log.info(f"Inserted {inserted} into suggested_articles (>= {SUGGESTED_FLOOR})")

        mark_ran_this_week(conn)
        conn.commit()

    log.info("=== economist_weekly_pick end ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
