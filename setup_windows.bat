@echo off
REM One-time setup for Windows. Double-click, or run from the project root.
cd /d "%~dp0backend"
py -3.11 -m venv .venv || (echo Python 3.11 not found. Install it from python.org & pause & exit /b 1)
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python check_setup.py
pause
