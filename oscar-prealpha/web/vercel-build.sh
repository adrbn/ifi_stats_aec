#!/usr/bin/env bash
set -euo pipefail
# Copier les données du repo dans le dossier bundlé par la fonction Python.
if [ -d "../../data" ]; then
  mkdir -p api/data && cp -R ../../data/. api/data/
fi
next build
