import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DB_PATH = os.getenv("DB_PATH", str(Path(__file__).resolve().parent.parent / "workbench.db"))


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row      # lets us read columns by name
    return conn


def _ensure_columns(conn, table: str, columns: dict) -> None:
    """Add columns that are missing, so an existing workbench.db keeps working."""
    existing = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
    for name, ddl in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def init_db():
    conn = get_connection()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        user TEXT NOT NULL,
        question TEXT NOT NULL,
        sources TEXT,
        tools_used TEXT,
        answer TEXT
    );
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_id TEXT,
        filename TEXT NOT NULL,
        stored_path TEXT NOT NULL,
        uploaded_by TEXT NOT NULL,
        uploaded_at TEXT NOT NULL
    );
    """)
    # Added by the AI-core merge (safe on an existing database):
    _ensure_columns(conn, "audit_log", {
        "action": "TEXT DEFAULT 'ask'",          # ask | upload | delete
        "model": "TEXT DEFAULT ''",
        "duration_seconds": "REAL DEFAULT 0",
    })
    conn.commit()
    conn.close()
