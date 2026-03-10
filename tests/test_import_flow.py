"""Integration tests for CSV import flows."""
import csv
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


def _write_csv(tmp_path, filename, headers, rows, encoding="utf-8"):
    """Helper to create test CSV files."""
    filepath = tmp_path / filename
    with open(filepath, "w", encoding=encoding, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return str(filepath)


class TestAmazonImport:
    def test_import_jp_csv(self, db_path, tmp_path):
        from import_amazon import import_amazon_csv
        csv_path = _write_csv(tmp_path, "amazon.csv",
            ["注文日", "注文番号", "商品名", "価格"],
            [
                {"注文日": "2026/01/15", "注文番号": "123-456", "商品名": "テスト商品", "価格": "¥1,500"},
                {"注文日": "2026/02/20", "注文番号": "789-012", "商品名": "Test Item", "価格": "¥3,000"},
            ]
        )
        stats = import_amazon_csv(csv_path, db_path)
        assert stats["imported"] == 2
        assert stats["errors"] == 0

    def test_duplicate_detection(self, db_path, tmp_path):
        from import_amazon import import_amazon_csv
        csv_path = _write_csv(tmp_path, "amazon.csv",
            ["注文日", "注文番号", "商品名", "価格"],
            [{"注文日": "2026/01/15", "注文番号": "DUP-001", "商品名": "Dup Item", "価格": "500"}]
        )
        import_amazon_csv(csv_path, db_path)
        stats = import_amazon_csv(csv_path, db_path)
        assert stats["skipped"] == 1
        assert stats["imported"] == 0

    def test_en_csv_uses_usd(self, db_path, tmp_path):
        from import_amazon import import_amazon_csv
        csv_path = _write_csv(tmp_path, "amazon_us.csv",
            ["Order Date", "Order ID", "Title", "Item Total"],
            [{"Order Date": "01/15/2026", "Order ID": "US-001", "Title": "USB Cable", "Item Total": "$9.99"}]
        )
        stats = import_amazon_csv(csv_path, db_path)
        assert stats["imported"] == 1
        conn = sqlite3.connect(db_path)
        currency = conn.execute("SELECT currency FROM purchase_history WHERE order_id = 'US-001'").fetchone()[0]
        conn.close()
        assert currency == "USD"


class TestEcPluginImport:
    def test_import_with_auto_detect(self, db_path, tmp_path):
        from import_ec_plugins import import_csv
        csv_path = _write_csv(tmp_path, "orders.csv",
            ["Item title", "Sale price", "Sale date", "Order number"],
            [{"Item title": "Vintage Lamp", "Sale price": "$45.00", "Sale date": "Mar-10-26", "Order number": "EB-001"}]
        )
        stats = import_csv(csv_path, db_path, None, None)
        assert stats["imported"] == 1

    def test_duplicate_by_order_id(self, db_path, tmp_path):
        from import_ec_plugins import import_csv
        csv_path = _write_csv(tmp_path, "orders.csv",
            ["Item title", "Sale price", "Order number"],
            [{"Item title": "Item A", "Sale price": "$10.00", "Order number": "DUP-001"}]
        )
        import_csv(csv_path, db_path, "ebay", None)
        stats = import_csv(csv_path, db_path, "ebay", None)
        assert stats["skipped"] == 1


class TestGenericImport:
    def test_import_credit_card_jp(self, db_path, tmp_path):
        from import_csv_generic import import_generic_csv
        csv_path = _write_csv(tmp_path, "card.csv",
            ["日付", "利用先", "金額"],
            [{"日付": "2026/03/01", "利用先": "コンビニ", "金額": "550"}]
        )
        stats = import_generic_csv(csv_path, db_path, "credit_card")
        assert stats["imported"] == 1

    def test_negative_price_preserved(self, db_path, tmp_path):
        from import_csv_generic import import_generic_csv
        csv_path = _write_csv(tmp_path, "card.csv",
            ["日付", "利用先", "金額"],
            [{"日付": "2026/03/01", "利用先": "返金", "金額": "-1000"}]
        )
        stats = import_generic_csv(csv_path, db_path, "credit_card")
        assert stats["imported"] == 1
        conn = sqlite3.connect(db_path)
        price = conn.execute("SELECT price FROM purchase_history WHERE item_name = '返金'").fetchone()[0]
        conn.close()
        assert price == -1000.0
