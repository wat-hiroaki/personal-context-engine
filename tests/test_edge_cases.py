"""Edge case tests: empty files, malformed data, Unicode, large values."""
import csv
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


def _write_csv(tmp_path, filename, headers, rows, encoding="utf-8"):
    filepath = tmp_path / filename
    with open(filepath, "w", encoding=encoding, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return str(filepath)


class TestEmptyAndMalformedCSV:
    def test_empty_csv_header_only(self, db_path, tmp_path):
        from import_amazon import import_amazon_csv
        csv_path = _write_csv(tmp_path, "empty.csv", ["注文日", "注文番号", "商品名", "価格"], [])
        stats = import_amazon_csv(csv_path, db_path)
        assert stats["imported"] == 0
        assert stats["errors"] == 0

    def test_csv_no_headers(self, db_path, tmp_path):
        filepath = tmp_path / "noheader.csv"
        filepath.write_text("")
        from import_amazon import import_amazon_csv
        stats = import_amazon_csv(str(filepath), db_path)
        assert stats["errors"] == 1

    def test_csv_extra_columns_ignored(self, db_path, tmp_path):
        from import_amazon import import_amazon_csv
        csv_path = _write_csv(tmp_path, "extra.csv",
            ["注文日", "注文番号", "商品名", "価格", "不明カラム"],
            [{"注文日": "2026/01/15", "注文番号": "X-001", "商品名": "Test", "価格": "100", "不明カラム": "foo"}]
        )
        stats = import_amazon_csv(csv_path, db_path)
        assert stats["imported"] == 1

    def test_csv_missing_price_column(self, db_path, tmp_path):
        """CSV with recognized headers but missing price — should still import."""
        from import_amazon import import_amazon_csv
        csv_path = _write_csv(tmp_path, "noprice.csv",
            ["注文日", "注文番号", "商品名"],
            [{"注文日": "2026/01/15", "注文番号": "NP-001", "商品名": "No Price Item"}]
        )
        stats = import_amazon_csv(csv_path, db_path)
        assert stats["imported"] == 1

    def test_generic_all_rows_error(self, db_path, tmp_path):
        """When all rows fail, errors count should match."""
        from import_ec_plugins import import_csv
        # Create CSV with wrong format that triggers per-row errors
        csv_path = _write_csv(tmp_path, "bad.csv",
            ["col1", "col2"],
            [{"col1": "", "col2": ""}]
        )
        stats = import_csv(csv_path, db_path, None, None)
        # Empty item_name + None price → row skipped (not an error)
        assert stats["errors"] == 0


class TestUnicodeEdgeCases:
    def test_japanese_full_width_numbers(self, db_path, tmp_path):
        from import_ec_plugins import import_csv
        csv_path = _write_csv(tmp_path, "fw.csv",
            ["注文日", "注文番号", "商品名", "価格"],
            [{"注文日": "2026/01/15", "注文番号": "FW-001", "商品名": "全角テスト", "価格": "¥1,000"}]
        )
        stats = import_csv(csv_path, db_path, "amazon_jp", None)
        assert stats["imported"] == 1

    def test_emoji_in_item_name(self, db_path, tmp_path):
        from import_ec_plugins import import_csv
        csv_path = _write_csv(tmp_path, "emoji.csv",
            ["注文日", "注文番号", "商品名", "価格"],
            [{"注文日": "2026/01/15", "注文番号": "EM-001", "商品名": "🎉 パーティーグッズ", "価格": "500"}]
        )
        stats = import_csv(csv_path, db_path, "amazon_jp", None)
        assert stats["imported"] == 1
        conn = sqlite3.connect(db_path)
        name = conn.execute("SELECT item_name FROM purchase_history WHERE order_id = 'EM-001'").fetchone()[0]
        conn.close()
        assert "🎉" in name


class TestShiftJISEncoding:
    def test_shift_jis_csv(self, db_path, tmp_path):
        """Test Shift-JIS encoded CSV (common for Japanese EC exports)."""
        from import_amazon import import_amazon_csv
        filepath = tmp_path / "sjis.csv"
        with open(filepath, "w", encoding="shift_jis", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["注文日", "注文番号", "商品名", "価格"])
            writer.writeheader()
            writer.writerow({"注文日": "2026/03/01", "注文番号": "SJ-001", "商品名": "テスト商品", "価格": "1500"})
        stats = import_amazon_csv(str(filepath), db_path)
        assert stats["imported"] == 1


class TestBootstrap:
    def test_parse_item_line_basic(self):
        from bootstrap import parse_item_line
        item = parse_item_line("Rice cooker", "kitchen")
        assert item is not None
        assert item["name"] == "Rice cooker"
        assert item["category"] == "kitchen"
        assert item["is_consumable"] == 0

    def test_parse_item_line_with_brand(self):
        from bootstrap import parse_item_line
        item = parse_item_line("Protein / SAVAS", "supplement")
        assert item["name"] == "Protein"
        assert item["brand"] == "SAVAS"
        assert item["is_consumable"] == 1
        assert item["estimated_lifespan_days"] == 60

    def test_parse_item_line_empty(self):
        from bootstrap import parse_item_line
        assert parse_item_line("", "kitchen") is None
        assert parse_item_line("   ", "kitchen") is None

    def test_insert_items(self, db_conn):
        from bootstrap import insert_items
        items = [
            {"name": "Test", "category": "kitchen", "brand": None, "is_consumable": 0, "estimated_lifespan_days": None},
            {"name": "Soap", "category": "bathroom", "brand": "Dove", "is_consumable": 1, "estimated_lifespan_days": 90},
        ]
        count = insert_items(db_conn, items)
        assert count == 2
        rows = db_conn.execute("SELECT COUNT(*) FROM possessions").fetchone()[0]
        assert rows == 2

    def test_insert_items_skips_duplicates(self, db_conn):
        from bootstrap import insert_items
        items = [
            {"name": "Knife", "category": "kitchen", "brand": None, "is_consumable": 0, "estimated_lifespan_days": None},
        ]
        insert_items(db_conn, items)
        # Insert again — should skip
        count = insert_items(db_conn, items)
        assert count == 0
        rows = db_conn.execute("SELECT COUNT(*) FROM possessions WHERE name = 'Knife'").fetchone()[0]
        assert rows == 1


class TestGenericCsvCurrency:
    def test_usd_currency_detected(self, db_path, tmp_path):
        """Generic CSV with $ should detect USD, not hardcode JPY."""
        from import_csv_generic import import_generic_csv
        csv_path = _write_csv(tmp_path, "usd.csv",
            ["日付", "利用先", "金額"],
            [{"日付": "2026/01/15", "利用先": "Amazon US", "金額": "$29.99"}]
        )
        stats = import_generic_csv(csv_path, db_path, "credit_card")
        assert stats["imported"] == 1
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT currency, price FROM purchase_history WHERE item_name = 'Amazon US'").fetchone()
        conn.close()
        assert row[0] == "USD"
        assert abs(row[1] - 29.99) < 0.01

    def test_jpy_currency_detected(self, db_path, tmp_path):
        """Generic CSV with ¥ should detect JPY."""
        from import_csv_generic import import_generic_csv
        csv_path = _write_csv(tmp_path, "jpy.csv",
            ["日付", "利用先", "金額"],
            [{"日付": "2026/02/01", "利用先": "コンビニ", "金額": "¥500"}]
        )
        stats = import_generic_csv(csv_path, db_path, "credit_card")
        assert stats["imported"] == 1
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT currency FROM purchase_history WHERE item_name = 'コンビニ'").fetchone()
        conn.close()
        assert row[0] == "JPY"


class TestMigrationIdempotency:
    def test_schema_applied_twice(self):
        """Running all migrations twice should not fail or duplicate data."""
        from conftest import _apply_schema
        conn = sqlite3.connect(":memory:")
        _apply_schema(conn)
        # Apply again — should not raise
        _apply_schema(conn)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'"
        ).fetchall()
        table_names = sorted(t[0] for t in tables)
        assert "purchase_history" in table_names
        assert "schema_version" in table_names
        conn.close()


class TestCommonModule:
    def test_detect_encoding_utf8(self, tmp_path):
        from common import detect_encoding
        f = tmp_path / "utf8.csv"
        f.write_text("hello,world\n", encoding="utf-8")
        assert detect_encoding(str(f)) == "utf-8-sig" or detect_encoding(str(f)) == "utf-8"

    def test_detect_encoding_unknown_raises(self, tmp_path):
        import pytest
        from common import detect_encoding
        f = tmp_path / "binary.dat"
        f.write_bytes(bytes(range(128, 256)) * 100)  # Invalid for utf-8/shift_jis/cp932
        with pytest.raises(ValueError):
            detect_encoding(str(f))

    def test_load_json_config_not_found(self):
        import pytest
        from common import load_json_config
        with pytest.raises(FileNotFoundError):
            load_json_config("nonexistent_file.json")
