@echo off
REM Optional: live-reloading dev server at http://127.0.0.1:5173 (talks to the backend on port 8000).
REM Needs Node.js 20.19+ or 22.12+. Start the backend first.
cd /d "%~dp0frontend"
if not exist node_modules call npm install
call npm run dev
