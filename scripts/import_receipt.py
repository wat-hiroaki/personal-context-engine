#!/usr/bin/env python3
"""
Receipt OCR scanner for Personal Context Engine.

Extracts store name, items, prices, and totals from receipt images
using Tesseract OCR (local, no API calls).

Usage:
    python3 import_receipt.py <image_path> [db_path] [--lang LANG]

Options:
    --lang    OCR language (ja, en, ja+en). Default: ja+en

Dependencies:
    - Tesseract OCR: https://github.com/tesseract-ocr/tesseract
    - pytesseract, Pillow, opencv-python-headless
"""

import sys
import os
import re
import sqlite3
import argparse
import hashlib
from pathlib import Path

try:
    import pytesseract
    from PIL import Image  # noqa: F401 — needed to verify Pillow install
    import cv2
    import numpy as np
except ImportError as e:
    print(f"Error: Missing dependency: {e}")
    print("Install: pip install pytesseract Pillow opencv-python-headless")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
CONFIG_DIR = SCRIPT_DIR.parent / "config"

# Language mapping for Tesseract
LANG_MAP = {
    "ja": "jpn",
    "en": "eng",
    "ja+en": "jpn+eng",
    "jpn": "jpn",
    "eng": "eng",
    "jpn+eng": "jpn+eng",
}

# Common price patterns
PRICE_PATTERNS = [
    # Japanese: ¥1,234 or ￥1,234 or 1,234円
    re.compile(r"[¥￥]\s*(\d[\d,]+)", re.UNICODE),
    re.compile(r"(\d[\d,]+)\s*円", re.UNICODE),
    # English: $12.34
    re.compile(r"\$\s*(\d[\d,]*\.\d{2})"),
    # Generic: just numbers with decimals
    re.compile(r"(\d[\d,]*\.\d{2})"),
]

# Total line patterns
TOTAL_PATTERNS = [
    re.compile(r"(合計|小計|総計|お支払い|お買上|tax\s*incl)", re.IGNORECASE),
    re.compile(r"(total|subtotal|amount\s*due|grand\s*total|balance)", re.IGNORECASE),
]

# Date patterns on receipts
DATE_PATTERNS = [
    (re.compile(r"(\d{4})[/\-年](\d{1,2})[/\-月](\d{1,2})"), "%Y-%m-%d"),
    (re.compile(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})"), None),  # Ambiguous M/D/Y or D/M/Y
    (re.compile(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{2})\b"), None),  # Short year
]

# Store name heuristic: first few non-empty, non-numeric lines
STORE_SKIP_PATTERNS = re.compile(
    r"^(\d+$|[\-=*]+$|tel|fax|phone|電話|レジ|担当|レシート|receipt|no\.|#)",
    re.IGNORECASE,
)


def preprocess_image(image_path: str) -> np.ndarray:
    """Preprocess receipt image for better OCR accuracy."""
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Cannot read image: {image_path}")

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Denoise
    denoised = cv2.fastNlMeansDenoising(gray, h=10)

    # Adaptive threshold for varying lighting
    thresh = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8
    )

    # Deskew
    coords = np.column_stack(np.where(thresh < 128))
    if len(coords) > 100:
        rect = cv2.minAreaRect(coords)
        angle = rect[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        if abs(angle) < 15:  # Only correct small angles
            (h, w) = thresh.shape
            center = (w // 2, h // 2)
            rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            thresh = cv2.warpAffine(
                thresh, rotation_matrix, (w, h),
                flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
            )

    return thresh


def ocr_image(image: np.ndarray, lang: str) -> tuple[str, float]:
    """Run OCR and return (text, confidence)."""
    tess_lang = LANG_MAP.get(lang, lang)

    # Get detailed data for confidence
    data = pytesseract.image_to_data(
        image, lang=tess_lang, output_type=pytesseract.Output.DICT
    )
    confidences = []
    for c in data["conf"]:
        try:
            val = int(c)
            if val > 0:
                confidences.append(val)
        except (ValueError, TypeError):
            continue
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    # Get full text
    text = pytesseract.image_to_string(image, lang=tess_lang)

    return text, avg_confidence


def extract_store_name(lines: list[str]) -> str | None:
    """Heuristic: store name is usually in the first few lines."""
    for line in lines[:5]:
        line = line.strip()
        if not line or len(line) < 2:
            continue
        if STORE_SKIP_PATTERNS.search(line):
            continue
        # Skip lines that are mostly numbers/prices
        if re.match(r"^[\d¥￥$,.\s]+$", line):
            continue
        return line
    return None


def extract_date(text: str) -> str | None:
    """Extract date from receipt text."""
    for pattern, _fmt in DATE_PATTERNS:
        match = pattern.search(text)
        if match:
            groups = match.groups()
            if len(groups) == 3:
                y, m, d = groups
                if len(y) == 4:
                    return f"{y}-{int(m):02d}-{int(d):02d}"
                elif len(groups[2]) == 4:
                    # M/D/Y format
                    return f"{groups[2]}-{int(groups[0]):02d}-{int(groups[1]):02d}"
                elif len(groups[2]) == 2:
                    year = 2000 + int(groups[2])
                    return f"{year}-{int(groups[0]):02d}-{int(groups[1]):02d}"
    return None


def extract_items(lines: list[str]) -> list[dict]:
    """Extract line items (name + price) from receipt lines."""
    items = []

    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue

        # Skip total/subtotal lines
        is_total = any(p.search(line) for p in TOTAL_PATTERNS)
        if is_total:
            continue

        # Try to find price in line
        price = None
        for pattern in PRICE_PATTERNS:
            match = pattern.search(line)
            if match:
                price_str = match.group(1).replace(",", "")
                try:
                    price = float(price_str)
                    break
                except ValueError:
                    continue

        if price is not None and price > 0:
            # Item name is everything before the price
            name = line
            for pattern in PRICE_PATTERNS:
                name = pattern.sub("", name)
            # Clean up
            name = re.sub(r"[¥￥$×x*]\s*\d+", "", name)  # Remove quantity markers
            name = re.sub(r"\s{2,}", " ", name).strip()
            name = name.rstrip(".-_= ")

            if name and len(name) >= 2:
                items.append({"name": name, "price": price})

    return items


def extract_total(lines: list[str]) -> float | None:
    """Extract total amount from receipt."""
    for line in lines:
        is_total = any(p.search(line) for p in TOTAL_PATTERNS)
        if not is_total:
            continue
        for pattern in PRICE_PATTERNS:
            match = pattern.search(line)
            if match:
                price_str = match.group(1).replace(",", "")
                try:
                    return float(price_str)
                except ValueError:
                    continue
    return None


def detect_currency(text: str) -> str:
    """Detect currency from receipt text."""
    if "¥" in text or "￥" in text or "円" in text:
        return "JPY"
    if "$" in text:
        return "USD"
    if "€" in text:
        return "EUR"
    if "£" in text:
        return "GBP"
    return "JPY"  # Default for ambiguous


def compute_image_hash(image_path: str) -> str:
    """Compute MD5 hash of image file for duplicate detection."""
    h = hashlib.md5()
    with open(image_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def save_to_db(
    db_path: str,
    image_path: str,
    store_name: str | None,
    total: float | None,
    currency: str,
    receipt_date: str | None,
    raw_text: str,
    confidence: float,
    lang: str,
    items: list[dict],
) -> int:
    """Save receipt scan and items to database."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    # Check for duplicate scan
    image_hash = compute_image_hash(image_path)
    cursor.execute(
        "SELECT id FROM receipt_scans WHERE image_path = ? OR image_path LIKE ?",
        (os.path.abspath(image_path), f"%{image_hash}%"),
    )
    existing = cursor.fetchone()
    if existing:
        print(f"Warning: This receipt appears to already be scanned (id={existing[0]}). Skipping.")
        conn.close()
        return -1

    try:
        # Insert receipt scan
        cursor.execute(
            """INSERT INTO receipt_scans
               (image_path, store_name, total_amount, currency, receipt_date, ocr_raw_text, ocr_confidence, language)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (f"{os.path.abspath(image_path)}|{image_hash}", store_name, total, currency, receipt_date, raw_text, confidence, lang),
        )
        receipt_id = cursor.lastrowid

        # Insert line items
        for item in items:
            cursor.execute(
                """INSERT INTO receipt_items (receipt_id, item_name, price, quantity)
                   VALUES (?, ?, ?, 1)""",
                (receipt_id, item["name"], item["price"]),
            )

            # Also add to purchase_history
            cursor.execute(
                """INSERT INTO purchase_history
                   (source, item_name, price, currency, purchase_date, raw_data)
                   VALUES ('receipt', ?, ?, ?, ?, ?)""",
                (item["name"], item["price"], currency, receipt_date, f"receipt_id={receipt_id},store={store_name}"),
            )

        conn.commit()
    finally:
        conn.close()
    return receipt_id


def scan_receipt(image_path: str, db_path: str, lang: str = "ja+en") -> dict:
    """Main function: scan receipt image and save to DB."""
    result = {
        "store": None,
        "date": None,
        "items": [],
        "total": None,
        "currency": "JPY",
        "confidence": 0.0,
        "receipt_id": None,
    }

    # Preprocess
    print("Preprocessing image...")
    processed = preprocess_image(image_path)

    # OCR
    print(f"Running OCR (lang={lang})...")
    raw_text, confidence = ocr_image(processed, lang)
    result["confidence"] = round(confidence, 1)

    if not raw_text.strip():
        print("Warning: OCR returned empty text. Image may be unreadable.")
        return result

    lines = [line for line in raw_text.split("\n") if line.strip()]

    # Extract components
    result["store"] = extract_store_name(lines)
    result["date"] = extract_date(raw_text)
    result["items"] = extract_items(lines)
    result["total"] = extract_total(lines)
    result["currency"] = detect_currency(raw_text)

    # Save to DB
    if result["items"]:
        result["receipt_id"] = save_to_db(
            db_path=db_path,
            image_path=os.path.abspath(image_path),
            store_name=result["store"],
            total=result["total"],
            currency=result["currency"],
            receipt_date=result["date"],
            raw_text=raw_text,
            confidence=confidence,
            lang=lang,
            items=result["items"],
        )

    return result


def main():
    parser = argparse.ArgumentParser(description="Receipt OCR scanner for Personal Context Engine")
    parser.add_argument("image_path", help="Path to receipt image (JPG, PNG)")
    parser.add_argument("db_path", nargs="?", default=None, help="Path to SQLite database")
    parser.add_argument("--lang", "-l", default="ja+en", help="OCR language: ja, en, ja+en (default: ja+en)")
    args = parser.parse_args()

    if not os.path.exists(args.image_path):
        print(f"Error: File not found: {args.image_path}")
        sys.exit(1)

    default_db = Path.home() / ".openclaw" / "workspace" / "data" / "personal.db"
    db_path = args.db_path or str(default_db)

    if not os.path.exists(db_path):
        print(f"Error: Database not found: {db_path}")
        print("Run setup.sh first to create the database.")
        sys.exit(1)

    print(f"Scanning receipt: {args.image_path}")
    print(f"Database: {db_path}")
    print(f"Language: {args.lang}")
    print()

    result = scan_receipt(args.image_path, db_path, args.lang)

    print("\nReceipt Scan Results")
    print(f"{'=' * 40}")
    print(f"Store:      {result['store'] or '(unknown)'}")
    print(f"Date:       {result['date'] or '(unknown)'}")
    print(f"Currency:   {result['currency']}")
    print(f"Confidence: {result['confidence']}%")
    print()

    if result["items"]:
        print(f"Items ({len(result['items'])}):")
        for i, item in enumerate(result["items"], 1):
            print(f"  {i}. {item['name']:30s}  {result['currency']} {item['price']:,.0f}")
        print()

    if result["total"]:
        print(f"Total: {result['currency']} {result['total']:,.0f}")

    if result["receipt_id"]:
        print(f"\nSaved to DB (receipt_id={result['receipt_id']})")
        print(f"  {len(result['items'])} items added to purchase_history")
    else:
        print("\nNo items detected — nothing saved.")


if __name__ == "__main__":
    main()
