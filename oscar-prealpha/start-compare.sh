#!/usr/bin/env bash
# OSCAR — lance le site unifié de comparaison v2 / v3 (local).
#
#   ./start-compare.sh
#
# Démarre, dans un seul terminal :
#   • le backend FastAPI de la v3      → http://localhost:8000
#   • le frontend Next.js de la v3     → http://localhost:3000
#   • la coque (toggle v2 / v3)        → http://localhost:8080  ← ouvre celle-ci
#
# La v2 (Streamlit) est embarquée en live depuis ifi-stats-aec.streamlit.app,
# rien à lancer pour elle. Ctrl-C arrête tout.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHELL_PORT=8080

pids=()
cleanup() {
  echo ""
  echo "[compare] arrêt des process…"
  for p in "${pids[@]}"; do kill "$p" 2>/dev/null || true; done
}
trap cleanup EXIT INT TERM

echo "[compare] 1/3 · backend FastAPI (port 8000)…"
( cd "$ROOT/web/server" && ./run.sh ) &
pids+=($!)

echo "[compare] 2/3 · frontend Next.js (port 3000)…"
( cd "$ROOT/web" && { [ -d node_modules ] || npm install; } && npm run dev ) &
pids+=($!)

echo "[compare] 3/3 · coque de comparaison (port ${SHELL_PORT})…"
( cd "$ROOT/shell" && python3 -m http.server "$SHELL_PORT" >/dev/null 2>&1 ) &
pids+=($!)

URL="http://localhost:${SHELL_PORT}"
sleep 4
echo ""
echo "[compare] ✅ prêt → ${URL}"
echo "[compare]    (le front v3 peut mettre ~10 s à compiler au 1er lancement)"
echo "[compare]    Ctrl-C pour tout arrêter."
echo ""
if   command -v open     >/dev/null 2>&1; then open "$URL"
elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL"
fi

wait
