"""Shared fixtures for Personal Context Engine tests."""
import sqlite3
from pathlib import Path

import pytest

SCHEMA_DIR = Path(__file__).parent.parent / "schema"

MIGRATION_FILES = ["init.sql", "migrate_v0.2.sql", "migrate_v1.0.sql"]


def _apply_schema(conn: sqlite3.Connection) -> None:
    """Apply all schema files to a connection."""
    conn.execute("PRAGMA foreign_keys = ON")
    for filename in MIGRATION_FILES:
        sql_path = SCHEMA_DIR / filename
        if sql_path.exists():
            with open(sql_path, encoding="utf-8") as f:
                conn.executescript(f.read())


@pytest.fixture
def db_conn():
    """Create an in-memory SQLite database with all schema applied."""
    conn = sqlite3.connect(":memory:")
    _apply_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def db_path(tmp_path):
    """Create a file-based SQLite database for integration tests."""
    path = str(tmp_path / "test.db")
    conn = sqlite3.connect(path)
    _apply_schema(conn)
    conn.close()
    return path
