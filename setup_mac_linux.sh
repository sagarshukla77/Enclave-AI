#!/usr/bin/env bash
# One-time setup for macOS / Linux. Run from the project root:  bash setup_mac_linux.sh
set -e
cd "$(dirname "$0")/backend"
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python check_setup.py || true
