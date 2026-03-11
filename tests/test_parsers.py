"""Test price and date parsing functions across all importers."""
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


class TestAmazonParser:
    def test_parse_price_yen_symbol(self):
        from import_amazon import parse_price
        assert parse_price("¥2,980") == 2980.0

    def test_parse_price_fullwidth_yen(self):
        from import_amazon import parse_price
        assert parse_price("￥1,234") == 1234.0

    def test_parse_price_plain_number(self):
        from import_amazon import parse_price
        assert parse_price("500") == 500.0

    def test_parse_price_empty(self):
        from import_amazon import parse_price
        assert parse_price("") is None

    def test_parse_price_invalid(self):
        from import_amazon import parse_price
        assert parse_price("abc") is None

    def test_parse_date_slash(self):
        from import_amazon import parse_date
        assert parse_date("2026/03/10") == "2026-03-10"

    def test_parse_date_iso(self):
        from import_amazon import parse_date
        assert parse_date("2026-03-10") == "2026-03-10"

    def test_parse_date_japanese(self):
        from import_amazon import parse_date
        assert parse_date("2026年3月10日") == "2026-03-10"

    def test_parse_date_us_format(self):
        from import_amazon import parse_date
        assert parse_date("03/10/2026") == "2026-03-10"

    def test_parse_date_empty(self):
        from import_amazon import parse_date
        assert parse_date("") is None

    def test_detect_jp_columns(self):
        from import_amazon import detect_column_mapping
        headers = ["注文日", "注文番号", "商品名", "価格"]
        mapping = detect_column_mapping(headers)
        assert "注文日" in mapping
        assert mapping["注文日"] == "purchase_date"

    def test_detect_en_columns(self):
        from import_amazon import detect_column_mapping
        headers = ["Order Date", "Order ID", "Title", "Item Total"]
        mapping = detect_column_mapping(headers)
        assert "Order Date" in mapping


class TestGenericParser:
    def test_parse_price_negative_minus(self):
        from import_csv_generic import parse_price
        assert parse_price("-1,000") == -1000.0

    def test_parse_price_negative_parens(self):
        from import_csv_generic import parse_price
        assert parse_price("(500)") == -500.0

    def test_parse_price_yen(self):
        from import_csv_generic import parse_price
        assert parse_price("¥3,500") == 3500.0

    def test_parse_price_dollar(self):
        from import_csv_generic import parse_price
        assert parse_price("$12.99") == 12.99

    def test_parse_price_en_suffix(self):
        from import_csv_generic import parse_price
        assert parse_price("2,000円") == 2000.0

    def test_parse_price_plain_negative(self):
        from import_csv_generic import parse_price
        assert parse_price("-500") == -500.0

    def test_auto_detect_mapping_jp(self):
        from import_csv_generic import auto_detect_mapping
        headers = ["日付", "利用先", "金額"]
        mapping = auto_detect_mapping(headers)
        assert "purchase_date" in mapping
        assert "item_name" in mapping
        assert "price" in mapping

    def test_auto_detect_mapping_en(self):
        from import_csv_generic import auto_detect_mapping
        headers = ["date", "merchant", "amount"]
        mapping = auto_detect_mapping(headers)
        assert "purchase_date" in mapping
        assert "item_name" in mapping
        assert "price" in mapping


class TestCommonParser:
    """Tests for shared common.py parsing functions."""

    def test_parse_price_usd(self):
        from common import parse_price_generic
        amount, currency = parse_price_generic("$29.99", {"$": "USD", "¥": "JPY"})
        assert amount == 29.99
        assert currency == "USD"

    def test_parse_price_jpy(self):
        from common import parse_price_generic
        amount, currency = parse_price_generic("¥2,980", {"$": "USD", "¥": "JPY"})
        assert amount == 2980.0
        assert currency == "JPY"

    def test_parse_price_yen_suffix(self):
        from common import parse_price_generic
        amount, currency = parse_price_generic("1,500円", {"$": "USD", "¥": "JPY"})
        assert amount == 1500.0
        assert currency == "JPY"

    def test_parse_price_negative(self):
        from common import parse_price_generic
        amount, currency = parse_price_generic("-$15.00", {"$": "USD"})
        assert amount == -15.0
        assert currency == "USD"

    def test_parse_price_empty(self):
        from common import parse_price_generic
        amount, currency = parse_price_generic("", {})
        assert amount is None

    def test_parse_date_iso(self):
        from common import parse_date_multi
        assert parse_date_multi("2026-03-10", ["%Y-%m-%d"]) == "2026-03-10"

    def test_parse_date_slash(self):
        from common import parse_date_multi
        assert parse_date_multi("2026/03/10", ["%Y/%m/%d"]) == "2026-03-10"

    def test_parse_date_empty(self):
        from common import parse_date_multi
        assert parse_date_multi("", ["%Y-%m-%d"]) is None

    def test_row_to_json(self):
        from common import row_to_json
        import json
        row = {"name": "Test", "price": "100"}
        result = json.loads(row_to_json(row))
        assert result["name"] == "Test"
        assert result["price"] == "100"


class TestEcPluginParser:

    def test_auto_detect_amazon_jp(self):
        from import_ec_plugins import auto_detect_format, load_ec_formats
        config = load_ec_formats()
        headers = ["注文日", "注文番号", "商品名", "価格", "数量"]
        result = auto_detect_format(headers, config["formats"])
        assert result == "amazon_jp"

    def test_auto_detect_ebay(self):
        from import_ec_plugins import auto_detect_format, load_ec_formats
        config = load_ec_formats()
        headers = ["Item title", "Sale price", "Sale date", "Order number"]
        result = auto_detect_format(headers, config["formats"])
        assert result == "ebay"

    def test_match_column_case_insensitive(self):
        from import_ec_plugins import match_column
        headers = ["ORDER DATE", "title", "PRICE"]
        assert match_column(headers, ["Order Date"]) == "ORDER DATE"
