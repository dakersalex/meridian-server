-- P2-8: Extension write-failure logging
-- Created Session 71 (28 Apr 2026)
-- Logs every failed POST/PATCH the Chrome extension makes against the VPS.
-- Used by extension_failure_watchdog.py to compute rolling 24h failure rate
-- and fire Tier-3 alert if rate exceeds 10% (PHASE_2_PLAN § 6 condition 3).
--
-- The matching CREATE TABLE IF NOT EXISTS lives in server.py's init_db() so
-- the schema lands on Flask boot. This file is the canonical record.

CREATE TABLE IF NOT EXISTS extension_write_failures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,    -- ms since epoch (server-side)
    url TEXT,                       -- the article URL the extension tried to write
    action TEXT,                    -- 'post_article' | 'patch_article' | 'post_cookies' | etc.
    error_msg TEXT,                 -- exception message or HTTP status text
    status_code INTEGER             -- HTTP status if the response came back; NULL on network/CORS
);

CREATE INDEX IF NOT EXISTS idx_extension_write_failures_timestamp
    ON extension_write_failures(timestamp);
