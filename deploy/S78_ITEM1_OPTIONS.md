# Item 1: Mac Playwright path — three architectural options

**Status:** Surfaced in S78, not decided. Read at fresh energy and decide in S79.

**Why this matters:** Item 1 gates items 3 (FA `_discover_latest_issue` parser fix), 6 (verify scraper write path), and 7 (refresh Eco/FA cookies). Whichever architecture lands, those three items either become trivial follow-ups, change shape, or vanish.

**The path under question:** the Mac-side Playwright scrapers — full-issue scrape for The Economist and Foreign Affairs, bookmarks-page scrape for FT. They run inside cookied Chromium contexts on the Mac (`ft_profile/`, `economist_profile/`, `fa_profile/`), driven by Playwright via Chrome DevTools Protocol. Pre-Block 5 they were triggered by the `wakesync` launchd job; post-Block 5 the trigger was unloaded but the path itself still exists in `server.py` (the threading scheduler in `_eco_weekly_runner` and similar) and runs whenever Chrome launches and the Flask Timer fires.

**What's wrong with it right now (from S77 final addendum):**
- Eco CDP connection died 30 April 22:00 (`eco_cdp_status: DOWN:2026-04-30 22:00` in `kt_meta`).
- FA `_discover_latest_issue` returns the wrong issue (March/April /105/2 instead of May/June /105/3) and has a hardcoded `/2026/105/2` fallback at server.py:1007.
- Section-page pollution still active (`/the-world-this-week/` URLs ingested as articles).
- 30 April 23:58 Flask restart loop suggests the scheduler-on-startup path can crash Flask itself.
- Post-relaunch tab activity in S77 produced zero DB writes (cause unclear: scrapers found nothing vs. scrapers wrote nothing vs. body-fetcher running on already-current articles).
- Of the ~70 articles in the 2 May Eco issue, ~14 made it into the DB (~20% capture rate).

**The three options as outlined in the S77 addendum:**

---

## Option A — Keep on Mac, fix the trigger

Stay where we are architecturally. Fix the cron / launchd trigger so Playwright runs reliably. Fix the parser bugs (item 3). Fix the section-page filter (item 4). Refresh cookies as needed (item 7). The Mac-side cookied browser profiles continue to be the source of authenticated full-issue scrape.

**What changes:**
- Decide a new Playwright trigger model. Not the unloaded `wakesync` (Block 5 retired that for a reason). Options: a fresh launchd cron job that simply runs scrapers on schedule (decoupled from `wake_sync_vps.sh` entirely); a wake-on-Chrome trigger via the extension; manual-only (Alex clicks Sync Bookmarks).
- Fix `_discover_latest_issue` (item 3) and remove `/105/2` fallback.
- Add `/the-world-this-week/` filter (item 4).
- Investigate 30 April Flask restart loop (item 5) — this becomes load-bearing in Option A because scheduler-on-startup is the trigger surface.
- Verify scraper write path (item 6) — also load-bearing here.

**What stays:** Mac is the scrape origin. VPS continues as the canonical write source via the existing `vps_push.py` after each Mac-side scrape. Cookied profiles stay on Mac. Login refresh is interactive on Mac (Chrome, browser, type password).

**Strengths:**
- Cookie refresh is interactive — Alex types the password in a real Chrome window. No headless 2FA workarounds. No "can the VPS hold a session" question.
- Mac browser profiles already exist and have working FA login (confirmed S77).
- Lowest delta from current state. No new infrastructure.
- Preserves the path that built the existing 434-article Eco corpus.

**Weaknesses:**
- Mac availability becomes load-bearing for ingestion. Laptop closed = no scrape. Laptop sleeps = no scrape. This is the underlying reason Block 5 moved the AI pick to VPS — and it's the reason "scrapers" have been intermittent since 19 April.
- The Mac→VPS push step (`vps_push.py`) is another moving part. Net: Mac scrape → push → VPS write. Two failure surfaces.
- Trigger reliability is the recurring failure mode. We've been through it: `wake_and_sync.sh` had a CDP race; new trigger model has to avoid the same. Item 5 (Flask restart loop) suggests the scheduler-on-startup pattern is itself fragile.
- Profile lock window stays. Manual Playwright work during sync windows still risks profile-cookie-less-copy bug (per userMemories rule).

**Effort:** Moderate. Items 3, 4, 5, 6, 7 all need to be done. ~3–5 sessions to get scrapers demonstrably reliable + pass trust audit.

**Failure modes if it doesn't work:** stuck back where we are now — intermittent scrapes, unclear capture rate, periodic CDP/Flask anomalies. Drift back toward Option C in slow motion.

---

## Option B — Move Playwright to VPS with virtual-display Chrome

Migrate the scrape origin from Mac to VPS. Run Chromium headlessly (or in Xvfb) on the Hetzner box. Re-establish FT/Eco/FA logins inside that VPS-side browser context. From then on, scrapes are triggered by VPS cron (not Mac launchd, not Flask threading.Timer), write directly to the VPS DB (no Mac→VPS push), and are independent of laptop state.

**What changes:**
- Stand up Chromium + Xvfb (or playwright-headless) on the VPS. Hetzner instance is small (already running Flask + RSS picker + cron jobs); needs sizing review.
- Bootstrap FT/Eco/FA cookied profiles on the VPS. This is the hard part — it's a one-time auth setup that has to survive long-running cookie refresh.
- Cookie expiry strategy: when an Eco/FA session lapses on the VPS, how does Alex re-authenticate? Manual cookie-string paste from a desktop browser? Periodic SSH-tunnel to a VPS-side X session? Token-refresh API where one exists (FT)?
- Item 3 (FA parser) still needed but lands in the VPS-side scraper code, not Mac.
- Item 4 (section filter) still needed, same code path on VPS.
- Items 5, 6 (Flask restart loop, write path verification) become moot — the scrape path moves off the Mac Flask process entirely.
- `vps_push.py` retires (no Mac→VPS push needed if VPS does its own writes).
- Mac retains: extension manual save (Path 1), extension Sync Bookmarks (Path 4), and the body-fetcher (also extension-side). Mac becomes a pure consumer.

**Strengths:**
- Eliminates Mac availability dependency. Laptop state stops mattering for ingestion.
- One write surface (VPS), not two. Aligns with Block 5's "VPS-as-write-source" direction. Architecturally cleaner.
- Trigger reliability is just VPS cron, which we've already proven works for `wake_sync_vps.sh`, `enrich_retry.py`, and (post-S78) the Block 5 weekly cron.
- Profile lock issue disappears — Mac never holds the FT/Eco/FA profiles for scraping.
- Future scaling: if Bloomberg or other sources are added later, they all live in the same VPS-side Chromium farm.

**Weaknesses:**
- Cookie refresh is the open problem. FT/Eco/FA all use session cookies that expire. Without an interactive Chrome window, refresh is non-trivial. Three sub-options exist (cookie-string paste from desktop, SSH-X session, partial token refresh API where available) and none are obviously clean.
- Bootstrap cost is significant: setting up Xvfb-Chromium that survives cookie wall on three publisher sites, including any anti-bot detection that's lighter on a real desktop than on a Hetzner IP.
- Hetzner IP is server-pool ASN — Cloudflare bot-detection on Eco specifically may be more aggressive against it than against Alex's residential IP. Bot-detection arms race is one of the reasons Path 3 was originally on the Mac.
- Migration is a multi-session project: bootstrap chromium, bootstrap profiles, port scraper code paths, port discovery logic (item 3), port section-page filter (item 4), test under each cookie state, verify capture rate matches Mac path, switch trigger, retire Mac-side scrapers. ~5–10 sessions estimate.
- Single point of failure on cookie expiry — if Alex doesn't refresh in time, all three sources go dark on the same VPS, with no Mac-side fallback.

**Effort:** High. Bootstrap is the bulk of it. Once running, ongoing maintenance might be lower than Option A.

**Failure modes if it doesn't work:** half-migrated state — VPS-side scraper for one source works, the other two don't, Mac-side scrapers half-retired. Worse than either A or C until fully landed. The migration has to land all three sources or revert.

---

## Option C — Drop Playwright entirely

Retire the Mac Playwright path completely. Accept that ingestion comes from RSS-driven AI pick (Path 2, working twice-daily), Chrome extension manual save (Path 1), Chrome extension Sync Bookmarks (Path 4, manual-trigger), newsletter sync (Path 5), and body-fetcher enrichment.

**What changes:**
- Delete `eco_weekly_scraper.py`, FA scraper code path, FT bookmarks scrape code paths from server.py.
- Remove the threading.Timer scheduler that triggers them (resolves item 5 by deletion).
- Items 3, 4, 6, 7 vanish — no scrapers to fix, no parser to repair, no write path to verify, no cookies to refresh.
- Capture coverage falls back to whatever RSS + manual + sync-bookmarks gives. From the S77 capture-rate finding: RSS path was keeping inflow alive on its own.
- Trust audit (item 8) becomes load-bearing in a different way: it's the test of whether RSS + manual + Sync-Bookmarks alone catches enough. If the audit shows it doesn't, the choice is either to add discovery features (currently deferred) or to revisit Options A/B.

**Strengths:**
- Simplest. Largest reduction in moving parts. Lots of code deletion.
- Eliminates the entire class of CDP, profile-lock, scheduler-restart-loop, cookie-expiry-on-Mac problems. Items 3, 4, 5, 6, 7 collapse.
- Ingestion model becomes: RSS for breadth, manual+Sync-Bookmarks for what RSS misses, AI scoring at curation step. Aligns with the Tuesday "curated capture, not comprehensive ingest" decision.
- Body-fetcher (post-S78 fix) handles the FT/Eco/FA articles that come through extension or RSS path.

**Weaknesses:**
- Foreign Affairs has no usable RSS feed. FA capture drops to whatever Alex manually bookmarks on `foreignaffairs.com/my-foreign-affairs/saved-articles` plus what the extension's Sync Bookmarks pulls. Issue-page coverage (the auto-pull-every-article-from-the-current-issue model) goes away.
- The Economist RSS only surfaces a subset of weekly issue content. Full-issue-of-70-articles capture goes away — back to the ~14-of-70 RSS rate, but consciously chosen rather than accidentally.
- The Tuesday architectural decision said "AI track must be a safety net for busy days" requiring "comprehensive-enough source pool." RSS alone may not be that pool, especially for FA. This may foreclose Option C unless the Sync-Bookmarks path is much more comprehensive than current evidence suggests.
- Conscious narrowing of inflow. Trust audit (item 8) gets done after the deletion, not before — uncomfortable, but the alternative is keeping broken code "just in case."

**Effort:** Low. Code deletion + scheduler removal + a trust audit pass. ~1–2 sessions.

**Failure modes if it doesn't work:** trust audit reveals coverage holes you actually care about. Then you either revisit B (full migration) or accept the holes and add discovery features later. There's no half-state — the deletion is the deletion.

---

## What's actually being decided

Three different bets on what's load-bearing for Meridian's value:

- **A bets** that comprehensive scraping matters and the Mac Playwright path can be made reliable. Pays off if items 3–7 land cleanly and the trust audit confirms the captured corpus is what Alex wants.
- **B bets** that comprehensive scraping matters AND the Mac is the wrong place for it. Pays off if VPS-side cookied browsing works in practice for at least Eco and FA, and the cookie-refresh story has a clean answer.
- **C bets** that comprehensive scraping doesn't actually matter — that RSS + extension paths are enough for what Alex reads, and the audit will confirm it.

The Tuesday "AI track as safety net for busy days" decision puts pressure on the source pool being comprehensive. That pressure cuts against C and toward A or B. But it doesn't decide between A and B — that decision turns on Mac-vs-VPS as the right place to hold authenticated browser sessions, which is a real tradeoff with no obvious right answer.

## Pre-S79 reading

To make the decision well, three things would help:
1. **Issue-coverage diagnostic on the 2 May Eco issue.** Of the ~70 URLs in `/weeklyedition/2026-05-02`, how many are in the DB? S77 estimated ~14. A proper count tells you what RSS alone delivered (Option C's floor) vs. what full-issue scrape would add (Options A/B's ceiling).
2. **FA RSS scope check.** Does FA publish an RSS feed at all that the AI picker pulls? If yes, what % of issue articles does it cover? If no, how does FA inflow currently work — is it 100% manual?
3. **VPS sizing.** How much headroom on the Hetzner instance for a Xvfb-Chromium process? Quick `htop` / `free -h` check tells you whether Option B is even feasible without a VPS upgrade.

None of these need to happen tonight. They're the reading material for opening S79 cleanly.
