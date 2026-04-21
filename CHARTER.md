# Meridian — Charter

**One-sentence purpose:** Meridian exists to help me absorb the daily torrent of news from FT, *The Economist*, and *Foreign Affairs* with less time and less noise than reading them directly, while building a private queryable corpus of what I've read.

**Author:** Alex Dakers (sole user, sole developer)
**Date:** 21 April 2026 (Session 64)
**Status:** Living document. Revise at each migration phase boundary.

---

## § 1 — Purpose

Meridian exists to help me absorb the daily torrent of news from a small set of trusted sources — primarily the *Financial Times*, *The Economist*, and *Foreign Affairs* — with less time and less noise than reading them directly.

It is a personal tool. It captures what I read into a private, queryable corpus so that I can later generate briefings on any topic it has covered, ask specific questions against the body of material it holds, and — over time — have it learn what I actually engage with so relevant articles surface without manual hunting. It should also help me avoid missing news worth seeing, by pulling a small number of trusted sources into one place rather than scattering my attention across their native apps.

It is explicitly *my* tool. Not a product, not a service, not shared. Its value is measured in my time reclaimed and my confidence that the system is doing what it can to surface what matters.

---

## § 2 — User & context

Meridian has one user: me. Solo developer, solo reader, no other audience. I am a paying subscriber to all three primary sources (FT, *Economist*, *Foreign Affairs*), and the tool's value is strictly additive to those subscriptions — it does not replace them, it makes them more tractable. Meridian is personal, not a work tool — reading for general knowledge and interest, not for client or research use.

Reading happens wherever I am: desktop at home, phone on the sofa, iPad at lunch, work browser between tasks, occasionally on weekends away from any laptop. Weekend usage is heavy. Mobile usage is not a fallback for broken desktop access — it is a primary, daily context, particularly on iPad in the evening.

---

## § 3 — The problem Meridian solves

Reading three subscriptions natively has three persistent costs:

- **Time cost.** Each source's native app has its own layout, own ordering, own sense of what today's news is. Moving between them is slow, duplicative, and rewards the publisher's priorities over mine.
- **Coverage risk.** The more sources I maintain, the easier it is to miss something in any one of them. The native apps don't help: the FT homepage doesn't know what the Economist published, and neither knows what I've already read.
- **No cross-source synthesis.** Native apps cannot answer "what's been going on with Turkey across these three sources this quarter" or "what are the main arguments about AI regulation that have appeared in my reading over the last month." That synthesis layer does not exist outside Meridian.

Meridian separates two jobs cleanly:

- **Daily flow — filter and amplifier.** Surfaces articles for me to read *myself*. AI-generated summaries (Brief / Analysis / Full-text views) help me match reading depth to available time, but I am still the reader. Scoring and Key Themes are in service of "what should I read today."
- **Retrospective layer — synthesis.** Briefs and Q&A operate over the corpus I have curated. This is the one place where AI synthesis genuinely replaces re-reading: when I ask for a brief on a topic, the alternative is not "read the ten underlying articles again," it is "don't bother." Briefs are how the corpus earns its keep.

---

## § 4 — Non-goals

Meridian is deliberately *not*:

- **Not a work or client tool.** Meridian is for personal reading and general knowledge building. Investment research, client work, and any real-time market use happen elsewhere, with different tools suited to those needs.
- **Not a general news aggregator.** The value comes from depth over breadth. A small set of trusted sources treated well beats a firehose from everywhere. New sources are a significant commitment, not a casual addition.
- **Not a real-time tool.** Breaking news reaches me through other channels. Meridian works on my schedule, not the news cycle's. Ingestion is batched; nothing in the system is optimised for sub-hour latency.
- **Not multi-user, not shared, not public.** No other readers, no public URLs with user-generated content, no citations produced for external consumption.
- **Not a replacement for reading originals.** The daily flow surfaces articles for me to read myself. AI-generated summaries support my reading (Brief / Analysis / Full-text views match available time), but Meridian is a filter and amplifier, not a synthesiser I blindly trust. The retrospective layer (briefs, Q&A) is the one place where AI synthesis genuinely replaces re-reading — and it operates over a corpus I have already curated.
- **Not a native mobile app.** Meridian will not ship as a Swift/SwiftUI iOS app distributed through the App Store. No native Android app. No developer-program fees, no store reviews, no separate codebase. **However**, *mobile web parity is a MUST (see § 5)*: the site at `meridianreader.com` must work well on iPhone and iPad, be responsive and touch-native, and behave correctly when added to the home screen via Safari's *Add to Home Screen* (giving a full-screen, app-like experience). PWA / home-screen-installable behaviour is in scope. Native App Store distribution is not.
- **Not revenue-generating.** Meridian is never monetised, never sold, never offered to others.

---

## § 5 — Capabilities

Must / nice / no, with notes where the framing matters.

### MUST

| # | Capability | Notes |
|---|---|---|
| 1 | Daily AI-picked articles across FT / *Economist* / FA | Current cadence once/day, gated via `kt_meta` |
| 2 | Key Themes — incremental seed + tag-new + evolve architecture | Currently VPS-only |
| 3 | On-demand briefs | Core value prop. See P3: briefs split into Tier A (quick, cheap) and Tier B (in-depth, quality-first) |
| 4 | Q&A over the corpus | Tier A synthesis — retrieval + Haiku over top-N |
| 5 | Learned scoring from read / save / dismiss behaviour | Single-pass enrichment; evolving preference vector rather than re-scoring old articles |
| 6 | Chart capture from *The Economist*, continuous | **Conditional MUST.** Continuous capture requires stable Economist ingestion. If Economist scraping cannot be stabilised, this capability degrades to NICE. Integration of captured charts into briefs can be batched. |
| 7 | Newsletter ingestion (Bloomberg, others via iCloud) | Already working |
| 8 | Mobile web parity — daily-flow subset | MUST = reading, saving, browsing Feed / Suggested / Saved, *viewing briefs*. Creating briefs can be desktop-primary; viewing is mobile-native. |
| 9 | Simple full-text search over the corpus | Table stakes |
| 10 | Unified read-state across Feed / Suggested / Saved | Principle locked (P2); implementation in Phase 2/3 |
| 11 | Health & Cost surface | Stats panel + cost tracking panel. Desktop-primary. Cost alerting (projected monthly >$20) from v1; other alerts follow P4. |
| 12 | Chrome-extension bookmark capture | Reliability bar applies (P1). Failures must be visible. |

### NICE

- PDF brief export (`brief_pdf.py` already drafted; markdown/HTML is the primary form)
- Historical cost view with feature-by-feature comparison (v2 of cost tracking)
- Chart-in-brief rendering improvements beyond the v1 integration

### NO

- Multi-user, sharing, public URLs
- Sources beyond the three primary + newsletters (no NYT, WSJ, Reuters, Substack, podcasts, YouTube)
- Native iOS / Android apps via App Store
- Export integrations to third-party services (Readwise, Notion, calendar)
- Social features, annotations visible to others, commentary
- Monetisation in any form
- Sub-hour ingestion latency / real-time push

---

## § 6 — Principles

These are the charter's most durable content. Specific features and tensions will change; these should still hold in eighteen months.

**P1 — Capture reliability outranks synthesis reliability.**
The core promise of Meridian is that if I'm supposed to see something, I see it. Anything that captures data — source ingestion, Chrome-extension bookmarking, newsletter sync, chart capture — has a high reliability bar: failures must be *detected within one sync cycle, alerted within hours, and diagnosable quickly enough that most fixes take under thirty minutes; complex failures escalate to a weekend maintenance window (Tier 1)*. Anything that synthesises captured data — briefs, Q&A, scoring — may degrade gracefully. A brief that fails today is inconvenient; an FT scrape that silently stopped three days ago breaks the whole proposition.

**P2 — One article, one read-state, across all surfaces.**
An article is the same article whether it appears in Feed, Suggested, Saved, or a brief's citations. Its read / unread / saved / dismissed state is singular and consistent across desktop, mobile, Mac-local, and VPS. I should never re-read something because two views of the same system disagreed about whether I had seen it. Implementation is a Phase 2/3 task; the principle is non-negotiable.

**P3 — Synthesis cost scales with intent.**
Frequent, low-stakes synthesis (Q&A, quick briefs, inline summaries) must be architected as *retrieval over an embedded index answered by a cheap model against top-N chunks* — whole-corpus context-stuffing is the antipattern being pre-empted here. In-depth briefings are the deliberate exception: when I ask for depth, accuracy outranks cost, and using the most capable model against a wider retrieved context is the right trade. The budget ceiling in § 8 assumes Tier A is the common path and Tier B is ad-hoc.

**P4 — Observability requires alerting from v1.**
Any monitoring surface — uptime, ingestion health, API cost, scoring drift — ships with alerting included, not as a later addition. A dashboard I have to remember to check is not observability; it is decoration. The corollary: I would rather have a crude panel with a working alert than a sophisticated panel with none.

**P5 — Deployment is three-tiered, and Tier 3 alerting is what makes Tier 1 safe.**

- **Tier 1 — Risky / architectural / maintenance changes: weekends.** More free time to monitor, roll back, iterate.
- **Tier 2 — Quick fixes (under 15 min, low risk, easy rollback): anytime.** Trivial corrections do not wait three days.
- **Tier 3 — Reliability-breaking incidents: alert immediately, any day, any hour.** A stopped source, a failing bookmark pipeline, a broken newsletter sync — these surface to me the moment they're detected, not at the next weekend review.

Tier 3 is load-bearing for Tier 1: I can only ship risky changes on a Saturday because alerting tells me on Sunday if something I did broke Monday's ingestion. Remove Tier 3 and weekend deploys become anxious and rare, and the "leave alone" ambition collapses.

**P6 — Meridian operates near its constraint frontier.**
Twelve MUST capabilities, a strict capture-side reliability bar, a $5–20/month budget ceiling, mobile web parity, solo development against a finite weekday-and-weekend time pool. This is a tight set. Adding a thirteenth MUST in future requires *explicitly* dropping an existing one or raising the budget ceiling. Silent accumulation of obligations is the failure mode; this principle is the guard against it.

---

## § 7 — Success criteria: "done enough to leave alone"

Meridian is "done enough" when all of the following hold simultaneously, not in isolation:

**Attention cost in steady state.** Meridian requires less than thirty minutes per week of my attention for maintenance, monitoring, or manual intervention — *excluding reading itself*, which is the point of the tool and doesn't count against its budget.

**Capture reliability meets the P1 bar.** No source has silently stopped for more than one sync cycle without my being alerted. The Chrome-extension bookmark path is reliable enough that I trust it; newsletter ingestion hasn't missed more than 24 hours in the last month. When capture breaks, the daily health email tells me which source, when it stopped, and ideally why.

**Synthesis is available but not precious — with one exception.** Tier A synthesis (Q&A, quick briefs, inline summaries) works, but a day's outage is acceptable and a week's is not. Tier B in-depth briefings are the deliberate exception where quality *is* precious: when I ask for an in-depth brief, I expect the best model available and a wide retrieved context, and I accept the per-call cost. Their architecture follows P3.

**The learning signal is real, not theatrical.** The 14-day AI-selected rate — currently 32%, 41% this week — is tracked over months and trends in the right direction. A specific numeric target is deferred (see § 10, Q4) but the trajectory is monitored. If the number collapses, I know. If it plateaus, I know.

**Mobile reading works.** I can read the daily flow, save articles, browse Feed / Suggested / Saved, and view briefs on iPhone and iPad, from a Safari home-screen shortcut, in any context I read news — sofa, lunch, train, weekend. No "open the laptop" friction for the reading loop itself.

**Costs stay honest.** Steady-state API + incidentals remain within $5–20/month. Projected overruns trigger an alert in the daily health email before month-end, not via the Anthropic invoice after the fact. If a MUST capability genuinely cannot live within that ceiling, I've decided explicitly whether to raise the ceiling or drop the capability — no silent degradation.

**The constraint frontier holds.** No thirteenth MUST has been added without a deliberate trade. The feature set has stabilised.

When these hold together for roughly a quarter — one season of use without *material intervention* — Meridian is done enough. **Material intervention** is defined as anything beyond the thirty-minute weekly attention budget in the first criterion: Tier 2 quick fixes within budget don't reset the quarter; anything larger (Tier 1 maintenance sessions, Tier 3 incident response, feature work) does. Further work after that point becomes optional improvement, not required maintenance.

---

## § 8 — Constraints

**Budget.**
- Steady-state API + incidentals: $5–20/month USD, $20 being the hard ceiling.
- VPS (Hetzner): €8/month, fixed.
- Existing subscriptions (FT, *Economist*, *Foreign Affairs*): paid separately; not adding more.
- If a MUST capability cannot be delivered within the $20/month ceiling, the choice between raising the ceiling and dropping the capability is made explicitly, never by silent quality degradation (cheaper model, shorter context, etc.).

**Time.**
- Solo developer. Weekday evenings and weekends. No other contributors.
- Half-marathon training (10 May 2026) is managed separately and is *not* a blocker for the current migration work.
- Weekend usage of Meridian itself is heavy — any fragility that surfaces at weekends is a direct hit to value, which is why P5 (three-tier deployment) and P4 (alerting-from-v1) exist.

**Hardware.**
- Mac M1 for development, bookmark capture, and (currently) parallel local ingestion.
- Hetzner VPS for production: ingestion, enrichment, DB-of-record, serving, scheduled jobs.
- Chrome extension v1.3 as the manual capture path for FT saved, Bloomberg, and as fallback for any source whose scraper is unreliable.

**Backups.**
- Daily DB snapshot to at least one location off the VPS. Implementation in Phase 4; specifics deferred.

**Architecture.**
- Mac/VPS parallel-run is the current transitional state, *not* the target. Phases 2–4 converge on VPS as production and Mac as dev + optional mirror.

**Known fragility (Phase-2 targets, flagged here for honesty).**
- Economist Playwright scraper intermittently blocked by Cloudflare; currently disabled, manual bookmark fallback.
- Intermittent partial-enrichment failures — some articles in a scrape batch enrich, others stay title-only; root cause not fully resolved.
- Occasional "database is locked" errors during parallel Mac/VPS sync (observed 20 Apr 2026); symptom of parallel-run friction that Phase 2 will structurally resolve.
- Mac and VPS DBs drift by small amounts between sync cycles (8 articles on 21 Apr); expected with current architecture, not a bug.

---

## § 9 — Target architecture (post all 4 migration phases)

```
                         ┌──────────────────────────────┐
                         │       Hetzner VPS            │
                         │    (production, always-on)   │
                         │                              │
                         │  • Ingestion (FT, Econ, FA)  │
                         │  • Enrichment pipeline       │
                         │  • DB of record (meridian.db)│
                         │  • Flask API + web serve     │
                         │  • AI picks (scheduled)      │
                         │  • Key Themes                │
                         │  • Briefs / Q&A (Tier A/B)   │
                         │  • Health & Cost surface     │
                         │  • Daily health email        │
                         │  • Tier-3 alerts → email/pn  │
                         └───────────────┬──────────────┘
                                         │
                   ┌─────────────────────┼───────────────────────┐
                   │                     │                       │
          ┌────────┴────────┐   ┌────────┴────────┐   ┌──────────┴──────────┐
          │  Mac M1 (dev)   │   │  Chrome ext v1+ │   │  Mobile web (PWA)   │
          │                 │   │                 │   │                     │
          │ • Code + deploy │   │ • FT saved      │   │ • iPhone, iPad      │
          │ • Bookmark term │   │ • Bloomberg     │   │ • Home-screen short │
          │ • Optional      │   │ • Scraper       │   │ • Read / save /     │
          │   local mirror  │   │   fallback      │   │   browse / view     │
          │                 │   │                 │   │   briefs            │
          └─────────────────┘   └─────────────────┘   └─────────────────────┘
```

Mobile web is a client of the VPS serving layer, not an independent node. The diagram places it alongside Mac/extension to highlight it as a distinct reading context, not to imply it runs independently.

**Key properties of the target state:**

- VPS is the single production system. One DB of record. One cost of record. One set of schedulers.
- Mac is development-primary. It may run a local mirror for offline development, but it is not where production data lives or is authoritative.
- The Chrome extension is a *capture* device — FT saved articles, Bloomberg newsletters, and any article on any page via the clip button. It writes to VPS.
- Mobile is a *read* device (plus save / dismiss / brief-viewing). It does not run ingestion, it does not run enrichment, it does not need to work offline beyond basic browser caching.
- The daily health email is the reliability enforcement mechanism. Tier-3 alerts (capture failures, cost overrun projections) are a separate, faster channel on the same infrastructure.

This is the post-Phase-4 steady state. Today (21 Apr 2026, post-Phase-1) we are still running Mac + VPS in parallel with the Mac as a mirror of capture; Phases 2–4 move the authoritative role fully to the VPS and put the observability / alerting layer on top.

---

## § 10 — Open questions

These are deliberately unresolved. Each is flagged for decision at or before the phase that forces the choice.

**Q1 — Newsletter scoring and theming.** Should ingested newsletters be scored / AI-picked / tagged with Key Themes the same as articles, or treated as a separate stream with their own handling? Currently treated separately; reassess in Phase 3 once Key Themes has matured.

**Q2 — Mac's post-migration role.** After Phase 4, does the Mac retain any production role (e.g. a read-only mirror, a scratch ingestion endpoint) or is it purely a development machine? Decide at Phase 4 planning.

**Q3 — Learned scoring: preference vector format and update cadence.** How is the user's preference signal represented, how often is it updated, and how is the evolving prompt/vector versioned? Architecture deferred to Phase 3.

**Q4 — Target for the 14-day AI-selected rate.** Currently 32% over 14 days, 41% this week. The charter uses this as the measurement of "is the system learning." Setting a specific target (e.g. 50%? 60%? asymptote?) requires more months of data and is deferred — premature definition is worse than none.

**Q5 — Brief persistence.** When I generate a brief on "Turkey Q1 2026" — is it saved, versioned, searchable? Or ephemeral, regenerated on demand? Affects cost (save once vs. regenerate) and the "private corpus" framing (are briefs part of the corpus or derivatives of it?). Decide at Phase 3 or when briefs become frequent enough for the choice to matter. Note the cost asymmetry: persisted briefs cost once and are free to re-view; ephemeral briefs cost each time but stay current with the evolving corpus. Which is right depends on how I actually use them.

---

## § 11 — Revision protocol

This charter is a living document.

- **Reviewed at each phase boundary** (after Phase 2, after Phase 3, after Phase 4). Every review asks: do the principles still hold? Have any MUSTs drifted? Have any NICE items silently been promoted?
- **Adding a new MUST requires naming what it displaces.** Principle P6 (constraint frontier) is enforced by this rule. A new MUST without a trade-off statement is rejected at review.
- **Budget ceiling ($20/month) is a hard constraint, not a soft target.** Crossing it requires an explicit decision to raise the ceiling, not a quiet acceptance of overage.
- **Open questions (§ 10) are reviewed at each phase boundary.** Each is either resolved, explicitly kept open, or closed as no-longer-relevant.
- **Principles (§ 6) change least.** If a principle is being challenged, the first question is whether the situation is an exception rather than a principle change.

---

## § 12 — Where we are in the project

Meridian's migration from Mac-authoritative to VPS-authoritative is planned as four phases:

- **Phase 1 — VPS foundation & secrets (complete, Session 63, 20 Apr 2026).** VPS stood up, secrets migrated, security incident resolved, parallel-run established.
- **Phase 2 — Authoritative role migration (next, Session 65+).** VPS becomes the DB of record and primary scheduler. Mac steps back to dev + mirror. Addresses the known fragility items in § 8 (DB-lock, drift, partial-enrichment).
- **Phase 3 — Synthesis & learning layer.** Briefs (Tier A/B per P3), Q&A, learned scoring architecture. Chart-capture integration. Resolves open questions Q3, Q5.
- **Phase 4 — Autonomous operation layer.** Daily health email, Tier-3 alerting (P5), cost alerting (P4), uptime monitoring, off-VPS DB snapshots. This is the layer that makes "done enough to leave alone" achievable.

Detailed phase plans are separate documents. This charter sets the target; the phases are the route.

---

*End of charter.*
