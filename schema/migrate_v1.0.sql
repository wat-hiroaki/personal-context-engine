-- Personal Context Engine — Migration v1.0
-- Adds image_hash column to receipt_scans
-- Removes restrictive CHECK constraint on purchase_history.source

-- Add image_hash column for proper duplicate detection
ALTER TABLE receipt_scans ADD COLUMN image_hash TEXT;
CREATE INDEX IF NOT EXISTS idx_receipt_scans_hash ON receipt_scans(image_hash);

-- SQLite does not support ALTER TABLE DROP CONSTRAINT.
-- To remove the CHECK constraint on purchase_history.source,
-- we recreate the table. This migration is safe for empty/new databases.
-- For existing databases with data, run migrate_v1.0_with_data.py instead.

-- Recreate purchase_history without restrictive source CHECK
CREATE TABLE IF NOT EXISTS purchase_history_new (
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

INSERT INTO purchase_history_new SELECT * FROM purchase_history;
DROP TABLE purchase_history;
ALTER TABLE purchase_history_new RENAME TO purchase_history;

-- Recreate indexes
CREATE INDEX IF NOT EXISTS idx_purchase_history_order_id ON purchase_history(order_id);
CREATE INDEX IF NOT EXISTS idx_purchase_history_source_date ON purchase_history(source, purchase_date);
