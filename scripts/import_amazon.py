#!/usr/bin/env python3
"""
Amazon.co.jp 注文履歴CSV → personal.db インポーター

Usage:
    python3 import_amazon.py <csv_path> [db_path]

db_path を省略した場合: ~/.openclaw/workspace/data/personal.db
"""

import sys
import csv
import sqlite3
import os
from pathlib import Path
from datetime import datetime

# Amazon CSV の想定カラム名（日本語版）
AMAZON_COLUMNS = {
    "注文日": "purchase_date",
    "注文番号": "order_id",
    "商品名": "item_name",
    "価格": "price",
    "数量": "quantity",
    "合計": "total",
}

# 英語版カラム名のフォールバック
AMAZON_COLUMNS_EN = {
    "Order Date": "purchase_date",
    "Order ID": "order_id",
    "Title": "item_name",
    "Item Total": "price",
    "Purchase Price Per Unit": "unit_price",
    "Quantity": "quantity",
}

ENCODING_ORDER = ["utf-8-sig", "utf-8", "shift_jis", "cp932"]


def detect_encoding(filepath: str) -> str:
    """Try multiple encodings and return the first that works."""
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
    """Parse price string like '¥2,980' or '2980' to float."""
    if not price_str:
        return None
    cleaned = price_str.replace("¥", "").replace(",", "").replace("￥", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_date(date_str: str) -> str | None:
    """Parse various date formats to YYYY-MM-DD."""
    if not date_str:
        return None
    date_str = date_str.strip()
    formats = [
        "%Y/%m/%d",
        "%Y-%m-%d",
        "%Y年%m月%d日",
        "%m/%d/%Y",
        "%d/%m/%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def detect_column_mapping(headers: list[str]) -> dict[str, str]:
    """Detect whether CSV uses Japanese or English column names."""
    mapping = {}
    # Try Japanese first
    for header in headers:
        header_clean = header.strip()
        if header_clean in AMAZON_COLUMNS:
            mapping[header_clean] = AMAZON_COLUMNS[header_clean]
    if mapping:
        return mapping
    # Try English
    for header in headers:
        header_clean = header.strip()
        if header_clean in AMAZON_COLUMNS_EN:
            mapping[header_clean] = AMAZON_COLUMNS_EN[header_clean]
    return mapping


def is_duplicate(cursor: sqlite3.Cursor, order_id: str) -> bool:
    """Check if order_id already exists in purchase_history."""
    cursor.execute(
        "SELECT COUNT(*) FROM purchase_history WHERE order_id = ? AND source = 'amazon'",
        (order_id,),
    )
    return cursor.fetchone()[0] > 0


def import_amazon_csv(csv_path: str, db_path: str) -> dict:
    """Import Amazon CSV into purchase_history table."""
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
            print(f"Error: Cannot detect Amazon CSV format. Headers: {reader.fieldnames}")
            conn.close()
            stats["errors"] = 1
            return stats

        # Reverse map: semantic name -> csv header
        rev_map: dict[str, str] = {v: k for k, v in col_map.items()}

        for row in reader:
            try:
                order_id = row.get(rev_map.get("order_id", ""), "").strip()
                if order_id and is_duplicate(cursor, order_id):
                    stats["skipped"] += 1
                    continue

                item_name = row.get(rev_map.get("item_name", ""), "").strip()
                price_key = rev_map.get("price") or rev_map.get("unit_price", "")
                price = parse_price(row.get(price_key, ""))
                purchase_date = parse_date(row.get(rev_map.get("purchase_date", ""), ""))

                raw_data = ",".join(f"{k}={v}" for k, v in row.items())

                cursor.execute(
                    """INSERT INTO purchase_history
                       (source, item_name, price, currency, purchase_date, order_id, raw_data)
                       VALUES ('amazon', ?, ?, 'JPY', ?, ?, ?)""",
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
        print("Usage: python3 import_amazon.py <csv_path> [db_path]")
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

    print(f"Importing Amazon CSV: {csv_path}")
    print(f"Database: {db_path}")

    stats = import_amazon_csv(csv_path, db_path)

    print(f"\nImport complete (Amazon)")
    print(f"  Imported: {stats['imported']}")
    print(f"  Skipped (duplicate): {stats['skipped']}")
    print(f"  Errors: {stats['errors']}")


if __name__ == "__main__":
    main()
