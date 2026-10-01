import json
from datetime import datetime, timezone
from app.database import get_connection
 
def log_request(user, question, sources, tools_used, answer):
    conn = get_connection()
    conn.execute(
        "INSERT INTO audit_log (timestamp, user, question, sources, tools_used, answer) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.now(timezone.utc).isoformat(), user, question,
         json.dumps(sources), json.dumps(tools_used), answer),
    )
    conn.commit()
    conn.close()
 
def get_recent(limit: int = 100):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["sources"] = json.loads(d["sources"] or "[]")
        d["tools_used"] = json.loads(d["tools_used"] or "[]")
        result.append(d)
    return result
