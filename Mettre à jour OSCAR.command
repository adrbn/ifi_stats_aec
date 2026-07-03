#!/bin/bash
# Double-clic (macOS) → met à jour les données OSCAR et publie en prod (Vercel).
cd "$(dirname "$0")"
if [ -x ".venv/bin/python" ]; then
    exec .venv/bin/python update_oscar_prod.py
else
    exec python3 update_oscar_prod.py
fi
