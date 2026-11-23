# ENCLAVE AI: merged project (Person A + Person B)

A private, on-premise AI workbench. Documents, questions and answers never leave your computer;
the only network call is to Ollama on `localhost:11434`.

| Part | Owner | Folder |
|---|---|---|
| AI core: models, agent (LangGraph), OCR, chunking, RAG (ChromaDB), tools | Person A | `ai-core/` |
| Backend API: login, `/chat`, audit log, document records | Person B | `backend/` |
| Frontend (React web app) | built to complete the merge | `frontend/` |

```
Enclave-AI_Merged/
  ai-core/ai_core/     agent.py  ingestion.py  rag.py  tools.py  llm.py  config.py
  backend/
    app/               main.py  auth.py  audit.py  database.py  documents.py  reports.py
                       agent_interface.py   <- the one file that connects B's backend to A's AI core
    run.py  check_setup.py  requirements.txt  .env  .env.example
    data/              created at run time: uploads, search index, reports (git-ignored)
  frontend/            React + Vite source (src/) and the ready-built app (dist/), served by the backend
  sample_docs/  tests/  docs/  setup_*.bat/.sh  start_backend_*.bat/.sh  build_frontend_windows.bat
```

## How the merge works
Person B built the backend with a **mock** `run_agent()` in `agent_interface.py` and an empty `ai-core/` folder, so I kept
B's structure and plugged A's code into it:

- `/chat` (B's route) now runs A's real agent. The mock answer is still available with `MOCK_AGENT=true` in `.env`.
- B's login (`/login`, passlib + JWT) replaces A's login. B's `auth.py` is unchanged.
- B's SQLite audit log replaces A's. Three columns were added (`action`, `model`, `duration_seconds`) and are
  **added automatically to an existing `workbench.db`**; old rows are kept.
- B's `documents` table, which was unused, now records who uploaded each file.
- B's empty `reports.py` now builds the Word/PDF reports.
- Added what the frontend needs: CORS (ports 3000 and 5173) and clear error messages.

**Route names follow Person B.** If you used Person A's names earlier:

| Earlier (Person A) | Now |
|---|---|
| `POST /auth/login` | `POST /login` |
| `POST /ask` | `POST /chat` (response field `citations` is now `sources`, `tools_called` is now `tools_used`) |
| `GET /audit` | same, but shows chat questions only by default; `?action=all` shows uploads/deletes too |

## 1. Install (Windows, Python 3.11.9)
1. **Ollama** with two models:
   ```
   ollama pull qwen2.5:7b-instruct-q4_K_M
   ollama pull nomic-embed-text
   ```
2. **Tesseract OCR** (https://github.com/UB-Mannheim/tesseract/wiki). If it isn't on PATH, `TESSERACT_CMD` in
   `backend\.env` already points to `C:\Program Files\Tesseract-OCR\tesseract.exe`.
3. Double-click **`setup_windows.bat`** once. It creates a fresh `backend\.venv`, installs everything and runs a check.
   Don't reuse the old venvs from either project.

macOS/Linux: `bash setup_mac_linux.sh`.

## 2. Run
Start Ollama, then double-click **`start_backend_windows.bat`** (or: `cd backend`, `.venv\Scripts\activate`, `python run.py`).
Open **http://127.0.0.1:8000** (the web app) and sign in with `ADMIN_USERNAME` / `ADMIN_PASSWORD` from `backend\.env`.
The raw API test page is still at http://127.0.0.1:8000/docs.
After editing `.env`, restart the backend. **No Node.js is needed**: the built web app is already in `frontend/dist`.

## 3. First test (in the web app)
1. **System** tab: Ollama, answer model, search model and text recognition should all show a green mark.
2. **Documents** tab: choose the 3 files from `sample_docs/` (SOP, scanned report image, scanned PDF).
3. **Ask** tab: click the first example question (the 4.2 mm impeller wear one) and press Ask.
   The first answer can take a minute while the model loads.
4. Click the small numbers in the answer to jump to the source passage; use **Word** or **PDF** to save a report.
5. **History** tab: every question, upload and removal, with the same reports.

## 3b. Changing the web app (optional, needs Node.js 20.19+ or 22.12+)
See `frontend/README.md`. In short: `build_frontend_windows.bat` rebuilds it; `start_frontend_dev_windows.bat` gives a live dev server.

## 4. Tests
```
cd backend
python ..\tests\test_api.py
```
47 checks using a stand-in Ollama (no model needed). Quit the real Ollama app first, since the stand-in uses port 11434.
They also check that an old Person B database is migrated, that failures return clear messages, and that the web app is served.

Optional browser test (29 checks: sign in, upload, ask, citations, reports, history, phone-sized screen, session expiry):
```
pip install playwright
playwright install chromium
python ..\tests\e2e_browser.py
```
Neither test has been run against your real models or on Windows. The web app was only exercised in Chromium on Linux with the stand-in model,
so the answers' wording in my screenshots is not what your real model will produce.

## Known issues and decisions
- **Vision model:** `VISION_MODEL` in `.env` is carried over exactly as in your Person A `.env`
  (`qwen2.5:7b-instruct-q4_K_M`). That is a text-only model, so `use_vision=true` will always report a vision error and fall
  back to Tesseract (the fallback is fixed in this version). When you want vision working: `ollama pull qwen2.5vl:7b`,
  then set `VISION_MODEL=qwen2.5vl:7b`. Or leave it empty to turn vision off.
- **Frontend:** Person B's files had none, so I built one (React). If Person B has their own, `docs/API_CONTRACT.md` is the contract; the two can share the backend.
- **Sign-in lasts for the browser tab** (it is kept in `sessionStorage`); closing the tab signs you out. The conversation on the Ask tab is kept the same way.
- **No data was copied** (uploads, search index, `workbench.db`, report files, `.venv`). The app recreates them on first start; re-upload your documents.
- **Passwords:** the admin account is created once, on first start. Changing `ADMIN_PASSWORD` later does nothing until you delete
  `backend/workbench.db` (which also clears the audit log).
- The empty `requirement.txt` (typo duplicate) was dropped; `requirements.txt` is now UTF-8 and merged.
- `bcrypt` is pinned to 4.0.1 and `passlib` to 1.7.4 because newer bcrypt breaks passlib. Don't upgrade them separately.
- Single admin user, no roles; one shared knowledge base for all documents; handwriting is poor with Tesseract.

