#!/usr/bin/env python3
"""
Personal Context Engine — Initial Data Bootstrap Wizard

Interactive CLI wizard to quickly populate the database with initial possessions.
Walks through categories one by one; user enters items one per line.

Usage:
    python3 bootstrap.py [--db-path PATH]
    echo "kitchen:Rice cooker\nsupplement:Protein" | python3 bootstrap.py --non-interactive

No external dependencies (stdlib + sqlite3 only).
"""

import sys
import os
import sqlite3
import argparse
from pathlib import Path
from datetime import date

CATEGORIES = [
    ("kitchen", "Kitchen (キッチン)", False),
    ("bathroom", "Bathroom (バスルーム)", True),
    ("electronics", "Electronics (電子機器)", False),
    ("clothing", "Clothing (衣類)", False),
    ("supplement", "Supplements (サプリメント)", True),
    ("food", "Food (食品)", True),
    ("office", "Office (オフィス)", False),
    ("other", "Other (その他)", False),
]

# Categories whose items are auto-detected as consumable
CONSUMABLE_CATEGORIES = {"bathroom", "supplement", "food"}

# Default estimated lifespan days per consumable category
CONSUMABLE_DEFAULTS = {
    "bathroom": 90,
    "supplement": 60,
    "food": 14,
}


def parse_item_line(line: str, default_category: str) -> dict | None:
    """Parse an item line. Supports 'name' or 'name / brand' format."""
    line = line.strip()
    if not line:
        return None

    name = line
    brand = None

    if " / " in line:
        parts = line.split(" / ", 1)
        name = parts[0].strip()
        brand = parts[1].strip()

    if not name:
        return None

    is_consumable = default_category in CONSUMABLE_CATEGORIES
    lifespan = CONSUMABLE_DEFAULTS.get(default_category) if is_consumable else None

    return {
        "name": name,
        "category": default_category,
        "brand": brand,
        "is_consumable": 1 if is_consumable else 0,
        "estimated_lifespan_days": lifespan,
    }


def insert_items(conn: sqlite3.Connection, items: list[dict]) -> int:
    """Insert items into the possessions table. Skips duplicates by name+category. Returns count of inserted rows."""
    cursor = conn.cursor()
    today = date.today().isoformat()
    count = 0

    for item in items:
        # Skip if item with same name and category already exists
        cursor.execute(
            "SELECT COUNT(*) FROM possessions WHERE name = ? AND category = ?",
            (item["name"], item["category"]),
        )
        if cursor.fetchone()[0] > 0:
            continue

        cursor.execute(
            """INSERT INTO possessions
               (name, category, brand, is_consumable, estimated_lifespan_days,
                last_replenished, created_at)
               VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (
                item["name"],
                item["category"],
                item["brand"],
                item["is_consumable"],
                item["estimated_lifespan_days"],
                today if item["is_consumable"] else None,
            ),
        )
        count += 1

    conn.commit()
    return count


def run_interactive(conn: sqlite3.Connection) -> None:
    """Interactive mode: walk through categories one by one."""
    all_items: list[dict] = []
    category_counts: dict[str, int] = {}

    print("=" * 50)
    print("  Personal Context Engine — Bootstrap Wizard")
    print("=" * 50)
    print()
    print("Enter items one per line for each category.")
    print("Optional brand: type 'Item name / Brand'")
    print("Press Enter on a blank line to move to the next category.")
    print()

    for cat_key, cat_label, _is_consumable in CATEGORIES:
        print(f"--- {cat_label} ---")
        items_in_cat = 0

        while True:
            try:
                line = input("> ")
            except EOFError:
                break

            if not line.strip():
                break

            item = parse_item_line(line, cat_key)
            if item:
                all_items.append(item)
                items_in_cat += 1
                consumable_tag = " [consumable]" if item["is_consumable"] else ""
                print(f"  + {item['name']}{consumable_tag}")

        if items_in_cat > 0:
            category_counts[cat_key] = items_in_cat
        print()

    if not all_items:
        print("No items entered. Exiting.")
        return

    inserted = insert_items(conn, all_items)

    print("=" * 50)
    print(f"  Done! {inserted} items registered across {len(category_counts)} categories.")
    print("=" * 50)
    for cat, cnt in category_counts.items():
        print(f"  {cat}: {cnt} items")
    print()


def run_non_interactive(conn: sqlite3.Connection) -> None:
    """Non-interactive mode: read 'category:name' lines from stdin."""
    all_items: list[dict] = []
    category_counts: dict[str, int] = {}
    valid_categories = {cat[0] for cat in CATEGORIES}

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        if ":" not in line:
            print(f"Warning: Skipping invalid line (no category prefix): {line}", file=sys.stderr)
            continue

        cat, rest = line.split(":", 1)
        cat = cat.strip().lower()

        if cat not in valid_categories:
            print(f"Warning: Unknown category '{cat}', skipping: {line}", file=sys.stderr)
            continue

        item = parse_item_line(rest, cat)
        if item:
            all_items.append(item)
            category_counts[cat] = category_counts.get(cat, 0) + 1

    if not all_items:
        print("No items parsed from stdin. Exiting.")
        return

    inserted = insert_items(conn, all_items)

    print(f"{inserted} items registered across {len(category_counts)} categories.")
    for cat, cnt in sorted(category_counts.items()):
        print(f"  {cat}: {cnt} items")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Personal Context Engine — Initial Data Bootstrap Wizard"
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="Path to SQLite database (default: ~/.openclaw/workspace/data/personal.db)",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Read from stdin in 'category:name' format (one item per line)",
    )
    args = parser.parse_args()

    default_db = Path.home() / ".openclaw" / "workspace" / "data" / "personal.db"
    db_path = args.db_path or str(default_db)

    if not os.path.exists(db_path):
        print(f"Error: Database not found: {db_path}")
        print("Run setup.sh first to create the database.")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")

        if args.non_interactive:
            run_non_interactive(conn)
        else:
            run_interactive(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
