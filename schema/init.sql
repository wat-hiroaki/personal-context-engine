-- Personal Context Engine — Database Schema
-- SQLite 3

CREATE TABLE IF NOT EXISTS possessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT CHECK(category IN (
        'electronics', 'clothing', 'consumable', 'food', 'supplement',
        'furniture', 'kitchen', 'bathroom', 'office', 'other'
    )),
    brand TEXT,
    purchase_date DATE,
    purchase_price REAL,
    purchase_source TEXT,
    location TEXT,
    condition TEXT NOT NULL DEFAULT 'good' CHECK(condition IN ('new', 'good', 'fair', 'poor')),
    is_consumable BOOLEAN NOT NULL DEFAULT 0,
    estimated_lifespan_days INTEGER,
    last_replenished DATE,
    notes TEXT,
    image_path TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS purchase_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL CHECK(source IN ('amazon', 'rakuten', 'ebay', 'walmart', 'shopify', 'credit_card', 'receipt', 'manual')),
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

CREATE TABLE IF NOT EXISTS consumption_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    possession_id INTEGER NOT NULL,
    event_type TEXT NOT NULL CHECK(event_type IN (
        'opened', 'half_used', 'low', 'empty', 'replaced', 'disposed'
    )),
    logged_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (possession_id) REFERENCES possessions(id)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_possessions_category ON possessions(category);
CREATE INDEX IF NOT EXISTS idx_possessions_location ON possessions(location);
CREATE INDEX IF NOT EXISTS idx_possessions_consumable ON possessions(is_consumable);
CREATE INDEX IF NOT EXISTS idx_purchase_history_order_id ON purchase_history(order_id);
CREATE INDEX IF NOT EXISTS idx_purchase_history_source_date ON purchase_history(source, purchase_date);
CREATE INDEX IF NOT EXISTS idx_consumption_log_possession ON consumption_log(possession_id);
