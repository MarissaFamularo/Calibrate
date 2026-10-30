#!/bin/bash
# Double-click to run Calibrate locally. First run sets up a private Python environment (~1 minute).
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is not installed. Run: xcode-select --install   (then double-click this again)"; read -r; exit 1
fi
if [ ! -d .venv ]; then echo "First run: setting up (about a minute)..."; python3 -m venv .venv || exit 1; fi
.venv/bin/pip install -q --upgrade pip >/dev/null 2>&1
.venv/bin/pip install -q -r requirements.txt || { echo "Setup failed. See the message above."; read -r; exit 1; }
PORT=8000
if [ "$1" = "fake" ] || [ -n "$CALIBRATE_FAKE" ]; then export CALIBRATE_FAKE=1; echo "Running with the scripted test model (no API calls)."; fi
(sleep 3; open "http://localhost:$PORT") &
echo "Calibrate is running at http://localhost:$PORT  (close this window to stop it)"
exec .venv/bin/python -m uvicorn calibrate.server:app --port "$PORT"
