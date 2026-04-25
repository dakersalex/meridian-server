#!/usr/bin/env python3
"""
Meridian — nightly enrichment retry job.

Phase 2 / P2-3 (PHASE_2_PLAN § 4.1, § 8). Picks up articles that captured
cleanly but never made it past `title_only` enrichment, retries them up to
3 times, and parks any that hit the cap at `status='enrichment_failed'`
with a Tier-3 alert.

Designed to run from cron on the VPS at 02:30 UTC, before the 03:40 UTC
RSS pick. Idempotent: re-running mid-window is a no-op for already-enriched
articles, and per-row retry counts only advance on actual attempts.

Query — articles eligible for retry:
    status='title_only'
    AND saved_at < datetime('now','-24 hours')
    AND url NOT IN (SELECT url FROM unfetchable_urls)
    AND COALESCE(enrichment_retries, 0) < 3
    AND body IS NOT NULL
    AND LENGTH(body) >= 200

The body-length floor matches enrich_article_with_ai's own gate. Articles
with no body (extension body-fetcher hasn't reached them yet) are NOT this
job's territory — they're already visible in /api/health/daily as
`title_only_pending`. Mixing the two failure modes pollutes the
enrichment_failed signal.

For each match:
    - load row, attempt enrichment via enrich_article_with_ai()
    - on success (summary length > 0): set status='enriched', save fields,
      leave enrichment_retries as the count of attempts that ran
    - on failure: increment enrichment_retries
    - if increment hits 3: set status='enrichment_failed' and fire Tier-3 alert

Logs to /var/log/meridian/enrich_retry.log. Touches a heartbeat file
/var/log/meridian/enrich_retry.last_run on every run (success or partial)
so a separate watchdog can alert on absence > 36h (PHASE_2_PLAN § 6 cond. 2).

Exit codes:
    0 — ran to completion (any per-article failures are logged, not fatal)
    1 — fatal (DB unreachable, secrets missing, alert.py missing, etc)

CLI flags:
    --dry-run       List candidates without modifying DB or calling Claude.
    --max N         Process at most N candidates this run (default: all).
    --force-fail ID Bypass enrichment for one article id; treat as failed
                    attempt. Used for P2-5 cap-hit alert verification.
                    Multiple ids may be passed comma-separated.
"""

import os
import sys
import json
import time
import sqlite3
import logging
import argparse
import traceback
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = str(BASE_DIR / "meridian.db")
LOG_DIR = Path("/var/log/meridian")
LOG_FILE = LOG_DIR / "enrich_retry.log"
HEARTBEAT_FILE = LOG_DIR / "enrich_retry.last_run"
RETRY_CAP = 3

# Make `import server` and `import alert` resolve when run from cron.
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def _setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    fmt = "%(asctime)s [%(levelname)s] %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[
            logging.FileHandler(str(LOG_FILE)),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("enrich_retry")


def _heartbeat():
    """Touch the run-marker file so the watchdog cron knows we ran."""
    try:
        HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
        HEARTBEAT_FILE.write_text(datetime.now(timezone.utc).isoformat(timespec="seconds") + "\n")
    except Exception as e:
        # Heartbeat failure is logged but not fatal — main job still ran.
        logging.warning(f"heartbeat write failed: {e}")


def _eligible_candidates(cx, max_n=None):
    rows = cx.execute(
        """
        SELECT id, url, source, title, COALESCE(enrichment_retries, 0) AS tries
        FROM articles
        WHERE status='title_only'
          AND saved_at < datetime('now','-24 hours')
          AND url NOT IN (SELECT url FROM unfetchable_urls)
          AND COALESCE(enrichment_retries, 0) < ?
          AND body IS NOT NULL
          AND LENGTH(body) >= 200
        ORDER BY saved_at ASC
        """,
        (RETRY_CAP,),
    ).fetchall()
    if max_n is not None:
        rows = rows[: int(max_n)]
    return rows


def _save_success(cx, aid, enriched, attempts):
    """Persist a successful enrichment. Mirrors /api/enrich/<aid> behaviour
    plus body/key_points/highlights so Phase-1's three-level reading mode
    still works for retries."""
    cx.execute(
        """
        UPDATE articles
        SET summary=?,
            tags=?,
            topic=?,
            pub_date=?,
            key_points=COALESCE(NULLIF(?, ''), key_points),
            highlights=COALESCE(NULLIF(?, ''), highlights),
            status='enriched',
            enrichment_retries=?
        WHERE id=?
        """,
        (
            enriched.get("summary", ""),
            enriched.get("tags", "[]"),
            enriched.get("topic", ""),
            enriched.get("pub_date", ""),
            enriched.get("key_points", "") or "",
            enriched.get("highlights", "") or "",
            attempts,
            aid,
        ),
    )


def _record_failure(cx, aid, attempts):
    """Bump retry count; if cap hit, mark enrichment_failed."""
    if attempts >= RETRY_CAP:
        cx.execute(
            "UPDATE articles SET enrichment_retries=?, status='enrichment_failed' WHERE id=?",
            (attempts, aid),
        )
        return True
    cx.execute(
        "UPDATE articles SET enrichment_retries=? WHERE id=?",
        (attempts, aid),
    )
    return False


def main(argv=None):
    parser = argparse.ArgumentParser(description="Nightly enrichment retry job")
    parser.add_argument("--dry-run", action="store_true",
                        help="List candidates without writing to DB or calling Claude")
    parser.add_argument("--max", type=int, default=None,
                        help="Process at most N candidates this run")
    parser.add_argument("--force-fail", type=str, default="",
                        help="Comma-separated article IDs to treat as failed (no Claude call). "
                             "Used for cap-hit alert verification.")
    args = parser.parse_args(argv)

    log = _setup_logging()
    log.info("=" * 60)
    log.info(f"enrich_retry start (dry_run={args.dry_run}, max={args.max}, "
             f"force_fail={args.force_fail or 'none'})")
    _heartbeat()

    # Imports deferred so --help works even if server.py / alert.py are missing.
    try:
        import server  # provides enrich_article_with_ai
    except Exception as e:
        log.error(f"could not import server.py: {e}")
        return 1
    try:
        from alert import send_alert
    except Exception as e:
        log.error(f"could not import alert.py: {e}")
        return 1

    force_fail_ids = {x.strip() for x in args.force_fail.split(",") if x.strip()}
    cap_hits = []  # articles that crossed retry cap this run

    try:
        with sqlite3.connect(DB_PATH) as cx:
            cx.row_factory = sqlite3.Row
            cands = _eligible_candidates(cx, max_n=args.max)
    except Exception as e:
        log.error(f"DB query failed: {e}")
        return 1

    log.info(f"candidates: {len(cands)} (cap={RETRY_CAP})")

    if args.dry_run:
        for r in cands:
            log.info(f"  [dry] id={r['id']} src={r['source']} tries={r['tries']} url={r['url']}")
        log.info("dry-run complete — no DB writes")
        return 0

    successes = 0
    failures = 0

    for r in cands:
        aid = r["id"]
        attempts = int(r["tries"]) + 1
        is_forced = aid in force_fail_ids
        try:
            with sqlite3.connect(DB_PATH) as cx:
                cx.row_factory = sqlite3.Row
                row = cx.execute("SELECT * FROM articles WHERE id=?", (aid,)).fetchone()
            if not row:
                log.warning(f"  id={aid} vanished between query and processing — skip")
                continue
            art = dict(row)

            if is_forced:
                log.info(f"  id={aid} FORCE-FAIL (attempt {attempts}/{RETRY_CAP})")
                summary = ""
                enriched = {}
            else:
                log.info(f"  id={aid} attempt {attempts}/{RETRY_CAP} src={art.get('source')}")
                enriched = server.enrich_article_with_ai(art) or {}
                summary = enriched.get("summary", "") if isinstance(enriched, dict) else ""

            with sqlite3.connect(DB_PATH) as cx:
                if summary:
                    _save_success(cx, aid, enriched, attempts)
                    cx.commit()
                    successes += 1
                    log.info(f"  id={aid} OK summary_len={len(summary)}")
                else:
                    capped = _record_failure(cx, aid, attempts)
                    cx.commit()
                    failures += 1
                    if capped:
                        cap_hits.append({
                            "id": aid,
                            "url": art.get("url", ""),
                            "source": art.get("source", ""),
                            "title": art.get("title", "")[:120],
                        })
                        log.warning(f"  id={aid} CAP HIT — status=enrichment_failed")
                    else:
                        log.info(f"  id={aid} FAIL ({attempts}/{RETRY_CAP})")
            time.sleep(0.5)  # gentle pacing — Claude side, not DB side
        except Exception as e:
            failures += 1
            log.error(f"  id={aid} unexpected error: {e}")
            log.error(traceback.format_exc())

    log.info(f"done — successes={successes} failures={failures} cap_hits={len(cap_hits)}")

    # Cap-hit Tier-3 alert (PHASE_2_PLAN § 6 cond. 1).
    if cap_hits:
        try:
            lines = [f"{len(cap_hits)} article(s) hit retry cap and were marked enrichment_failed:", ""]
            for h in cap_hits:
                lines.append(f"  • [{h['source']}] {h['title']}")
                lines.append(f"    id={h['id']}  {h['url']}")
            lines.append("")
            lines.append("Inspect via /api/health/enrichment or "
                         "SELECT * FROM articles WHERE status='enrichment_failed';")
            send_alert(
                f"enrich_retry cap hit — {len(cap_hits)} article(s) failed",
                "\n".join(lines),
                severity="tier3",
            )
            log.info(f"cap-hit alert sent ({len(cap_hits)} article(s))")
        except Exception as e:
            log.error(f"cap-hit alert send failed: {e}")
            # Do NOT fail the run on alert send failure — the DB is already updated.

    return 0


if __name__ == "__main__":
    sys.exit(main())
