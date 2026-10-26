"""End-to-end test of the merged app (Person A + Person B). Uses tests/fake_ollama.py, so no model is needed.

Run from the backend folder:   python ../tests/test_api.py
(Quit the real Ollama app first - the fake server needs port 11434.)
"""
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import threading
from http.server import HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
tmp = Path(tempfile.mkdtemp())

# Isolate everything BEFORE the app is imported (real env vars win over backend/.env)
os.environ.update({
    "DATA_DIR": str(tmp / "data"), "DB_PATH": str(tmp / "wb.db"),
    "ADMIN_USERNAME": "admin", "ADMIN_PASSWORD": "test-pass", "JWT_SECRET": "test-secret",
    "TESSERACT_CMD": "", "VISION_MODEL": "", "LLM_TIMEOUT_SECONDS": "30",
    "OLLAMA_URL": "http://127.0.0.1:11434", "MOCK_AGENT": "",
})
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "tests"))

# A database created by Person B's ORIGINAL schema (no action/model/duration columns, 1 old row)
old = sqlite3.connect(tmp / "wb.db")
old.executescript("""
CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL);
CREATE TABLE audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, user TEXT NOT NULL,
                        question TEXT NOT NULL, sources TEXT, tools_used TEXT, answer TEXT);
CREATE TABLE documents (id INTEGER PRIMARY KEY AUTOINCREMENT, doc_id TEXT, filename TEXT NOT NULL,
                        stored_path TEXT NOT NULL, uploaded_by TEXT NOT NULL, uploaded_at TEXT NOT NULL);
INSERT INTO audit_log (timestamp, user, question, sources, tools_used, answer)
VALUES ('2026-10-01T00:00:00+00:00', 'admin', 'old mock question', '[]', '[]', 'Mock response for: old mock question');
""")
old.commit(); old.close()

import fake_ollama  # noqa: E402

srv = HTTPServer(("127.0.0.1", 11434), fake_ollama.H)
threading.Thread(target=srv.serve_forever, daemon=True).start()

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
import app.agent_interface as ai  # noqa: E402
from ai_core import config  # noqa: E402

passed = failed = 0


def check(name, cond, extra=""):
    global passed, failed
    if cond:
        passed += 1; print(f"  PASS  {name}")
    else:
        failed += 1; print(f"  FAIL  {name} {extra}")


with TestClient(app) as c:
    print("Web app served by the backend")
    if (ROOT / "frontend" / "dist" / "index.html").exists():
        r = c.get("/", follow_redirects=False)
        check("/ redirects to /ui/", r.status_code in (302, 307) and r.headers["location"] == "/ui/")
        page = c.get("/ui/")
        check("/ui/ serves the React app", page.status_code == 200 and 'id="root"' in page.text)
        asset = re.search(r'src="\./(assets/[^"]+\.js)"', page.text)
        check("its JavaScript file is served", bool(asset) and c.get("/ui/" + asset.group(1)).status_code == 200)
    else:
        print("  (frontend/dist not built - skipping)")

    print("Login (Person B)")
    check("health open", c.get("/health").json()["status"] == "ok")
    check("protected route without token -> 401", c.get("/documents").status_code == 401)
    check("wrong password -> 401", c.post("/login", data={"username": "admin", "password": "nope"}).status_code == 401)
    r = c.post("/login", data={"username": "admin", "password": "test-pass"})
    check("login ok", r.status_code == 200 and r.json()["token_type"] == "bearer", r.text)
    H = {"Authorization": "Bearer " + r.json()["access_token"]}
    check("/me", c.get("/me", headers=H).json()["username"] == "admin")

    print("Existing database migrated, old audit row kept")
    a = c.get("/audit", headers=H).json()
    check("old audit row still readable", len(a) == 1 and a[0]["question"] == "old mock question", str(a))
    check("old row defaults to action=ask", a[0]["action"] == "ask")

    print("Upload / OCR / chunking (Person A)")
    samples = ROOT / "sample_docs"
    for fn in ["SOP_Pump_Maintenance.docx", "Inspection_Report_Pump_P101.png", "Inspection_Report_Pump_P101_scanned.pdf"]:
        with open(samples / fn, "rb") as f:
            r = c.post("/upload", files={"file": (fn, f)}, headers=H)
        j = r.json()
        check(f"upload {fn}", r.status_code == 200 and j["chunks_indexed"] > 0, r.text[:200])
    check("bad extension rejected", c.post("/upload", files={"file": ("x.exe", b"abc")}, headers=H).status_code == 400)
    check("path traversal neutralised", c.post("/upload", files={"file": ("../../evil.pdf", b"x")}, headers=H).status_code in (400, 422))
    ex = c.post("/extract-text", params={"filename": "Inspection_Report_Pump_P101.png"}, headers=H).json()
    check("OCR read the wear value", "4.2" in ex["full_text"])
    check("scanned PDF used OCR", c.post("/extract-text", params={"filename": "Inspection_Report_Pump_P101_scanned.pdf"}, headers=H).json()["pages"][0]["method"] == "ocr")
    check("chunk-text works", c.post("/chunk-text", params={"filename": "SOP_Pump_Maintenance.docx"}, headers=H).json()["chunk_count"] >= 2)
    docs = c.get("/documents", headers=H).json()["documents"]
    check("documents list has 3 files", len(docs) == 3)
    check("documents carry uploaded_by (Person B's table)", all(d.get("uploaded_by") == "admin" for d in docs), str(docs[:1]))

    print("Vision model path + status")
    st = c.get("/models/status", headers=H).json()
    check("model status ok", st["llm"]["installed"] and st["embedding"]["installed"] and st["tesseract"])
    check("vision disabled in this test", st["vision"]["enabled"] is False)
    config.VISION_MODEL = "fake-vl"
    ex = c.post("/extract-text", params={"filename": "Inspection_Report_Pump_P101.png", "use_vision": True}, headers=H).json()
    check("use_vision=true reads via vision model", ex["pages"][0]["method"] == "vision")
    import ai_core.llm as _llm
    _orig = _llm.describe_image
    def _boom(*a, **k):
        raise _llm.OllamaError("model does not support multimodal requests")
    _llm.describe_image = _boom
    ex = c.post("/extract-text", params={"filename": "Inspection_Report_Pump_P101.png", "use_vision": True}, headers=H).json()
    check("vision FAILS -> falls back to Tesseract (not empty)", ex["pages"][0]["method"] == "ocr" and "4.2" in ex["full_text"] and ex["warnings"])
    _llm.describe_image = _orig
    config.VISION_MODEL = ""

    print("Retrieval + calculator")
    res = c.post("/search", json={"query": "impeller wear limit", "k": 3}, headers=H).json()["results"]
    check("search returns source + page", res and res[0]["source"] and "page" in res[0])
    check("4.2 > 3.5 is True", c.post("/tools/calculator", json={"expression": "4.2 > 3.5"}, headers=H).json()["result"] is True)
    check("code injection blocked", c.post("/tools/calculator", json={"expression": "__import__('os').system('ls')"}, headers=H).status_code == 400)

    print("Chat = Person B's route running Person A's agent")
    r = c.post("/chat", json={"question": "Does an impeller wear measurement of 4.2 mm pass or fail the SOP limit?"}, headers=H)
    j = r.json()
    check("chat ok", r.status_code == 200, r.text[:300])
    print("         answer:", j["answer"][:140])
    check("answer is not the mock", not j["answer"].startswith("Mock response"))
    check("B's contract keys present: answer/sources/tools_used/user/model",
          all(k in j for k in ("answer", "sources", "tools_used", "user", "model")))
    check("used document_search + calculator", {"document_search", "calculator"} <= {t["tool"] for t in j["tools_used"]})
    check("sources carry file + page", j["sources"] and j["sources"][0]["source"] and "page" in j["sources"][0])
    check("validation attached", "validation" in j and "audit_id" in j)
    aid = j["audit_id"]
    check("unknown model name ('string') falls back, with a warning",
          c.post("/chat", json={"question": "What is the shaft vibration limit?", "model": "string"}, headers=H).json().get("model_warning") is not None)
    r2 = c.post("/chat", json={"question": "What is the cafeteria lunch menu on Fridays?"}, headers=H).json()
    print("         off-topic answer:", r2["answer"])

    print("Audit + reports")
    e = c.get(f"/audit/{aid}", headers=H).json()
    check("audit row complete", e["question"] and e["sources"] and e["tools_used"] and e["answer"] and e["model"])
    check("audit default = chat only", all(x["action"] == "ask" for x in c.get("/audit", headers=H).json()))
    check("audit ?action=upload shows uploads", len(c.get("/audit", params={"action": "upload"}, headers=H).json()) == 3)
    check("audit ?action=all shows everything", len(c.get("/audit", params={"action": "all"}, headers=H).json()) == 7)
    for fmt in ("docx", "pdf"):
        r = c.get(f"/report/{aid}", params={"format": fmt}, headers=H)
        check(f"{fmt} report", r.status_code == 200 and len(r.content) > 1500, r.text[:100])
        (Path("/tmp") / f"merged_report.{fmt}").write_bytes(r.content)
    check("report for an upload row (id 2) is refused with 404", c.get("/report/2", headers=H).status_code == 404)
    check("report for a non-existent id is 404", c.get("/report/9999", headers=H).status_code == 404)
    check("delete document", c.delete("/documents/Inspection_Report_Pump_P101.png", headers=H).status_code == 200)
    check("deleted doc gone from list", len(c.get("/documents", headers=H).json()["documents"]) == 2)

    print("Failure paths")
    srv.shutdown(); srv.server_close()
    r = c.post("/chat", json={"question": "Is the pump within limits at 4.2 mm?"}, headers=H)
    check("Ollama down -> clear 503 message", r.status_code == 503 and "Ollama" in r.text, f"{r.status_code} {r.text[:150]}")
    check("failure was audited", any(x["answer"].startswith("ERROR:") for x in c.get("/audit", headers=H).json()))

    print("Mock mode (for frontend work)")
    os.environ["MOCK_AGENT"] = "true"
    j = c.post("/chat", json={"question": "anything at all"}, headers=H).json()
    check("MOCK_AGENT returns Person B's original mock", j["answer"].startswith("Mock response for:"))
    os.environ["MOCK_AGENT"] = ""

print(f"\n{passed} passed, {failed} failed")
shutil.rmtree(tmp, ignore_errors=True)
sys.exit(1 if failed else 0)
