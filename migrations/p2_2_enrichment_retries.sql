-- Phase 2, P2-2: add enrichment_retries column to articles
-- Date: 2026-04-25 (Session 66)
-- Plan reference: PHASE_2_PLAN.md § 8 Block 1 / § 4.1
--
-- This column tracks how many times the nightly enrich_retry job has
-- attempted to enrich a stuck title_only article. Cap at 3 retries; on
-- cap hit, status is set to 'enrichment_failed' and a Tier-3 alert fires.
--
-- DEFAULT 0 means existing rows are NULL-safe and treated as "never retried."

ALTER TABLE articles ADD COLUMN enrichment_retries INTEGER DEFAULT 0;
