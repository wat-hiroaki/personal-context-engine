#!/usr/bin/env python3
"""
楽天市場 購入履歴CSV → personal.db インポーター

Usage:
    python3 import_rakuten.py <csv_path> [db_path]

db_path を省略した場合: ~/.openclaw/workspace/data/personal.db
"""

import sys
import csv
import sqlite3
import os
from pathlib import Path
from datetime import datetime

RAKUTEN_COLUMNS = {
    "注文日時": "purchase_date",
    "注文番号": "order_id",
    "商品名": "item_name",
    "商品価格": "price",
    "個数": "quantity",
    "送料": "shipping",
    "ショップ名": "shop",
}

RAKUTEN_COLUMNS_ALT = {
    "注文日": "purchase_date",
    "受注番号": "order_id",
    "商品名称": "item_name",
    "金額": "price",
    "数量": "quantity",
}

ENCODING_ORDER = ["utf-8-sig", "utf-8", "shift_jis", "cp932"]


def detect_encoding(filepath: str) -> str:
    for enc in ENCODING_ORDER:
        try:
            with open(filepath, "r", encoding=enc) as f:
                f.read(1024)
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError(
        f"Cannot detect encoding for {filepath}. "
        f"Tried: {', '.join(ENCODING_ORDER)}"
    )


def parse_price(price_str: str) -> float | None:
    if not price_str:
        return None
    cleaned = price_str.replace("¥", "").replace(",", "").replace("￥", "").replace("円", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_date(date_str: str) -> str | None:
    if not date_str:
        return None
    date_str = date_str.strip()
    formats = [
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y年%m月%d日",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def detect_column_mapping(headers: list[str]) -> dict[str, str]:
    mapping = {}
    for header in headers:
        h = header.strip()
        if h in RAKUTEN_COLUMNS:
            mapping[h] = RAKUTEN_COLUMNS[h]
    if mapping:
        return mapping
    for header in headers:
        h = header.strip()
        if h in RAKUTEN_COLUMNS_ALT:
            mapping[h] = RAKUTEN_COLUMNS_ALT[h]
    return mapping


def is_duplicate(cursor: sqlite3.Cursor, order_id: str) -> bool:
    cursor.execute(
        "SELECT COUNT(*) FROM purchase_history WHERE order_id = ? AND source = 'rakuten'",
        (order_id,),
    )
    return cursor.fetchone()[0] > 0


def import_rakuten_csv(csv_path: str, db_path: str) -> dict:
    stats = {"imported": 0, "skipped": 0, "errors": 0}

    encoding = detect_encoding(csv_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    with open(csv_path, "r", encoding=encoding) as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            print("Error: CSV has no headers")
            conn.close()
            stats["errors"] = 1
            return stats

        col_map = detect_column_mapping(reader.fieldnames)
        if not col_map:
            print(f"Error: Cannot detect Rakuten CSV format. Headers: {reader.fieldnames}")
            conn.close()
            stats["errors"] = 1
            return stats

        rev_map: dict[str, str] = {v: k for k, v in col_map.items()}

        for row in reader:
            try:
                order_id = row.get(rev_map.get("order_id", ""), "").strip()
                if order_id and is_duplicate(cursor, order_id):
                    stats["skipped"] += 1
                    continue

                item_name = row.get(rev_map.get("item_name", ""), "").strip()
                price = parse_price(row.get(rev_map.get("price", ""), ""))
                purchase_date = parse_date(row.get(rev_map.get("purchase_date", ""), ""))

                raw_data = ",".join(f"{k}={v}" for k, v in row.items())

                cursor.execute(
                    """INSERT INTO purchase_history
                       (source, item_name, price, currency, purchase_date, order_id, raw_data)
                       VALUES ('rakuten', ?, ?, 'JPY', ?, ?, ?)""",
                    (item_name, price, purchase_date, order_id, raw_data),
                )
                stats["imported"] += 1
            except Exception as e:
                print(f"Warning: Skipping row due to error: {e}")
                stats["errors"] += 1

    conn.commit()
    conn.close()
    return stats


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 import_rakuten.py <csv_path> [db_path]")
        sys.exit(1)

    csv_path = sys.argv[1]
    if not os.path.exists(csv_path):
        print(f"Error: File not found: {csv_path}")
        sys.exit(1)

    default_db = Path.home() / ".openclaw" / "workspace" / "data" / "personal.db"
    db_path = sys.argv[2] if len(sys.argv) > 2 else str(default_db)

    if not os.path.exists(db_path):
        print(f"Error: Database not found: {db_path}")
        print("Run setup.sh first to create the database.")
        sys.exit(1)

    print(f"Importing Rakuten CSV: {csv_path}")
    print(f"Database: {db_path}")

    stats = import_rakuten_csv(csv_path, db_path)

    print(f"\nImport complete (Rakuten)")
    print(f"  Imported: {stats['imported']}")
    print(f"  Skipped (duplicate): {stats['skipped']}")
    print(f"  Errors: {stats['errors']}")


if __name__ == "__main__":
    main()
