"""Shared test fixtures for Personal Context Engine."""
import os
import sqlite3
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SCHEMA_DIR = PROJECT_ROOT / "schema"


@pytest.fixture
def db_path(tmp_path):
    """Create a temporary database with full schema applied."""
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("PRAGMA foreign_keys = ON")

    with open(SCHEMA_DIR / "init.sql", encoding="utf-8") as f:
        conn.executescript(f.read())
    with open(SCHEMA_DIR / "migrate_v0.2.sql", encoding="utf-8") as f:
        conn.executescript(f.read())

    conn.close()
    return str(db_file)


@pytest.fixture
def db_conn(db_path):
    """Provide a database connection with foreign keys enabled."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    yield conn
    conn.close()
