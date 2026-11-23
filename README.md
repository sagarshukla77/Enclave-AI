# Enclave AI

Enclave AI is a document question-answering workbench with cited answers, a searchable history, and local model support.

## Privacy and deployment

The local setup sends model requests to Ollama on `localhost` and keeps uploaded documents on the computer running the app. The public repository intentionally omits the original planning files and bundled inspection examples.

Cloud hosting changes this boundary: uploaded documents and questions are stored on the hosted backend, and model traffic goes to the configured Ollama service. The Oracle Cloud Always Free setup is documented in `deploy/ORACLE.md`; it uses persistent Docker volumes and Caddy-managed HTTPS. Oracle's free ARM VM has limited CPU, so local model responses may be slow.

## Run locally

1. Install Python 3.11, [Ollama](https://ollama.com/), and Tesseract OCR.
2. Copy `backend/.env.example` to `backend/.env`. Replace the admin password and JWT secret with unique values.
3. Pull the models listed by `LLM_MODEL` and `EMBED_MODEL` in `backend/.env`.
4. Run `setup_windows.bat` on Windows or `bash setup_mac_linux.sh` on macOS/Linux.
5. Start Ollama, run `start_backend_windows.bat` on Windows or `python backend/run.py` from the project root, and open `http://127.0.0.1:8000`.

The built frontend is included in `frontend/dist`. To edit it, use Node.js 20.19+ or 22.12+, run `npm ci` in `frontend`, then `npm run build`.

## Configuration

`backend/.env.example` lists the backend settings. Keep `backend/.env` private; it is ignored by Git. Do not use the example credentials in a deployed instance.

