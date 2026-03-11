"""Shared utilities for Personal Context Engine scripts."""

import json
import re
from datetime import datetime
from pathlib import Path

ENCODING_ORDER_DEFAULT = ["utf-8-sig", "utf-8", "shift_jis", "cp932", "iso-8859-1", "latin-1"]

CONFIG_DIR = Path(__file__).parent.parent / "config"
OPENCLAW_CONFIG_DIR = Path.home() / ".openclaw" / "workspace" / "config"
DEFAULT_DB_PATH = Path.home() / ".openclaw" / "workspace" / "data" / "personal.db"


def detect_encoding(filepath: str, encoding_order: list[str] | None = None) -> str:
    """Try multiple encodings and return the first that works."""
    order = encoding_order or ENCODING_ORDER_DEFAULT

    for enc in order:
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


def parse_price_generic(price_str: str, currency_symbols: dict | None = None) -> tuple[float | None, str]:
    """Parse price string and detect currency. Returns (amount, currency_code)."""
    if not price_str:
        return None, "USD"

    symbols = currency_symbols or {"¥": "JPY", "￥": "JPY", "$": "USD", "€": "EUR", "£": "GBP"}
    price_str = price_str.strip()
    currency = "USD"

    for symbol, code in sorted(symbols.items(), key=lambda x: -len(x[0])):
        if symbol in price_str:
            currency = code
            price_str = price_str.replace(symbol, "")
            break

    if "円" in price_str:
        currency = "JPY"
        price_str = price_str.replace("円", "")

    cleaned = re.sub(r"[^\d.\-]", "", price_str)
    try:
        return float(cleaned), currency
    except ValueError:
        return None, currency


def parse_date_multi(date_str: str, date_formats: list[str]) -> str | None:
    """Parse date string using provided format list."""
    if not date_str:
        return None
    date_str = date_str.strip()
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        pass
    return None


def load_json_config(filename: str) -> dict:
    """Load a JSON config file from config/ or OpenClaw workspace."""
    config_path = CONFIG_DIR / filename
    if not config_path.exists():
        config_path = OPENCLAW_CONFIG_DIR / filename
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {filename}")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def row_to_json(row: dict) -> str:
    """Convert a CSV row dict to JSON string for raw_data storage."""
    return json.dumps(row, ensure_ascii=False, default=str)
