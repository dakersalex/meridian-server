# Meridian — Cost Model

**Purpose:** Ground the charter's $5–20/month budget ceiling in concrete per-feature estimates. Inform Phase 2+ scope decisions. Calibrate against real data after 30 days of cost tracking (Phase 4 deliverable).

**Author:** Alex Dakers
**Date:** 21 April 2026 (Session 64)
**Status:** v1 estimate. ±50% uncertainty on all numbers until cost-tracking panel is live. Revise at each phase boundary.

---

## § 1 — Scope & assumptions

**Budget container.** Meridian steady-state API + incidentals: $5–20/month USD. VPS (€8/month) and publisher subscriptions (FT / *Economist* / *Foreign Affairs*) are outside this envelope.

**What this document does NOT include.** VPS hosting, domain, Backblaze B2 (when added in Phase 4, ~$0.50/month for this corpus size), Apple iCloud IMAP (free at this scale).

**Corpus assumptions (today's state, light growth projection).**

| Dimension | Today | Steady-state assumption |
|---|---|---|
| Article corpus | ~1,000 | 1,500–2,000 after one year |
| New articles ingested/week | ~60–80 | ~100 |
| Articles enriched/week | ~100 (incl. backfill) | ~100 |
| RSS candidates scored/day | ~40 | ~50 |
| Active KT themes | 8 | 10–15 |
| Newsletters/week | ~30 | ~30 |
| Videos/interviews/month | unknown (a handful) | ~4 |

**Usage assumptions (Alex-stated, Session 64).**

- **Briefs:** 2 short (Tier A) + 1 in-depth (Tier B) per week = 8 short + 4 in-depth per month.
- **Q&A:** ad-hoc, assume 20 queries/month steady-state. Low-volume by construction.
- **Bulk import:** Chrome-extension scraping; no LLM call. Zero API cost.
- **Chart capture:** image extraction via Playwright; no LLM call. Zero API cost. (Optional future OCR/description = negligible at volume.)

**Model pricing reference (Anthropic public pricing, Apr 2026).**

| Model | Input $/1M tok | Output $/1M tok | Batch (50% off both) |
|---|---|---|---|
| Claude Haiku 4.5 | $0.80 | $4.00 | $0.40 / $2.00 |
| Claude Sonnet 4.6 | $3.00 | $15.00 | $1.50 / $7.50 |
| Claude Opus 4.7 | $15.00 | $75.00 | $7.50 / $37.50 |

**Other services used.**

- OpenAI `text-embedding-3-small`: $0.02 / 1M tokens. Used for retrieval index (P3).
- Anthropic Files API: negligible for this corpus.
- Web search (via Claude tool use or SerpAPI): ~$0.005–0.01 per search. Currently low-volume.
- Video transcription (OpenAI Whisper API or equivalent): ~$0.006/minute.

**Batch API assumption.** Non-latency-sensitive pipelines (enrichment, KT tagging, embeddings backfill) use the 50% batch discount. Latency-sensitive paths (Q&A, briefs at request time) do not.

**Tier B model choice (locked Session 64).** Opus is the default for in-depth briefs, not Sonnet. At 4 briefs/month the cost difference is ~$1.90/month ($0.50 Sonnet → $2.40 Opus), which sits comfortably within the $20 ceiling. This reflects the charter's P3 principle that in-depth briefings are the deliberate exception where quality outranks cost — and within that exception, there's no reason to accept Sonnet when Opus is affordable.

---

## § 2 — Per-feature monthly cost estimates

Each feature has an estimate with stated assumptions. "Base" = expected steady-state; "High" = upper realistic bound.

### F1 — Article enrichment

Haiku pass on each newly ingested article: body → summary + key_points + highlights + tags + topic + pub_date.

- Assumption: 100 articles/week × 4 weeks = 400/month. Average input 3,500 tokens (body), output 800 tokens.
- Non-batch: 400 × (3,500 × $0.80/1M + 800 × $4.00/1M) = 400 × ($0.0028 + $0.0032) = **$2.40/month**
- Batch (50% off): **$1.20/month**

**Base estimate: $1.20/month** (assume batch path is default, already proven in Session 59 PoC).

### F2 — RSS AI picks

Twice-daily candidate scoring across 13 RSS feeds. Haiku scores each candidate; saves score ≥ 7–8.

- Assumption: ~50 candidates/run × 2 runs/day × 30 days = 3,000 scoring calls/month. Each call: input ~600 tokens (headline + abstract + context), output ~150 tokens (score + reasoning).
- Non-batch (latency-sensitive, runs at 03:40 & 09:40 UTC): 3,000 × (600 × $0.80/1M + 150 × $4.00/1M) = 3,000 × ($0.00048 + $0.0006) = **$3.24/month**
- These are latency-sensitive by design (feed updates tied to daily cadence), so batch discount not applied here.

**Base estimate: $3.20/month.** Biggest single line item at current design.

**Saving lever:** Pre-filter more aggressively upstream (tighter RSS keyword filters, unfetchable blocklist already in place) — could drop candidate count 30–50%. Savings: ~$1.00–1.50/month.

### F3 — Key Themes (incremental architecture)

- **Seeding:** one-off; done. Not in recurring cost.
- **Tag-new:** each new article gets tagged against active themes. Haiku, ~100 articles/week.
  - Input ~1,500 tokens (article summary + theme definitions), output ~100 tokens.
  - 400/month × (1,500 × $0.80/1M + 100 × $4.00/1M) = 400 × ($0.0012 + $0.0004) = **$0.64/month**
  - Batch: **$0.32/month**
- **Evolve:** periodic theme refresh, ~monthly. One Sonnet call against summaries of articles tagged to a theme.
  - 10 themes × 1 evolve/month × (10,000 input + 2,000 output tokens) = 10 × ($0.03 + $0.03) = **$0.60/month**

**Base estimate: $0.90/month.** Small but non-trivial.

### F4 — Tier A synthesis (Q&A + quick briefs)

Retrieval + Haiku over top-N chunks (P3).

- Q&A: 20/month × (2,000 input tokens retrieved context + 400 output) = 20 × ($0.0016 + $0.0016) = **$0.06/month**
- Short briefs: 8/month × (4,000 input tokens + 800 output) = 8 × ($0.0032 + $0.0032) = **$0.05/month**

**Base estimate: $0.15/month.** Essentially free.

### F5 — Tier B in-depth briefs (Opus, default)

Opus over wider retrieved context (P3 exception — quality > cost, within a capped frequency).

- Frequency: 4/month (Alex-stated: 1/week).
- Per-call assumption: 25,000 input tokens (retrieved context covering ~15–20 articles + charts + newsletter excerpts + instruction), 3,000 output tokens (structured brief with citations).
- 4 × (25,000 × $15.00/1M + 3,000 × $75.00/1M) = 4 × ($0.375 + $0.225) = **$2.40/month**

**Base estimate: $2.40/month.**

**Sensitivity:** doubling frequency to 8/month → $4.80. Downgrading to Sonnet → $0.48 (saves $1.90 but loses the explicit quality step). Using Opus batch where tolerable (Opus batch isn't typically suited to on-demand briefs since they're latency-sensitive) → no realistic saving.

**Saving lever:** prompt caching on the brief system prompt + template + instructions (lever 3 below) will materially reduce the per-call input cost once implemented. Estimate: –20–30% on F5, i.e. saves $0.50–0.70/month from this line alone.

### F6 — Retrieval index (embeddings)

One-time cost per article at ingestion; re-embedded only if model changes. Cost is per-article, scales linearly.

- Embedding backfill (existing 1,000 articles): 1,000 × 2,500 tokens × $0.02/1M = **$0.05 one-off.**
- Ongoing: 400 articles/month × 2,500 tokens × $0.02/1M = **$0.02/month.**

**Base estimate: <$0.05/month.** Essentially free with `text-embedding-3-small`.

### F7 — Video/interview transcription (MUST #13)

User-submitted YouTube / podcast / interview URLs → audio pulled → transcribed → Haiku post-processing (summary, key_points, topic).

- Assumption: 4 items/month × avg 35 min = 140 minutes/month.
- Whisper API: 140 × $0.006 = **$0.84/month**
- Haiku post-process (~same cost profile as article enrichment, but longer input): 4 × (8,000 input + 1,200 output) = 4 × ($0.0064 + $0.0048) = **$0.045/month**. Batch: $0.02.

**Base estimate: $0.85–0.90/month.**

**Sensitivity:** 8 items/month (double) → $1.80. 12 items/month → $2.70. Stays under budget comfortably.

**Saving lever:** `whisper-1` at $0.006/min is already the cheapest mainstream option. Local Whisper on Mac M1 is free but (a) only works when Mac is on, which violates the Phase-4 always-on target, and (b) slower. Not pursuing.

### F8 — Health & cost monitoring

Self-referential: cost-tracking itself must cost almost nothing.

- Implementation is a decorator on each API call logging token counts + feature tag to a DB table. Pure local write, zero API cost.
- Daily health email: one templated send via iCloud SMTP, zero API cost.
- Tier-3 alerts: email + optional push, negligible.

**Base estimate: $0.00/month** (infrastructure only).

### F9 — Bulk import (Chrome extension buttons) (MUST #14)

Source-specific pagination through Economist / Bloomberg saved-articles pages. Extension scrapes; no LLM call at import time.

- API cost: $0. Ingested articles then flow through F1 enrichment and F3 KT tagging at normal per-article cost.

**Base estimate: $0.00/month** (the cost is already counted in F1/F3).

---

## § 3 — Totals & scenarios

### Base steady-state total (Opus as default on Tier B)

| Feature | $/month |
|---|---|
| F1 Enrichment (batch) | 1.20 |
| F2 RSS picks | 3.20 |
| F3 Key Themes | 0.90 |
| F4 Tier A synthesis | 0.15 |
| F5 Tier B briefs (Opus, 4/mo) | 2.40 |
| F6 Embeddings | 0.05 |
| F7 Video/interview transcription | 0.90 |
| F8 Health monitoring | 0.00 |
| F9 Bulk import | 0.00 |
| **Subtotal** | **8.80** |
| Buffer for web search, agent tool use, retries, misc (+20%) | 1.80 |
| **Total base** | **~$10.60/month** |

**Base sits comfortably in the $5–20 band, about $10 under the $20 ceiling.** The two cost drivers are F2 (RSS picks, ~$3.20) and F5 (Tier B briefs on Opus, ~$2.40). Together they're ~55% of base spend.

### High-scenario (all features trending upward)

Doubling Tier B brief frequency (1→2/week, +$2.40), doubling video volume (4→8/mo, +$0.90), tighter Q&A (20→40/mo, +$0.06), +25% buffer: **~$15/month**. Still within ceiling.

### Scenarios against budget bands

| Band | Monthly | What fits comfortably | What's constrained | What's excluded |
|---|---|---|---|---|
| **$5 floor** | $5 | F1 enrichment, F3 KT, F4 Q&A, F6 embeddings, F8, F9 | F2 RSS picks (trim candidates aggressively or reduce to once/day). F5 downgrades to Sonnet or Haiku only. F7 video (1–2/month max). | Opus for anything. Tier B on Sonnet above 4/mo. |
| **$10 mid** | $10 | Everything at base cadence including Opus for Tier B at 4/mo | Video above ~6/mo. Tier B above ~4/mo. | High-frequency Q&A with wide retrieval. Opus on routine paths (Tier A, scoring). |
| **$20 ceiling** | $20 | Everything at base, 1.5–2× briefs, 1.5× video | Room for Opus briefs at 2/week OR 2× video volume AND 2× brief frequency. | Opus on routine paths. Whole-corpus context stuffing for any synthesis (violates P3). |

**Reading of the table:** the base design (~$10.60/month) leaves meaningful headroom. The $20 ceiling is comfortable unless routine paths (F1/F2/F3) get upgraded to Opus, which P3 prohibits.

---

## § 4 — Cost-saving levers

Ranked by leverage. Each line: mechanism → expected saving → trade-off.

1. **Batch API for non-latency-sensitive pipelines.** Already applied to F1, F3. → Saves 50% on those paths (~$0.90/month vs non-batch). → Trade-off: 24h latency on batch completion. Acceptable for enrichment (article is already ingested; summary just lags) and KT tag-new.

2. **Retrieval not stuffing, for all synthesis (P3).** The difference between sending top-10 retrieved chunks (~5k tokens) and whole-corpus stuffing (~500k tokens) is 100× cost on every call. → For Tier A at 28 calls/month, stuffing would cost ~$20/month on Haiku alone. Retrieval keeps it at $0.15. → Trade-off: retrieval quality depends on embeddings and chunking; Tier B's wider context is the pressure valve.

3. **Prompt caching** for repeated context (theme definitions, system prompts, brief templates). → Anthropic caches input prefixes at 10% of base input rate for cache hits; 90% reduction on the cached portion. Applies strongest to F5 Tier B briefs (template stable) and F3 KT tag-new (theme definitions stable). → Savings: ~$0.60–0.90/month, most of it on F5. → Trade-off: none. Pure win. Implement in Phase 3.

4. **Tighter upstream filtering** for F2 RSS. Better keyword rules, richer unfetchable blocklist, de-dup against recent ingestion. → Candidates 50→30/run. → Savings: ~$1.30/month. → Trade-off: risk of filtering out articles that would have scored highly. Tune carefully.

5. **Haiku-first cascading** for synthesis. Tier A uses Haiku; Tier B uses Opus. The charter's P3 codifies this already. → No additional saving beyond what's counted. → Trade-off: none; this is just the design.

6. **Downgrade Tier B to Sonnet** if budget squeezed. Saves $1.90/month. → Trade-off: loses the quality step that justifies the Tier B exception in the first place. Only do this if the model is signalling stress, not as a default.

7. **Reduce RSS pick cadence** (2/day → 1/day). → Savings: $1.60/month. → Trade-off: lose the afternoon-edition pickup. Probably fine for Meridian's non-real-time posture, but directly conflicts with the daily twice-a-day schedule that currently runs.

8. **Local Whisper for transcription.** Free but requires Mac always-on. → Savings: $0.85/month. → Trade-off: breaks the "VPS is authoritative" target (§9 architecture). Not pursuing.

---

## § 5 — Auto-degradation paths (what can scale down under cost pressure)

Each path lists: what to degrade, how, and the quality impact. Framed as options the charter authorises, not silent defaults (per § 8 budget rule: "never by silent quality degradation").

| Feature | Degradation step | Quality impact |
|---|---|---|
| F5 Tier B briefs | Opus → Sonnet | Moderate loss on nuanced synthesis. Sonnet is meaningfully cheaper and still strong. Use only if the $20 ceiling is under actual pressure. |
| F5 Tier B briefs | Sonnet → Haiku (with wider retrieval) | Significant loss. Haiku less coherent over 20+ article synthesis. Last-resort degradation only. |
| F2 RSS picks | Haiku → smaller prompt | Moderate. Scoring quality depends on reasoning context; aggressive trimming loses signal. |
| F2 RSS picks | 2×/day → 1×/day | Low. Misses afternoon pickup but Meridian is not real-time. |
| F4 Tier A Q&A | top-10 → top-5 retrieval | Low at current corpus size. Revisit when corpus > 5k articles. |
| F7 Video transcription | 35-min avg → skip anything > 60 min | Loss of long-form interviews. Probably never binds. |
| F1 Enrichment | Real-time → batch only | None. Already the default. |
| F3 KT evolve | Monthly → quarterly | Low. Themes don't drift that fast. |

**Not auto-degradable:** F6 embeddings (already near-free), F8 monitoring (already free), F9 bulk import (free), F4 baseline (already cheap).

---

## § 6 — Implications for the charter

Directly relevant to the charter edits pending from your review comments.

1. **#13 Video/interview transcription is affordable as a MUST.** Base cost ~$0.90/month; even at 2× volume it stays under $2. No charter change needed — keep as MUST.

2. **#14 Bulk import is free** at the API layer; the ingested articles flow through normal enrichment cost. No charter change needed.

3. **Tier B briefs default to Opus, not Sonnet.** Cost delta is +$1.90/month (Sonnet $0.50 → Opus $2.40 at 4/mo). Base total moves from ~$8.30 to ~$10.60. Still comfortably under $20 with ~$10 headroom. This makes P3's "accuracy outranks cost" concrete: Tier B uses Opus.

4. **RSS picks (F2) and Tier B briefs (F5) are the two biggest cost drivers**, together ~55% of base spend. If budget pressure emerges, F2 has more saving levers (4, 7) than F5 (only meaningful lever is model downgrade).

5. **The $20 ceiling is not near being threatened** at base design. Base ~$10.60, high-scenario ~$15. The ceiling is a genuine safety margin, not a tight bound.

6. **No MUST needs to be dropped or downgraded on cost grounds.** The constraint frontier (P6) holds on *time* and *scope*, not on dollars.

---

## § 7 — Open questions for future revision

**C1 — Real-data calibration.** Every number above is a pre-measurement estimate. After 30 days of the cost-tracking panel running in production (Phase 4), revise this document against actuals. Expect ±50% drift on individual lines, likely within ±20% at the total level.

**C2 — Prompt-caching uptake.** Quantify savings from lever 3 (prompt caching) once implemented in Phase 3. F5 is the biggest beneficiary.

**C3 — Growth curve of F2.** If RSS candidates grow with corpus (they shouldn't, but source behaviour could change), F2 may scale non-linearly. Monitor.

**C4 — Web search volume.** Currently minor. If Tier B briefs start routinely pulling live web search for context, cost rises. Cap or budget explicitly in Phase 3.

**C5 — Opus vs Sonnet for Tier B as standing choice.** Current decision (Session 64): Opus as default for Tier B in-depth briefs. Revisit after ~10 Tier B briefs have been generated and the quality delta over Sonnet can be judged against the +$1.90/month cost.

---

*End of cost model v1.*
