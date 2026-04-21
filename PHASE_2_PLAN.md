# Meridian — Phase 2 Plan

**Scope:** Authoritative role migration — VPS becomes the sole production writer. Mac steps back to dev.

**Author:** Alex Dakers
**Date:** 21 April 2026 (Session 65)
**Charter reference:** `CHARTER.md` § 12 (Phase 2), § 6 principles P1/P4/P5/P6, § 8 known fragility, § 9 target architecture.
**Cost reference:** `COST_MODEL.md` § 6 (nothing in Phase 2 changes the cost profile; all changes are structural).
**Status:** v1, Session 65. Revise at Phase 2 close.

---

## § 1 — Objective

End Phase 2 with the following true:

1. VPS is the only system writing to the production DB.
2. All capture paths (Chrome extension, RSS pick, newsletter IMAP, Economist weekly) write to the VPS.
3. The partial-enrichment fragility (§ 8 of charter) has a live structural mitigation, visible observability, and either a testable root-cause hypothesis or a clean Phase-3 handoff.
4. The three-tier deployment posture (P5) and alerting-from-v1 posture (P4) are honoured for every new surface introduced.
5. Rollback to Phase-1 parallel-run is a single launchctl command per plist.

Non-objectives (explicitly out of scope, deferred to P3/P4):
- Briefs, Q&A, learned scoring, prompt caching — Phase 3.
- Daily health email, off-VPS backups, uptime monitoring — Phase 4.
- Mobile PWA polish — Phase 3.
- Shell-bridge filter fix — carried as known ops constraint; not load-bearing for P2.

---

## § 2 — End-state definition

What is true at end of Phase 2, stated precisely enough to test against:

**Mac:**
- `com.alexdakers.meridian.sync.plist` — **unloaded** (`launchctl unload`), file kept on disk for fast rollback, never deleted.
- `wake_and_sync.sh` — archived under `archive/` with a dated suffix. Never executed again. Not deleted (audit trail).
- Mac Flask (`server.py` on port 4242) — **still running** via its existing launchd plist, for the session shell-bridge workflow and local dev. Backed by a non-authoritative DB (see § 3).
- `vps_push.py` — still in repo, but no scheduler calls it. Callable by hand for one-off backfills only.
- Newsletter IMAP sync on Mac — confirmed stopped (either never ran or already disabled in Phase 1; verify at step P2-0).
- Chrome extension v1.x on Mac — repointed to `https://meridianreader.com/api/*`. `localhost:4242` removed as a valid write target.

**VPS:**
- Single canonical `meridian.db` at `/opt/meridian-server/meridian.db`.
- Schedulers own every capture path: RSS pick (already live), newsletter IMAP (already live), Economist weekly (Session-65 decision — see § 7), partial-enrichment retry (new, § 4).
- Existing cron (03:40 + 09:40 UTC) remains.
- Health & Cost panel exposes two new metrics (§ 5).
- Tier-3 alerting wired for the four P2-scoped conditions (§ 6).

**Chrome extension:**
- All writes to `https://meridianreader.com/api/*`. No conditional localhost fallback.
- Auth/cookie/CORS working end-to-end against production domain. Verified with a clipped test article before cutover.
- Re-enabled (currently disabled since Session 63).

**Rollback:**
- Mac plist: `launchctl load ~/Library/LaunchAgents/com.alexdakers.meridian.sync.plist` → wake_sync resumes.
- Extension: one-line flip of `API_BASE` constant → localhost again.
- Both rollbacks are under 2 minutes.

---

## § 3 — Mac's non-authoritative DB

Mac Flask stays running, which requires a DB to serve. Committing to **option A**: nightly read-only snapshot from VPS.

**Mechanism.** A Mac launchd job runs once per night (e.g. 04:00 Geneva, after the VPS 03:40 UTC cron has produced a fresh authoritative DB): take a SQLite-backup-API snapshot on the VPS, `scp` the snapshot to Mac, then `chmod 444` the resulting file. Mac Flask can only read it. Any attempt to write fails at the filesystem layer, not at application logic — belt-and-braces against accidental drift.

**On-demand refresh.** `refresh_mac_db.sh` remains as a manual override — same snapshot + scp + chmod, callable by hand when mid-day freshness is wanted. Compatible with the nightly job.

**Why A, not B (dev-scratch).** The parallel-run friction Phase 2 exists to kill (DB-lock, drift) comes from two *writers*, not two copies. A read-only snapshot on the Mac has zero writers on the Mac side — it's a cache, not a second writer. Option B also failed a use case that actually matters: Mac is genuinely used for offline reading sometimes (plane mode, network flaking), and a fresh-nightly snapshot covers that without reintroducing parallel-run risk.

**Implementation notes.**
- SQLite backup API (`sqlite3 source.db ".backup dest.db"`) for the snapshot, not raw `cp` — avoids grabbing the DB mid-write.
- Mac Flask should tolerate the file replacement; if it doesn't cleanly, wrap the swap in a stop/replace/start in the launchd job.
- `vps_push.py` stays in the repo but is orphaned — no scheduler calls it. Kept callable by hand only for one-off backfills during dev.

---

## § 4 — Partial-enrichment mitigation (P1 capture-reliability)

Per Q2 decision: mitigation first, observability alongside, time-boxed diagnosis third. Phase 3 handoff is only legitimate if all three landed cleanly.

### 4.1 — Mitigation: nightly retry job (ships FIRST)

**Location:** VPS, new script `/opt/meridian-server/enrich_retry.py`. Cron entry `30 2 * * *` (02:30 UTC daily, runs before 03:40 RSS pick to avoid overlap).

**Query:** articles `WHERE status='title_only' AND saved_at < datetime('now','-24 hours') AND url NOT IN (SELECT url FROM unfetchable_urls)`.

**Behaviour:**
- For each match, call the existing `/api/enrich/<id>` path.
- Track retry count in a new column `enrichment_retries INTEGER DEFAULT 0` on the `articles` table.
- Cap at **3 retries**. On cap hit, set `status='enrichment_failed'` and emit a Tier-3 alert (§ 6).
- Idempotent: running the script twice in a window is a no-op.
- Logs to `/var/log/meridian/enrich_retry.log`.

**Size:** ~30 lines Python + one schema migration for the column.

### 4.2 — Observability: Health & Cost panel metric

**New metric on the panel:** "Articles needing retry to enrich" — count of `status='title_only' AND saved_at < 24h ago`.

**Secondary metric:** "Articles permanently failed enrichment" — count of `status='enrichment_failed'`.

**Purpose:** The trend over weeks tells us whether the mitigation covers the symptom or whether root-cause work is needed. If the first metric trends toward zero, the retry job is eating the problem. If the second grows, root cause is still alive.

**Delivery:** Extend existing `/api/health/enrichment` endpoint with these two counts; add panel tiles. Ship alongside the retry job.

### 4.3 — Diagnosis: one 60-minute session

**Hard time box:** 60 minutes within a future session (not Session 65).

**Exit criteria — exactly one of:**
- (i) Testable root-cause hypothesis, implementable in the next single session.
- (ii) "Deferred to Phase 3 with mitigation live + observability collecting data." Documented in NOTES.md with a named trigger for revisit (e.g. "revisit if metric 4.2.a exceeds 20 articles/week for two consecutive weeks").

**No open-ended poking.** If hour one ends without (i) or (ii), default to (ii).

### 4.4 — Alerting

Ship with the retry job (P4: no panel without an alert). Tier-3 alert fires when:
- Any article crosses the retry cap and lands at `enrichment_failed`.
- The nightly retry job itself fails (non-zero exit, or doesn't run for > 36h).

See § 6 for alert plumbing.

---

## § 5 — Chrome extension re-enablement

Extension has been disabled since Session 63. Re-enablement is **in scope of Phase 2 execution**, but not of this planning session.

### 5.1 — Precondition for cutover (gate 1 of 3)

Extension must write end-to-end to `https://meridianreader.com/api/*` before Mac authority is dropped. Specifically:
- Clip one real article from a browser tab → lands on VPS DB → visible in the VPS Feed.
- Bookmark sync (FT saved, Economist bookmarks) → articles land on VPS.
- Unfetchable detection still works against VPS endpoints.
- CORS + auth + cookies confirmed working for all four write endpoints the extension currently targets.

### 5.2 — Scope of extension changes

- `API_BASE` constant → `https://meridianreader.com`.
- Remove localhost fallback branches (they become noise once the prod path is real).
- Manifest `host_permissions` → include `https://meridianreader.com/*` if not already.
- Version bump (v1.8) so Chrome actually reloads the background script.

### 5.3 — Non-scope

- No new extension features in Phase 2. Any feature additions (bulk import UX, MUST #14) are separate work.

### 5.4 — Testing

Before declaring gate 1 green, execute a documented test script against a staging article. Script lives at `test/extension_prod_smoketest.md`.

---

## § 6 — Alerting (P4, ships with every new surface)

Tier-3 alert conditions introduced by Phase 2. All route via the same channel — sendmail from the VPS to Alex's iCloud address. **A working skeleton alert must ship in Phase 2**, not a TODO. Pushover and other channel upgrades are explicitly a Phase 4 concern.

Conditions:
1. Nightly enrich_retry hits the retry cap on any article.
2. Nightly enrich_retry fails to run for > 36 hours.
3. Chrome extension prod write fails at a rate > 10% over a rolling 24h window (requires logging extension POSTs to a small table on VPS).
4. Cost alert — projected monthly spend > $20 (deferred to Phase 4 per charter, flagged here so it doesn't get orphaned).

Alerting infrastructure for Phase 2:
- One VPS script `/opt/meridian-server/alert.py` — takes severity + message, fires via sendmail.
- Called by each condition above.
- Deliberately crude. This satisfies P4's "crude panel with a working alert > sophisticated panel with none."

**Event-driven vs digest.** This is event-driven alerting, not a daily digest. A daily "heartbeat" summary email is a Phase 4 concern (see § 11 Phase 3 handoff). Absence of Tier-3 alerts is the positive signal in Phase 2. The in-app stats panel (extended in § 4.2) covers pull-mode status checking; Tier-3 alerts cover push-mode failure notification. Both are needed because they serve different failure modes — the panel for when I'm looking, the alert for when I'm not.

---

## § 7 — Economist weekly scraper (open sub-question)

**Current state:** Mac Playwright, Thursday 22:00 UTC, called by `ai_pick_economist_weekly()` in server.py's internal scheduler. Must relocate or replace before Mac write authority is dropped.

**Four options:**
- (α) Port to Chrome extension alarm — **rejected.** Still Mac-bound (extension runs in Alex's Chrome). Doesn't achieve the VPS-authoritative end state.
- (β) Port to VPS Playwright — **likely rejected.** Cloudflare blocks headless Chrome on VPS; Session 63 notes confirm this has been the blocker throughout.
- (γ) Keep on Mac as named exception — acceptable fallback. Carries one explicit Mac production role into Phase 3. Requires updating charter § 9 diagram text to note the exception.
- (δ) Replace with source-bookmark bulk import (MUST #14) — **recommended starting point.** MUST #14 exists precisely for Cloudflare-blocked sources. The extension's Economist bookmark sync already works (Session 62 v1.7). Weekly AI-pick can run over articles ingested via bookmark sync, rather than scraping fresh candidates.

**Plan:** attempt δ first. Concretely:
- On the VPS, a weekly scheduled job queries articles ingested from Economist in the last 7 days, runs the existing `ai_pick` scoring, surfaces top N to the Suggested swim lane.
- If the candidate pool is consistently too thin to produce good picks (e.g. < 15 candidates per week), fall back to γ — keep the Mac Playwright job, document it in charter § 9 as a named exception, revisit in Phase 3.

**Decision point:** after 2 weeks of running under δ. If AI picks stop surfacing Economist articles or quality visibly drops, fall back to γ.

**Not doing in Phase 2:** building a new VPS-side Economist fetcher. That's a Phase 3 concern if δ fails.

---

## § 8 — Execution plan (ordered)

Eleven steps. Each has an estimated slot, a success criterion, and a rollback. Grouped into six tier-classified deploy blocks.

### Block 1 — Preconditions (Tier 2, anytime, ~1 session)

**P2-0 — Baseline check.**
Confirm Mac IMAP sync is stopped; line-by-line diff Mac `wake_and_sync.sh` vs VPS `wake_sync_vps.sh` to catch anything missed in Session 63.
*Success:* diff produced, any gaps listed explicitly.
*Rollback:* n/a — read-only.

**P2-1 — Alerting skeleton.**
Ship `/opt/meridian-server/alert.py` with sendmail-based email. One dummy test alert fires end-to-end.
*Success:* test alert arrives in Alex's iCloud inbox.
*Rollback:* remove script; no callers yet.

**P2-2 — Schema migration: `enrichment_retries` column.**
ALTER TABLE on VPS (and Mac dev DB) adding the column with DEFAULT 0.
*Success:* column present on both; all existing rows NULL-safe.
*Rollback:* DROP COLUMN (SQLite: recreate table — prep rollback SQL alongside migration).

### Block 2 — Mitigation & observability (Tier 2, anytime, ~1 session)

**P2-3 — Enrich retry job.**
`/opt/meridian-server/enrich_retry.py` written, deployed, cron entry added. Cap at 3 retries.
*Success:* dry-run against current title_only backlog produces expected candidate list without actually re-triggering; then live run.
*Rollback:* comment the cron line; script does nothing.

**P2-4 — Health panel metrics.**
Extend `/api/health/enrichment`; add two panel tiles.
*Success:* tiles render on Mac Flask dev view and on VPS production view.
*Rollback:* revert `meridian.html` via git; endpoint extension is additive.

**P2-5 — Wire enrich_retry alerts.**
Conditions 1 and 2 from § 6 fire via `alert.py`.
*Success:* forced failure fires the alert.
*Rollback:* remove alert calls from `enrich_retry.py`.

### Block 3 — Diagnosis (Tier 2, anytime, ~1 session)

**P2-6 — Partial-enrichment diagnosis session.**
60-minute hard-timebox. Output: either (i) testable hypothesis, or (ii) Phase-3 handoff note in NOTES.md with revisit trigger.
*Success:* exit criterion documented. Not "we understand it."
*Rollback:* n/a — investigation only.

### Block 4 — Extension prod cutover (Tier 1, weekend, ~1 session)

**P2-7 — Extension repoint.**
Update `API_BASE`, remove localhost fallback, bump to v1.8, reload in Chrome.
*Success:* smoketest script (§ 5.4) all green.
*Rollback:* one-line flip of `API_BASE`, reload.

**P2-8 — Extension write-failure logging + alert (§ 6 condition 3).**
Tiny endpoint on VPS that the extension reports failures to; alert fires over threshold.
*Success:* forced failure fires the alert.
*Rollback:* remove endpoint and alert call.

### Block 5 — Authority cutover (Tier 1, weekend, ~1 session — same or next weekend as Block 4)

**P2-9 — Economist scraper: option δ in place.**
VPS weekly job querying recent Economist ingestion and running ai_pick. Two-week observation window starts.
*Success:* first weekly run produces picks of visibly reasonable quality.
*Rollback within Block 5:* Block 5 rolls back as a unit. P2-10 drops Mac write authority immediately after P2-9, so "revert P2-9 alone" is not coherent once Block 5 begins landing — re-enabling `ai_pick_economist_weekly()` on Mac while Mac's scheduler is unloaded changes nothing. The Block 5 commit is atomic: either both P2-9 and P2-10 land, or both revert (re-load Mac scheduler plist AND re-enable Mac `ai_pick_economist_weekly()`). If δ proves unsound after Block 5 has fully landed, the remedy is the δ→γ fallback in § 7, not a Block 5 rollback.

**P2-10 — Mac write authority dropped.**
`launchctl unload com.alexdakers.meridian.sync.plist`; archive `wake_and_sync.sh`; write `refresh_mac_db.sh`; snapshot Mac DB first for paranoia.
*Success:* next VPS scheduled run is the only production write; Mac DB can be refreshed on demand without breaking Mac Flask.
*Rollback:* `launchctl load` the plist; wake_sync resumes. Mac DB is a snapshot, so no data loss even if rollback delayed.

### Block 6 — Close (Tier 2)

**P2-11 — Charter review + Phase 2 retrospective.**
Re-read CHARTER.md § 11 (revision protocol). Decide: any MUSTs drifted? Any NICE promoted silently? Does § 9 diagram need the Economist-exception update? Update NOTES.md with Phase 2 close entry.

---

## § 9 — Time budget

Rough session count, each ~1–2h:

| Block | Sessions | Notes |
|---|---|---|
| 1 Preconditions | 1 | Mostly investigation + alerting skeleton |
| 2 Mitigation + obs | 1 | Biggest code chunk; schema mig + retry job + panel |
| 3 Diagnosis | 1 (60-min timebox) | Can be tail of another session |
| 4 Extension cutover | 1 (weekend, Tier 1) | |
| 5 Authority cutover | 1 (weekend, Tier 1) | |
| 6 Close | 0.5 | |

**Total: ~5 sessions, 6–9 hours wall time.**

Blocks 4 and 5 are both Tier 1 — P5 says weekends only. If both fit on one weekend, fine; otherwise split across two. Do not stack a Tier 1 onto a weekday evening.

---

## § 10 — Risk register

Named risks specific to Phase 2. Each has a mitigation stated.

| # | Risk | Mitigation |
|---|---|---|
| R1 | Extension CORS/auth breaks against production domain in ways not visible on localhost | Gate 1 smoketest is the whole point; don't skip |
| R2 | Mac DB snapshot during cutover is incomplete/corrupt, rollback is compromised | Take the snapshot via SQLite backup API, not file copy. Verify integrity before proceeding |
| R3 | VPS cron overlap between 02:30 enrich_retry and 03:40 RSS pick | 70-minute gap is comfortable; keep job times fixed and documented |
| R4 | Economist δ option produces too few candidates, weekly picks dry up | 2-week observation window + documented fallback to γ |
| R5 | Partial-enrichment diagnosis runs over the 60-min box | Hard stop at 60; default to option (ii) Phase-3 handoff. Treat this as a bright line |
| R6 | Shell-bridge filter silently eats output during cutover work | Known issue; route all observations through `~/meridian-server/logs/output.txt` as currently practised |
| R7 | launchd double-spawn (Phase 1 recurrence) bites during cutover | Mac Flask is staying running; if it enters crash loop, kill the orphan by PID, wait 10s, reinject bridge. Pattern known, not new |
| R8 | Anthropic cost spike during enrich_retry backfill (hundreds of re-enrichments at once) | First run is throttled/capped; review cost panel after first live run before clearing throttle |
| R9 | Session 63's git-history cleanup sandbox at `~/meridian-server-sandbox` (removes leaked app password + 22k-file Chrome profiles from history, reduces repo from 748 MB to 44 MB) remains pending | Not Phase-2-scoped. Decision required before Phase 3: force-push, abandon, or keep deferring. Flagging here so it doesn't rot |

---

## § 11 — Phase 3 handoff shape (advance notice)

Things Phase 2 should hand cleanly to Phase 3:

- Enrichment retry observability collecting ≥ 2 weeks of data, ready to inform root-cause decisions.
- Economist option δ decided (either proven or failed back to γ), so Phase 3 isn't re-litigating it.
- Alerting skeleton (`alert.py` + sendmail) in place, so Phase 4 can upgrade channels without writing from scratch.
- Mac firmly in a dev-only posture, so Phase 3's synthesis-layer work can develop on Mac, deploy to VPS, without parallel-run worries.
- Charter § 9 diagram updated if Economist exception (γ) is the outcome.

Things deliberately **not** pre-committed to Phase 3: brief persistence details, prompt-caching architecture, retrieval index schema, preference-vector format. All open per charter § 10.

---

## § 12 — Open questions for Phase 2 execution

**O1 — Economist δ vs γ.** Decided at ~2 weeks into Block 5. No earlier commitment.

**O2 — Alert channel upgrade.** sendmail is the Phase 2 default. Pushover / APNs push / Telegram deferred to Phase 4. No decision needed now.

**O3 — Refresh-Mac-DB cadence.** Nightly + on-demand per § 3 (option A). No Phase 2 blocker.

**O4 — Retry cap value (§ 4.1 uses 3).** Arbitrary starting point. May need tuning once live data accumulates. Treated as a tunable, not a decision.

**O5 — Weekend choice for Blocks 4 and 5.** No commitment in plan. Scheduled at session time, honouring P5.

---

*End of Phase 2 plan v1.*
