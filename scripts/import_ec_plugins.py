#!/usr/bin/env python3
"""
Plugin-based EC site CSV importer for Personal Context Engine.

Reads column mappings from config/ec_formats.json and supports
any EC site without code changes — just add a format definition.

Usage:
    python3 import_ec_plugins.py <csv_path> [db_path] [--format FORMAT] [--source SOURCE]

If --format is omitted, auto-detection is attempted based on CSV headers.
"""

import sys
import csv
import sqlite3
import os
import json
import argparse
import re
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
CONFIG_DIR = SCRIPT_DIR.parent / "config"
ENCODING_ORDER_DEFAULT = ["utf-8-sig", "utf-8", "shift_jis", "cp932", "iso-8859-1", "latin-1"]


def load_ec_formats() -> dict:
    """Load EC format definitions from config."""
    config_path = CONFIG_DIR / "ec_formats.json"
    # Fallback: check OpenClaw workspace
    if not config_path.exists():
        config_path = Path.home() / ".openclaw" / "workspace" / "config" / "ec_formats.json"
    if not config_path.exists():
        print(f"Error: ec_formats.json not found")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def detect_encoding(filepath: str, encoding_order: list[str]) -> str:
    """Try multiple encodings and return the first that works."""
    for enc in encoding_order:
        try:
            with open(filepath, "r", encoding=enc) as f:
                f.read(4096)
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue

    # Fallback: try chardet if available
    try:
        import chardet
        with open(filepath, "rb") as f:
            result = chardet.detect(f.read(8192))
        if result["encoding"]:
            return result["encoding"]
    except ImportError:
        pass

    raise ValueError(f"Cannot detect encoding for {filepath}")


def parse_price(price_str: str, currency_symbols: dict) -> tuple[float | None, str]:
    """Parse price string and detect currency. Returns (amount, currency_code)."""
    if not price_str:
        return None, "USD"

    price_str = price_str.strip()
    currency = "USD"  # Default

    # Detect currency from symbol
    for symbol, code in sorted(currency_symbols.items(), key=lambda x: -len(x[0])):
        if symbol in price_str:
            currency = code
            price_str = price_str.replace(symbol, "")
            break

    # Detect JPY from context (no decimal point, or 円 suffix)
    if "円" in price_str:
        currency = "JPY"
        price_str = price_str.replace("円", "")

    cleaned = re.sub(r"[^\d.\-]", "", price_str)
    try:
        return float(cleaned), currency
    except ValueError:
        return None, currency


def parse_date(date_str: str, date_formats: list[str]) -> str | None:
    """Parse date string using provided format list."""
    if not date_str:
        return None
    date_str = date_str.strip()
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Last resort: try ISO format
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        pass
    return None


def match_column(headers: list[str], candidates: list[str]) -> str | None:
    """Find the first matching header from candidate list."""
    header_set = {h.strip() for h in headers}
    for candidate in candidates:
        if candidate in header_set:
            return candidate
    # Case-insensitive fallback
    header_lower = {h.strip().lower(): h.strip() for h in headers}
    for candidate in candidates:
        if candidate.lower() in header_lower:
            return header_lower[candidate.lower()]
    return None


def auto_detect_format(headers: list[str], formats: dict) -> str | None:
    """Auto-detect EC format by matching headers against all format definitions."""
    best_match = None
    best_score = 0

    for format_key, fmt_def in formats.items():
        score = 0
        columns = fmt_def.get("columns", {})
        for _semantic, candidates in columns.items():
            if not candidates:
                continue
            if match_column(headers, candidates):
                score += 1
        if score > best_score:
            best_score = score
            best_match = format_key

    # Require at least 2 column matches
    if best_score >= 2:
        return best_match
    return None


def is_duplicate_by_order(cursor: sqlite3.Cursor, source: str, order_id: str) -> bool:
    cursor.execute(
        "SELECT COUNT(*) FROM purchase_history WHERE order_id = ? AND source = ?",
        (order_id, source),
    )
    return cursor.fetchone()[0] > 0


def is_duplicate_by_composite(
    cursor: sqlite3.Cursor, source: str, item_name: str, purchase_date: str | None, price: float | None
) -> bool:
    cursor.execute(
        """SELECT COUNT(*) FROM purchase_history
           WHERE source = ? AND item_name = ? AND purchase_date = ? AND price = ?""",
        (source, item_name, purchase_date, price),
    )
    return cursor.fetchone()[0] > 0


def import_csv(csv_path: str, db_path: str, format_key: str | None, source_override: str | None) -> dict:
    """Import CSV using plugin format definitions."""
    stats = {"imported": 0, "skipped": 0, "errors": 0, "format": "unknown"}
    config = load_ec_formats()
    formats = config["formats"]
    currency_symbols = config.get("currency_symbols", {})
    encoding_order = config.get("encoding_order", ENCODING_ORDER_DEFAULT)

    encoding = detect_encoding(csv_path, encoding_order)

    with open(csv_path, "r", encoding=encoding) as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            print("Error: CSV has no headers")
            stats["errors"] = 1
            return stats

        headers = [h.strip() for h in reader.fieldnames]

        # Determine format
        if format_key and format_key in formats:
            fmt = formats[format_key]
        else:
            detected = auto_detect_format(headers, formats)
            if detected:
                fmt = formats[detected]
                format_key = detected
                print(f"Auto-detected format: {fmt['name']} ({detected})")
            else:
                # Fall back to generic credit card
                fmt = formats.get("generic_credit_card", {})
                format_key = "generic_credit_card"
                print(f"Could not detect format. Using generic. Headers: {headers}")

        source = source_override or fmt.get("source_key", "manual")
        date_formats = fmt.get("date_formats", ["%Y-%m-%d", "%m/%d/%Y"])
        columns = fmt.get("columns", {})
        stats["format"] = fmt.get("name", format_key)

        # Resolve column mappings
        col_item = match_column(headers, columns.get("item_name", []))
        col_price = match_column(headers, columns.get("price", []))
        col_date = match_column(headers, columns.get("purchase_date", []))
        col_order = match_column(headers, columns.get("order_id", []))
        col_category = match_column(headers, columns.get("category", []))

        print(f"Column mapping: item={col_item}, price={col_price}, date={col_date}, order={col_order}")

        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()

        try:
            for row_num, row in enumerate(reader, start=2):  # start=2 because row 1 is header
                try:
                    item_name = row.get(col_item, "").strip() if col_item else ""
                    price_str = row.get(col_price, "") if col_price else ""
                    price, currency = parse_price(price_str, currency_symbols)
                    purchase_date = parse_date(row.get(col_date, ""), date_formats) if col_date else None
                    order_id = row.get(col_order, "").strip() if col_order else None
                    category = row.get(col_category, "").strip() if col_category else None

                    if not item_name and price is None:
                        continue

                    # Duplicate check
                    if order_id and is_duplicate_by_order(cursor, source, order_id):
                        stats["skipped"] += 1
                        continue
                    elif not order_id and item_name and is_duplicate_by_composite(cursor, source, item_name, purchase_date, price):
                        stats["skipped"] += 1
                        continue

                    raw_data = ",".join(f"{k}={v}" for k, v in row.items())

                    cursor.execute(
                        """INSERT INTO purchase_history
                           (source, item_name, price, currency, purchase_date, order_id, category, raw_data)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (source, item_name, price, currency, purchase_date, order_id, category, raw_data),
                    )
                    stats["imported"] += 1
                except Exception as e:
                    print(f"Warning: Skipping row {row_num}: {e}")
                    stats["errors"] += 1

            conn.commit()
        finally:
            conn.close()

    return stats


def list_formats():
    """Print available format definitions."""
    config = load_ec_formats()
    print("Available EC formats:")
    for key, fmt in config["formats"].items():
        print(f"  {key:25s} — {fmt['name']}")


def main():
    parser = argparse.ArgumentParser(
        description="Plugin-based EC CSV importer for Personal Context Engine"
    )
    parser.add_argument("csv_path", nargs="?", help="Path to the CSV file")
    parser.add_argument("db_path", nargs="?", default=None, help="Path to SQLite database")
    parser.add_argument("--format", "-f", default=None, help="EC format key (e.g. amazon_jp, ebay, rakuten)")
    parser.add_argument("--source", "-s", default=None, help="Override source name in DB")
    parser.add_argument("--list-formats", action="store_true", help="List available formats")
    args = parser.parse_args()

    if args.list_formats:
        list_formats()
        return

    if not args.csv_path:
        parser.print_help()
        sys.exit(1)

    if not os.path.exists(args.csv_path):
        print(f"Error: File not found: {args.csv_path}")
        sys.exit(1)

    default_db = Path.home() / ".openclaw" / "workspace" / "data" / "personal.db"
    db_path = args.db_path or str(default_db)

    if not os.path.exists(db_path):
        print(f"Error: Database not found: {db_path}")
        print("Run setup.sh first to create the database.")
        sys.exit(1)

    print(f"Importing: {args.csv_path}")
    print(f"Database: {db_path}")

    stats = import_csv(args.csv_path, db_path, args.format, args.source)

    print(f"\nImport complete ({stats['format']})")
    print(f"  Imported: {stats['imported']}")
    print(f"  Skipped (duplicate): {stats['skipped']}")
    print(f"  Errors: {stats['errors']}")


if __name__ == "__main__":
    main()
