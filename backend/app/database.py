import os
import sqlite3
from pathlib import Path
 
DB_PATH = os.getenv("DB_PATH", str(Path(__file__).resolve().parent.parent / "workbench.db"))
 
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row      # lets us read columns by name
    return conn
 
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
    conn.commit()
    conn.close()

