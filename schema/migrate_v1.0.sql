-- Personal Context Engine — Migration v1.0
-- 1. Adds image_hash column to receipt_scans (for existing v0.2 databases)
-- 2. Removes restrictive CHECK constraint on purchase_history.source
-- Idempotent: safe to run multiple times.

-- Version tracking table
CREATE TABLE IF NOT EXISTS schema_version (
    version TEXT PRIMARY KEY,
    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO schema_version (version) VALUES ('1.0.0');

-- image_hash: already in v0.2 CREATE TABLE for fresh installs.
-- For upgrades from v0.2, the ALTER TABLE is handled by setup.sh.
CREATE INDEX IF NOT EXISTS idx_receipt_scans_hash ON receipt_scans(image_hash);

-- Recreate purchase_history without restrictive source CHECK (idempotent)
CREATE TABLE IF NOT EXISTS purchase_history_v1 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    item_name TEXT,
    price REAL,
    currency TEXT NOT NULL DEFAULT 'JPY',
    purchase_date DATE,
    order_id TEXT,
    category TEXT,
    possession_id INTEGER,
    raw_data TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (possession_id) REFERENCES possessions(id)
);

-- Copy data only if v1 table is empty (first migration run)
INSERT INTO purchase_history_v1
    SELECT * FROM purchase_history
    WHERE NOT EXISTS (SELECT 1 FROM purchase_history_v1 LIMIT 1);

DROP TABLE IF EXISTS purchase_history;
ALTER TABLE purchase_history_v1 RENAME TO purchase_history;

-- Recreate indexes
CREATE INDEX IF NOT EXISTS idx_purchase_history_order_id ON purchase_history(order_id);
CREATE INDEX IF NOT EXISTS idx_purchase_history_source_date ON purchase_history(source, purchase_date);
