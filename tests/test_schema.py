"""Test database schema integrity."""
import sqlite3


def test_all_tables_created(db_conn):
    tables = db_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'"
    ).fetchall()
    table_names = sorted(t[0] for t in tables)
    assert table_names == [
        "consumption_log",
        "possessions",
        "purchase_history",
        "receipt_items",
        "receipt_scans",
        "video_sessions",
    ]


def test_purchase_history_accepts_all_sources(db_conn):
    valid_sources = ["amazon", "rakuten", "ebay", "walmart", "shopify", "credit_card", "receipt", "manual"]
    for source in valid_sources:
        db_conn.execute(
            "INSERT INTO purchase_history (source, item_name, price) VALUES (?, ?, ?)",
            (source, f"test_{source}", 100.0),
        )
    db_conn.commit()
    count = db_conn.execute("SELECT COUNT(*) FROM purchase_history").fetchone()[0]
    assert count == len(valid_sources)


def test_purchase_history_accepts_custom_source(db_conn):
    """v1.0: source CHECK constraint removed — any source string is valid."""
    db_conn.execute(
        "INSERT INTO purchase_history (source, item_name) VALUES ('custom_store', 'test')"
    )
    db_conn.commit()
    row = db_conn.execute(
        "SELECT source FROM purchase_history WHERE item_name = 'test'"
    ).fetchone()
    assert row[0] == "custom_store"


def test_purchase_history_has_created_at(db_conn):
    db_conn.execute(
        "INSERT INTO purchase_history (source, item_name) VALUES ('manual', 'test')"
    )
    db_conn.commit()
    row = db_conn.execute("SELECT created_at FROM purchase_history WHERE item_name = 'test'").fetchone()
    assert row[0] is not None


def test_foreign_key_enforcement(db_conn):
    import pytest
    with pytest.raises(sqlite3.IntegrityError):
        db_conn.execute(
            "INSERT INTO consumption_log (possession_id, event_type) VALUES (99999, 'opened')"
        )


def test_receipt_scans_has_image_hash(db_conn):
    """v1.0: receipt_scans has image_hash column for duplicate detection."""
    db_conn.execute(
        "INSERT INTO receipt_scans (image_path, image_hash) VALUES ('test.jpg', 'abc123')"
    )
    db_conn.commit()
    row = db_conn.execute(
        "SELECT image_hash FROM receipt_scans WHERE image_path = 'test.jpg'"
    ).fetchone()
    assert row[0] == "abc123"


def test_receipt_items_name_not_null(db_conn):
    import pytest
    # First insert a receipt scan
    db_conn.execute(
        "INSERT INTO receipt_scans (image_path) VALUES ('test.jpg')"
    )
    db_conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        db_conn.execute(
            "INSERT INTO receipt_items (receipt_id, item_name) VALUES (1, NULL)"
        )
