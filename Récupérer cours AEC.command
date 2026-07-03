#!/bin/bash
# Double-clic (macOS) → ouvre l'outil OSCAR (fenêtre + logs en direct).
cd "$(dirname "$0")"
if [ -x ".venv/bin/python" ]; then
    exec .venv/bin/python oscar_tool.py
else
    exec python3 oscar_tool.py
fi
