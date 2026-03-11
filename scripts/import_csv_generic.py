#!/usr/bin/env python3
"""
汎用CSV → personal.db インポーター
クレジットカード明細やその他CSVフォーマットに対応。

Usage:
    python3 import_csv_generic.py <csv_path> [db_path] [--source SOURCE]

Options:
    --source    データソース名 (credit_card, receipt, manual)。デフォルト: credit_card

カラムマッピングは対話的に行う。初回はヘッダーを表示し、
ユーザーにマッピングを確認する。
"""

import sys
import csv
import sqlite3
import os
import argparse
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from common import detect_encoding as _detect_encoding, parse_price_generic, parse_date_multi, row_to_json

ENCODING_ORDER = ["utf-8-sig", "utf-8", "shift_jis", "cp932"]

DATE_FORMATS = [
    "%Y/%m/%d",
    "%Y-%m-%d",
    "%Y年%m月%d日",
    "%m/%d/%Y",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
]

# よくあるクレカ明細のカラム名パターン
COMMON_MAPPINGS = {
    "item_name": ["商品名", "利用先", "摘要", "内容", "明細", "店名", "description", "merchant"],
    "price": ["金額", "利用金額", "支払金額", "請求金額", "price", "amount"],
    "purchase_date": ["日付", "利用日", "利用年月日", "取引日", "date", "transaction_date"],
    "order_id": ["注文番号", "管理番号", "order_id", "reference"],
}


def detect_encoding(filepath: str) -> str:
    return _detect_encoding(filepath, ENCODING_ORDER)


def parse_price(price_str: str) -> tuple[float | None, str]:
    """Parse price and detect currency using common module."""
    return parse_price_generic(price_str)


def parse_date(date_str: str) -> str | None:
    """Parse date using common module."""
    return parse_date_multi(date_str, DATE_FORMATS)


def auto_detect_mapping(headers: list[str]) -> dict[str, str]:
    """Try to auto-detect column mapping from common patterns."""
    mapping: dict[str, str] = {}
    for semantic, patterns in COMMON_MAPPINGS.items():
        for header in headers:
            h = header.strip()
            if h in patterns or h.lower() in [p.lower() for p in patterns]:
                mapping[semantic] = h
                break
    return mapping


def is_duplicate(cursor: sqlite3.Cursor, source: str, item_name: str, purchase_date: str | None, price: float | None) -> bool:
    """Check for duplicates using composite key (no order_id available)."""
    cursor.execute(
        """SELECT COUNT(*) FROM purchase_history
           WHERE source = ? AND item_name = ? AND purchase_date = ? AND price = ?""",
        (source, item_name, purchase_date, price),
    )
    return cursor.fetchone()[0] > 0


def import_generic_csv(csv_path: str, db_path: str, source: str) -> dict:
    stats = {"imported": 0, "skipped": 0, "errors": 0}

    encoding = detect_encoding(csv_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()

        with open(csv_path, "r", encoding=encoding) as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                print("Error: CSV has no headers")
                stats["errors"] = 1
                return stats

            headers = [h.strip() for h in reader.fieldnames]
            mapping = auto_detect_mapping(headers)

            if "item_name" not in mapping and "price" not in mapping:
                print("Warning: Could not auto-detect column mapping.")
                print(f"Available columns: {headers}")
                print(f"Detected mapping: {mapping}")
                print("Will import with available data.")
            for row_num, row in enumerate(reader, start=2):  # start=2 because row 1 is header
                try:
                    item_name = row.get(mapping.get("item_name", ""), "").strip()
                    price, currency = parse_price(row.get(mapping.get("price", ""), ""))
                    purchase_date = parse_date(row.get(mapping.get("purchase_date", ""), ""))
                    order_id = row.get(mapping.get("order_id", ""), "").strip() or None

                    # Skip empty rows
                    if not item_name and price is None:
                        continue

                    # Duplicate check
                    if order_id:
                        cursor.execute(
                            "SELECT COUNT(*) FROM purchase_history WHERE order_id = ? AND source = ?",
                            (order_id, source),
                        )
                        if cursor.fetchone()[0] > 0:
                            stats["skipped"] += 1
                            continue
                    elif item_name and is_duplicate(cursor, source, item_name, purchase_date, price):
                        stats["skipped"] += 1
                        continue

                    raw_data = row_to_json(row)

                    cursor.execute(
                        """INSERT INTO purchase_history
                           (source, item_name, price, currency, purchase_date, order_id, raw_data)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (source, item_name, price, currency, purchase_date, order_id, raw_data),
                    )
                    stats["imported"] += 1
                except Exception as e:
                    print(f"Warning: Skipping row {row_num}: {e}")
                    stats["errors"] += 1

        conn.commit()
    finally:
        conn.close()
    return stats


def main():
    parser = argparse.ArgumentParser(description="Generic CSV importer for Personal Context Engine")
    parser.add_argument("csv_path", help="Path to the CSV file")
    parser.add_argument("db_path", nargs="?", default=None, help="Path to SQLite database")
    parser.add_argument("--source", default="credit_card", choices=["credit_card", "receipt", "manual"],
                        help="Data source type (default: credit_card)")
    args = parser.parse_args()

    if not os.path.exists(args.csv_path):
        print(f"Error: File not found: {args.csv_path}")
        sys.exit(1)

    default_db = Path.home() / ".openclaw" / "workspace" / "data" / "personal.db"
    db_path = args.db_path or str(default_db)

    if not os.path.exists(db_path):
        print(f"Error: Database not found: {db_path}")
        print("Run setup.sh first to create the database.")
        sys.exit(1)

    print(f"Importing CSV: {args.csv_path}")
    print(f"Source: {args.source}")
    print(f"Database: {db_path}")

    stats = import_generic_csv(args.csv_path, db_path, args.source)

    print(f"\nImport complete ({args.source})")
    print(f"  Imported: {stats['imported']}")
    print(f"  Skipped (duplicate): {stats['skipped']}")
    print(f"  Errors: {stats['errors']}")


if __name__ == "__main__":
    main()
