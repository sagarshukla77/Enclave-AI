@echo off
REM Only needed if you CHANGE the web app (frontend\src). Needs Node.js 20.19+ or 22.12+ (https://nodejs.org, LTS).
cd /d "%~dp0frontend"
call npm install
call npm run build
echo.
echo Done. Restart the backend and refresh the page.
pause
