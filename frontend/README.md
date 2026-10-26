# Frontend (React + Vite)

The web app for ENCLAVE AI. **You do not need Node.js to use it**: the built app is in `dist/` and the
backend serves it. Start the backend, then open **http://127.0.0.1:8000** (it redirects to `/ui/`).

Screens: sign in, Ask (answers with clickable citations and a sources column, Word/PDF report download),
Documents (upload, list, remove), History (audit log with filters), System (Ollama, models, OCR status).

## Changing the app (needs Node.js 20.19+ or 22.12+)
```
cd frontend
npm install
npm run dev        # live dev server: http://127.0.0.1:5173  (backend must be running on port 8000)
npm run build      # rebuilds dist/ - restart nothing, just refresh the page served at :8000
```
On Windows you can double-click `build_frontend_windows.bat` or `start_frontend_dev_windows.bat` in the project root.

## Files
```
src/api.js         every call to the backend (login token, errors, report download)
src/App.jsx        sign-in gate + navigation
src/views/         Ask, Documents, History, System
src/components/    RichAnswer (citation chips), SourceSlip, Verdict, HowAnswered, ReportButtons, Login
src/styles.css     all styling (colours and fonts are CSS variables at the top)
```
Fonts (Source Serif 4, Public Sans) are bundled from npm, so nothing is fetched from the internet.
Backend address: `http://127.0.0.1:8000` in dev, same origin when served by the backend; override with `VITE_API_URL`.
