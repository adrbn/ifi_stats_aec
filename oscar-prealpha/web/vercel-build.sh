#!/usr/bin/env bash
set -euo pipefail
# Copier les données du repo dans le dossier bundlé avec la fonction Python.
if [ -d "../../data" ]; then
  mkdir -p server/data && cp -R ../../data/. server/data/
fi
next build
