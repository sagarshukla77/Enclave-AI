"""Tracks who uploaded which file, using Person B's `documents` table."""
import uuid
from datetime import datetime, timezone

from app.database import get_connection


def register(filename: str, stored_path: str, user: str) -> str:
    """Record an upload. Re-uploading the same filename replaces the old record."""
    doc_id = uuid.uuid4().hex
    conn = get_connection()
    conn.execute("DELETE FROM documents WHERE filename = ?", (filename,))
    conn.execute(
        "INSERT INTO documents (doc_id, filename, stored_path, uploaded_by, uploaded_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (doc_id, filename, stored_path, user, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()
    return doc_id


def remove(filename: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM documents WHERE filename = ?", (filename,))
    conn.commit()
    conn.close()


def metadata() -> dict:
    """filename -> {doc_id, uploaded_by, uploaded_at}"""
    conn = get_connection()
    rows = conn.execute("SELECT doc_id, filename, uploaded_by, uploaded_at FROM documents").fetchall()
    conn.close()
    return {r["filename"]: {"doc_id": r["doc_id"], "uploaded_by": r["uploaded_by"],
                            "uploaded_at": r["uploaded_at"]} for r in rows}
