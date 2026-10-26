"""ENCLAVE AI - backend API (Person B's backend + Person A's AI core).

Run from the backend folder:   python run.py        (docs: http://127.0.0.1:8000/docs)
"""
import os
import re
import shutil
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from app import audit, auth, documents, reports
from app.agent_interface import (OllamaError, ai_config, ingestion, llm, rag,
                                 resolve_model, run_agent, tools)
from app.database import init_db

MAX_UPLOAD_BYTES = 50 * 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    auth.create_admin_if_missing()
    yield


app = FastAPI(title="ENCLAVE AI", version="1.0.0", lifespan=lifespan)

_origins = [o.strip() for o in os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
).split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_methods=["*"], allow_headers=["*"])

CurrentUser = Depends(auth.get_current_user)

# The built React app (frontend/dist) is served at /ui/, so one command starts the whole app.
_UI_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _UI_DIR.exists():
    app.mount("/ui", StaticFiles(directory=_UI_DIR, html=True), name="ui")

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse("/ui/")
else:
    @app.get("/", include_in_schema=False)
    def root():
        return {"message": "ENCLAVE AI backend is running. API docs: /docs. The web app is not built yet: see frontend/README.md."}


# ------------------------------------------------------------------ helpers
def _safe_filename(name: str) -> str:
    name = Path(name or "").name                       # strip any folder parts
    name = re.sub(r"[^\w.\- ]", "_", name).strip()
    if not name or name.startswith("."):
        raise HTTPException(400, "Invalid filename.")
    return name


def _uploaded_path(filename: str) -> Path:
    path = ai_config.UPLOAD_DIR / _safe_filename(filename)
    if not path.exists():
        raise HTTPException(404, f"No uploaded file named '{filename}'")
    return path


# ------------------------------------------------------------------ open routes
@app.get("/health")
def health():
    """Backend is up. Also reports whether Ollama is reachable."""
    return {"status": "ok", "ollama": "up" if llm.is_up() else "down",
            "model": ai_config.LLM_MODEL, "embed_model": ai_config.EMBED_MODEL}


@app.get("/test-ollama")
def test_ollama():
    """Proves backend <-> Ollama wiring (Week 1 milestone)."""
    try:
        return {"model": ai_config.LLM_MODEL, "response": llm.generate("Say hello in one sentence.")}
    except OllamaError as e:
        raise HTTPException(503, str(e))


@app.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = auth.authenticate(form.username, form.password)
    if not user:
        raise HTTPException(status_code=401, detail="Wrong username or password")
    return {"access_token": auth.create_token(user), "token_type": "bearer"}


# ------------------------------------------------------------------ chat (the agent)
class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    model: str | None = None        # leave empty to use the default model


@app.post("/chat")
def chat(req: ChatRequest, user: str = CurrentUser):
    """Run the agent: classify -> retrieve -> tools -> draft -> validate. Logged to the audit log."""
    started = time.time()
    model_used, _ = resolve_model(req.model)
    try:
        result = run_agent(req.question, user, req.model)
    except OllamaError as e:                      # Ollama down / model missing: tell the user why
        audit.log_request(user, req.question, [], [], f"ERROR: {e}", model=model_used,
                          duration=time.time() - started)
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        # Log failed requests as well
        audit.log_request(user, req.question, [], [], f"ERROR: {str(e)}", model=model_used,
                          duration=time.time() - started)
        raise HTTPException(status_code=500, detail="An error occurred while processing your request.")

    result["audit_id"] = audit.log_request(
        user, req.question, result.get("sources", []), result.get("tools_used", []),
        result.get("answer", ""), model=result.get("model", ""), duration=time.time() - started)
    return result


# ------------------------------------------------------------------ account / models
@app.get("/me")
def me(user: str = CurrentUser):
    return {"username": user}


@app.get("/models")
def models(user: str = CurrentUser):
    """Model dropdown: the configured models and whether each is pulled in Ollama."""
    status = llm.model_status()
    return {"default": ai_config.LLM_MODEL, "embedding_model": ai_config.EMBED_MODEL,
            "models": status["available_models"]}


@app.get("/models/status")
def models_status(user: str = CurrentUser):
    """Is Ollama up, and are the LLM / embedding / vision models pulled?"""
    status = llm.model_status()
    status["tesseract"] = bool(ai_config.TESSERACT_CMD or shutil.which("tesseract"))
    return status


# ------------------------------------------------------------------ documents
@app.post("/upload")
def upload_file(file: UploadFile = File(...), use_vision: bool = False, user: str = CurrentUser):
    """Save a PDF/DOCX/image, extract text (OCR if scanned), chunk it and index it for search.

    ?use_vision=true reads images/scans with the optional vision model instead of Tesseract."""
    filename = _safe_filename(file.filename)
    ext = Path(filename).suffix.lower()
    if ext not in ai_config.ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type '{ext}'. Allowed: {sorted(ai_config.ALLOWED_EXTENSIONS)}")
    contents = file.file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large (limit 50 MB).")
    if not contents:
        raise HTTPException(400, "The uploaded file is empty.")

    destination = ai_config.UPLOAD_DIR / filename
    destination.write_bytes(contents)

    try:
        pages, warnings = ingestion.extract_pages(destination, use_vision)
    except Exception as e:
        destination.unlink(missing_ok=True)
        raise HTTPException(422, f"Could not read this file: {e}")
    chunks = ingestion.chunk_pages(pages, filename)
    if not chunks:
        warnings.append("No readable text was found in this file, so nothing was indexed.")
    try:
        indexed = rag.index_chunks(filename, chunks)
    except OllamaError as e:
        raise HTTPException(503, f"File saved, but indexing failed: {e}")

    documents.register(filename, str(destination), user)
    audit.log_request(user, filename, [], [], f"{indexed} chunks indexed from {len(pages)} page(s)",
                      action="upload")
    return {
        "filename": filename, "size_bytes": len(contents), "saved_to": str(destination),
        "pages": len(pages), "ocr_pages": sum(p["method"] == "ocr" for p in pages),
        "vision_pages": sum(p["method"] == "vision" for p in pages),
        "chunks_indexed": indexed, "warnings": warnings,
    }


@app.get("/documents")
def list_documents(user: str = CurrentUser):
    meta = documents.metadata()
    items = [{**d, **meta.get(d["filename"], {})} for d in rag.list_documents()]
    return {"documents": items}


@app.delete("/documents/{filename}")
def delete_document(filename: str, user: str = CurrentUser):
    safe = _safe_filename(filename)
    rag.delete_document(safe)
    (ai_config.UPLOAD_DIR / safe).unlink(missing_ok=True)
    documents.remove(safe)
    audit.log_request(user, safe, [], [], "deleted", action="delete")
    return {"deleted": safe}


@app.post("/extract-text")
def extract_text(filename: str, use_vision: bool = False, user: str = CurrentUser):
    """Re-read an already-uploaded file and return its plain text (typed, OCR or vision)."""
    pages, warnings = ingestion.extract_pages(_uploaded_path(filename), use_vision)
    text = "\n\n".join(p["text"] for p in pages)
    return {"filename": filename,
            "pages": [{"page": p["page"], "method": p["method"], "characters": len(p["text"])} for p in pages],
            "character_count": len(text), "text_preview": text[:500], "full_text": text,
            "warnings": warnings}


@app.post("/chunk-text")
def chunk_text(filename: str, chunk_size: int = 500, chunk_overlap: int = 50, user: str = CurrentUser):
    """Show how a file is split into overlapping chunks (with page numbers)."""
    if chunk_overlap >= chunk_size:
        raise HTTPException(400, "chunk_overlap must be smaller than chunk_size.")
    pages, _ = ingestion.extract_pages(_uploaded_path(filename))
    chunks = ingestion.chunk_pages(pages, filename, chunk_size, chunk_overlap)
    return {"filename": filename, "chunk_count": len(chunks), "chunks": chunks}


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    k: int = Field(default=ai_config.TOP_K, ge=1, le=20)


@app.post("/search")
def search(req: SearchRequest, user: str = CurrentUser):
    """Raw retrieval: top-k chunks with source filename + page (no answer is written)."""
    try:
        return {"query": req.query, "results": rag.retrieve(req.query, k=req.k)}
    except OllamaError as e:
        raise HTTPException(503, str(e))


class CalcRequest(BaseModel):
    expression: str


@app.post("/tools/calculator")
def calculator_tool(req: CalcRequest, user: str = CurrentUser):
    try:
        return tools.calculator(req.expression)
    except tools.ToolError as e:
        raise HTTPException(400, str(e))


# ------------------------------------------------------------------ audit + reports
@app.get("/audit")
def get_audit(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
              action: str = Query("ask", description="ask (default) | upload | delete | all"),
              user: str = CurrentUser):
    """Audit log, newest first. Default shows chat questions only; use ?action=all for everything."""
    act = None if action == "all" else action
    return audit.get_recent(limit, offset, act)


@app.get("/audit/{audit_id}")
def get_audit_entry(audit_id: int, user: str = CurrentUser):
    row = audit.get_by_id(audit_id)
    if not row:
        raise HTTPException(404, "Audit entry not found.")
    return row


@app.get("/report/{audit_id}")
def report(audit_id: int, format: str = Query("docx", pattern="^(docx|pdf)$"), user: str = CurrentUser):
    """Download the Word/PDF report for one answered question (use the audit_id from /chat)."""
    row = audit.get_by_id(audit_id)
    if not row or (row.get("action") or "ask") != "ask" or (row.get("answer") or "").startswith("ERROR:"):
        raise HTTPException(404, "No answered question with that audit id.")
    path = ai_config.REPORT_DIR / f"report_{audit_id}.{format}"
    (reports.build_docx if format == "docx" else reports.build_pdf)(row, path)
    media = ("application/vnd.openxmlformats-officedocument.wordprocessingml.document"
             if format == "docx" else "application/pdf")
    return FileResponse(path, media_type=media, filename=path.name)
