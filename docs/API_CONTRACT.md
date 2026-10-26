# API contract (for the frontend)

The bundled React app (`frontend/`) uses exactly these routes. The backend serves it at `/ui/`.

Base URL `http://127.0.0.1:8000`. All routes except `/health`, `/test-ollama` and `/login` need the header
`Authorization: Bearer <token>`. Errors are `{"detail": "message"}` with status 400/401/404/413/422/500/503.
CORS allows `http://localhost:3000` and `:5173` (edit `CORS_ORIGINS` in `backend/.env`).

| Method + path | Purpose | Request | Response (main fields) |
|---|---|---|---|
| GET `/health` | backend + Ollama status | - | `status`, `ollama` ("up"/"down"), `model` |
| POST `/login` | log in | **form-encoded** `username`, `password` | `access_token`, `token_type` (token lasts 8 h) |
| GET `/me` | who am I | - | `username` |
| GET `/models` | model dropdown | - | `default`, `models[{name, installed}]` |
| GET `/models/status` | health of models + OCR | - | `ollama_up`, `llm`, `embedding`, `vision`, `tesseract` |
| POST `/upload?use_vision=false` | upload + OCR + index | multipart field `file` (pdf, docx, png, jpg) | `filename`, `pages`, `ocr_pages`, `vision_pages`, `chunks_indexed`, `warnings[]` |
| GET `/documents` | indexed files | - | `documents[{filename, chunks, pages, uploaded_by, uploaded_at}]` |
| DELETE `/documents/{filename}` | remove file + index | - | `deleted` |
| POST `/search` | raw retrieval (no answer) | `{query, k}` | `results[{text, source, page, score}]` |
| POST `/chat` | ask the agent | `{question, model?}` | see below |
| GET `/audit?limit=&offset=&action=` | audit table | `action`: `ask` (default), `upload`, `delete`, `all` | list of audit items |
| GET `/audit/{id}` | one entry | - | audit item |
| GET `/report/{audit_id}?format=docx\|pdf` | download report | - | file (fetch as a blob, sending the token header) |
| POST `/tools/calculator` | direct calculator | `{expression}` | `expression`, `result` |

## `/chat` response
```json
{
  "audit_id": 7,
  "answer": "The wear of 4.2 mm exceeds the 3.5 mm limit [S1] ... FAILS.",
  "sources": [{"label": "S1", "source": "SOP_Pump_Maintenance.docx", "page": 1, "score": 0.71, "text": "..."}],
  "tools_used": [{"tool": "document_search", "input": "...", "output": "..."},
                 {"tool": "calculator", "input": "4.2 > 3.5", "output": "4.2 > 3.5 = True"}],
  "user": "admin",
  "model": "qwen2.5:7b-instruct-q4_K_M",
  "task_type": "both",
  "validation": {"passed": true, "issues": [], "cited_sources": ["SOP... (p1)"], "grounding": 0.57},
  "trace": [{"step": "classify", "detail": "task type = both", "t": 1727...}],
  "duration_seconds": 14.2
}
```
- `answer` contains `[S1]`, `[S2]` tags that match `sources[].label`; render them as clickable citations.
- Not in the documents: `answer` = `"Not found in provided documents."`, `sources` = `[]`, `validation.passed` = false.
- `validation.passed=false` with a real answer = answered but flagged; show `validation.issues` as a warning.
- `model_warning` appears only if the requested model name was unknown (the default was used instead).
- A chat can take 10-60 s: show a spinner, and don't use a short client timeout.
- Ollama not running -> status **503** with a readable `detail`. Other failures -> **500** (also written to the audit log).

## Audit item
`{id, timestamp, user, question, sources[], tools_used[], answer, action, model, duration_seconds}`
Failed chats are stored with `answer` starting `ERROR:`.
