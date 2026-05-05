# S79 Session brief — Meridian

I'm starting Session 79 of my Meridian project. I wrote this brief myself at the end of S78 to give you full context. Standard startup applies — please proceed normally.

Before any prose response, run tool_search three times: filesystem write, chrome browser tabs, shell bash. Only then read NOTES.md.

Read NOTES.md and run the standard startup sequence. Read the S78 entry IN FULL — that's where items 2 + 9 outcomes, the gitignore amendment, and the surfaced-but-undecided item 1 summary live.

**S79 scope:** Item 1 architectural decision (Mac Playwright path), then whatever items 3–7 reshape into based on that decision. Tier-2. This is fresh-energy conversation work — I deferred this from S78 deliberately because it's load-bearing and shouldn't happen tail-end of another session.

**Time-box:** I'll choose at session start, typical 90–120 min. 75% flag at 75% of agreed length.

**Pre-flight (read-only, mandatory):**

1. VPS `/api/health/daily` should be `ok=true` or `ok=false` on info/warning only.
2. extension_write_failures last 24h should be 0–2. Column is `timestamp`, not `saved_at_ms`.
3. Three SHAs aligned. S78 final commit was `b0d6e5ca` (or whatever the session-close commit is — see below). What matters is Mac == VPS == origin.
4. Working tree state. Expect clean. If dirty in production files (server.py, meridian.html, manifest.json) — STOP, that's unexpected drift since S78.
5. Block 5 systems still operating: wakesync should be unloaded, refresh launchd job should be loaded, Mac DB should be chmod 444.
6. Did the nightly Mac refresh fire on 6 May 04:00 Geneva and 7 May 04:00 Geneva? Check `~/meridian-server/logs/refresh_mac_db.log` for entries on those dates.
7. **Did the Block 5 Friday cron fire on 8 May 13:15 UTC?** Check `/var/log/meridian/economist_weekly.cron.log` on VPS. This is the FIRST run on the new schedule (Thursday → Friday change landed S78). If the file is still empty on/after 8 May, that's a problem worth investigating before any architectural work.
8. Body-fetcher pending list: should be 1 article (the FT one), not 9. Confirms the S78 server-side filter is still doing its job and that no new long-tail-domain articles have been queued. If count > 1 and includes non-FT/Eco/FA/Bloomberg hosts, the host_clause may need to be widened.
9. Confirm the 8 articles from S78 are still status `unfetchable` (not flipped back). One-shot SQL was permanent but worth a sanity check.

**The single load-bearing decision:** which of three options to take for the Mac Playwright path. Read `deploy/S78_ITEM1_OPTIONS.md` IN FULL. The doc closes with three pre-S79 diagnostic reads (~30 min total) that would inform the decision but aren't required. Recommend running them BEFORE deciding:
1. **Issue-coverage diagnostic on the 2 May Eco issue.** Of the ~70 URLs in `/weeklyedition/2026-05-02`, how many are in the DB? Tells you Option C's floor vs. Options A/B's ceiling.
2. **FA RSS scope check.** Does `rss_ai_pick.py` pull a FA RSS feed at all? If yes, % of issue articles covered? If no, FA inflow is currently 100% manual.
3. **VPS sizing.** `htop` / `free -h` / `df -h` on Hetzner. Tells you whether Option B (Xvfb-Chromium on VPS) is feasible without a VPS upgrade.

These are read-only, no Tier-2 work. ~10 min each.

**After item 1 decision lands:** items 3, 4, 5, 6, 7 reshape based on the choice:
- **If Option A (keep Mac, fix trigger):** all five items in scope. Sequence them. Item 5 (Flask restart loop investigation) becomes load-bearing because scheduler-on-startup is the trigger surface.
- **If Option B (move to VPS):** items 3, 4 port to VPS-side scraper code. Items 5, 6 become moot. Item 7 reshapes around VPS-side cookie refresh. Major migration, multi-session.
- **If Option C (drop entirely):** items 3–7 collapse via code deletion. Item 8 (trust audit) becomes the next session's main work.

**S79 priority list (post-item-1 decision):**

1. (Conditional) Run pre-S79 diagnostic reads.
2. Item 1 decision.
3. Items 3–7 sequenced according to decision.
4. Item 8 trust audit (if Option C lands quickly enough).
5. Item 9 Part B (manifest.json widen) — only if item 1 decision suggests long-tail domains will keep arriving.
6. δ→γ observation window restart decision — conditional on items 1 + scrapers fixed + first clean Friday cron run.

**Standing approvals (read-only diagnostic, no need to ask):**

- All read-only Mac and VPS queries (sqlite3 SELECT, ls, cat, grep, log show, stat, launchctl list, systemctl list-timers)
- ast.parse() and bash -n syntax checks
- Reading any file under /opt/meridian-server/ via ssh
- Reading Mac logs in ~/meridian-server/logs/
- Reading kt_meta values
- Reading the three pre-S79 diagnostic outputs (Eco issue page contents, FA RSS feed, VPS sizing)

**Standing approvals (Tier-2 work, ask me first in chat):**

- crontab edits on VPS
- server.py patches via str_replace inside ~/meridian-server/ (NEVER edit VPS server.py directly — patch Mac, run deploy.sh)
- Running deploy.sh after a server.py patch
- Restart Flask via SSH (NEVER via the shell endpoint — that kills the process serving the request)
- Manually triggering a single scraper run for testing, IF and ONLY IF I've explicitly chosen "verify scraper write path" as in-scope
- Code deletion if item 1 lands as Option C — review what's being deleted before doing it

**Hard rules:**

- Don't touch server.py, meridian.html, or manifest.json without explicit chat approval for that specific change. Show the proposed patch, get "yes do it," then patch + ast.parse + deploy.
- Don't make architectural decisions on my behalf. Item 1 is mine to decide. Surface tradeoffs, let me choose. The S78 doc is already written — read it, don't rewrite it.
- Don't run scrapers as casual experiments. If a scraper run is needed for verification, it's a deliberate setup with explicit approval.
- Don't execute deploy.sh without my go on a specific patch.
- Don't push to origin/main without my explicit confirmation.
- Don't restart the δ→γ observation window unless I explicitly decide it should restart now. Default is "still paused."
- If running pre-S79 diagnostics, don't synthesize a recommendation — just report numbers.

**Recommended session structure:**

- Phase 1 (10–15 min): Pre-flight + scoping. Run the 9 pre-flight checks. Surface results. Ask me whether to run the three pre-S79 diagnostics.
- Phase 2 (if pre-S79 diagnostics in scope, 30 min): Run the three reads. Report numbers, no recommendation.
- Phase 3: Item 1 decision conversation. Surface tradeoffs from `deploy/S78_ITEM1_OPTIONS.md` (don't rewrite, just summarize key contrasts). Let me decide.
- Phase 4: Items 3–7 reshape based on decision. Pick an in-scope subset.
- Phase 5: Close. Update NOTES.md with S79 entry. Commit + push. Update δ→γ status.

**Interrupt me for:**

- Pre-flight failure (especially items 6, 7, 8, 9 — those are new since S78)
- Friday 8 May cron didn't fire (item 7 above)
- Body-fetcher queue grew from 1 to >1 with new long-tail domains (item 8 above)
- Any production file modification surfacing
- 75% time flag hit
- Architectural decision about to be made without my explicit input

Default if you don't know: stop and ask me. S79 is conversation-driven, not autonomous.

**When done:**

- Working tree dirty in well-understood ways or fully committed
- NOTES.md S79 entry written
- S80 prompt drafted at deploy/S80_PROMPT.md if items remain
- δ→γ status updated in NOTES (still paused / restart with new dates)

**My first action when handed back:** `git status` and `cat ~/meridian-server/NOTES.md | head -50`
