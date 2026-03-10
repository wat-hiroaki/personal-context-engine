-- Personal Context Engine — Migration v0.2
-- Adds receipt support and video cataloger metadata

-- Receipt scans table
CREATE TABLE IF NOT EXISTS receipt_scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_path TEXT NOT NULL,
    store_name TEXT,
    total_amount REAL,
    currency TEXT NOT NULL DEFAULT 'JPY',
    receipt_date DATE,
    ocr_raw_text TEXT,
    ocr_confidence REAL,
    language TEXT DEFAULT 'ja',
    processed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Receipt line items (individual items from a receipt)
CREATE TABLE IF NOT EXISTS receipt_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_id INTEGER NOT NULL,
    item_name TEXT NOT NULL,
    price REAL,
    quantity INTEGER DEFAULT 1,
    purchase_history_id INTEGER,
    FOREIGN KEY (receipt_id) REFERENCES receipt_scans(id),
    FOREIGN KEY (purchase_history_id) REFERENCES purchase_history(id)
);

-- Video catalog sessions
CREATE TABLE IF NOT EXISTS video_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_path TEXT NOT NULL,
    frame_count INTEGER,
    has_audio BOOLEAN DEFAULT 0,
    audio_transcript TEXT,
    items_detected INTEGER DEFAULT 0,
    items_confirmed INTEGER DEFAULT 0,
    processed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_receipt_scans_date ON receipt_scans(receipt_date);
CREATE INDEX IF NOT EXISTS idx_receipt_items_receipt ON receipt_items(receipt_id);
CREATE INDEX IF NOT EXISTS idx_video_sessions_date ON video_sessions(processed_at);
