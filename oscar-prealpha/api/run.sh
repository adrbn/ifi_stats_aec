#!/usr/bin/env bash
# Create the venv if missing, install requirements, and run the API.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR=".venv"

if [ ! -d "$VENV_DIR" ]; then
  echo "[run.sh] creating virtualenv in $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "[run.sh] installing requirements"
pip install --upgrade pip >/dev/null
pip install -r requirements.txt

echo "[run.sh] starting uvicorn on http://localhost:8000"
exec uvicorn main:app --reload --port 8000
