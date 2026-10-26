import json
from datetime import datetime, timezone

from app.database import get_connection


def log_request(user, question, sources, tools_used, answer,
                action="ask", model="", duration=0.0) -> int:
    """Write one audit row and return its id (the id is used to download the report)."""
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO audit_log (timestamp, user, question, sources, tools_used, answer, "
        "action, model, duration_seconds) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (datetime.now(timezone.utc).isoformat(), user, question,
         json.dumps(sources, ensure_ascii=False), json.dumps(tools_used, ensure_ascii=False),
         answer, action, model, round(float(duration), 1)),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def _row_to_dict(r) -> dict:
    d = dict(r)
    d["sources"] = json.loads(d["sources"] or "[]")
    d["tools_used"] = json.loads(d["tools_used"] or "[]")
    return d


def get_recent(limit: int = 100, offset: int = 0, action: str | None = "ask") -> list:
    """Newest first. action="ask" (default) = chat questions only; action=None = everything."""
    conn = get_connection()
    sql, params = "SELECT * FROM audit_log", []
    if action:
        sql += " WHERE COALESCE(action, 'ask') = ?"
        params.append(action)
    sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
    rows = conn.execute(sql, (*params, limit, offset)).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def count(action: str | None = "ask") -> int:
    conn = get_connection()
    if action:
        n = conn.execute("SELECT COUNT(*) FROM audit_log WHERE COALESCE(action, 'ask') = ?", (action,)).fetchone()[0]
    else:
        n = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    conn.close()
    return n


def get_by_id(audit_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM audit_log WHERE id = ?", (audit_id,)).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None
