-- P2-8 rollback: drop extension_write_failures table.
-- SQLite >= 3.35 supports DROP COLUMN; here the whole table goes.

DROP INDEX IF EXISTS idx_extension_write_failures_timestamp;
DROP TABLE IF EXISTS extension_write_failures;
