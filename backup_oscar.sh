#!/bin/bash
# backup_oscar.sh — sauvegarde automatique des données + exports + scripts OSCAR
# vers une branche GitHub dédiée « backup/latest », SANS toucher main/prod ni
# l'arbre de travail (git plumbing avec un index temporaire).
#
# Lancé quotidiennement par le LaunchAgent com.oscar.backup (+ à chaque login).
# Ne commite que si quelque chose a changé. Historique conservé sur la branche.
set -uo pipefail

REPO="/Users/adrien/vibecoding/claudecode_repos/ifi/stats_aec_app"
BRANCH="backup/latest"
LOG="$REPO/.backup.log"
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
cd "$REPO" || { echo "$(date '+%F %T')  repo introuvable" >>"$LOG"; exit 1; }
ts=$(date '+%F %T')

# Fichiers à sauvegarder (globs étendus par le shell ; nullglob ignore les absents).
shopt -s nullglob
FILES=(
  data/category_mapping.csv
  data/new_cours/cache_cours.xlsx
  data/new_cours/cache_eleves.xlsx
  data/new_cours/eleves_par_classe_*.xlsx
  data/new_cours/cours_*.xlsx
  oscar-prealpha/web/server/data/new_cours/cache_cours.xlsx
  oscar-prealpha/web/server/data/new_cours/cache_eleves.xlsx
  oscar-prealpha/web/server/data/category_mapping.csv
  oscar-prealpha/web/server/fixtures/snapshot.json
  *.py
  *.command
  *.bat
  backup_oscar.sh
)
if [ ${#FILES[@]} -eq 0 ]; then echo "$ts  aucun fichier" >>"$LOG"; exit 0; fi

git fetch -q origin "$BRANCH" 2>/dev/null

# Index temporaire isolé → n'affecte ni l'index ni la branche courante.
TMPIDX="$(mktemp -t oscar_backup_idx)"
export GIT_INDEX_FILE="$TMPIDX"
git read-tree --empty
git add -f -- "${FILES[@]}" 2>>"$LOG"
tree=$(git write-tree)

parent=$(git rev-parse -q --verify "refs/remotes/origin/$BRANCH" || true)
if [ -n "$parent" ] && [ "$tree" = "$(git rev-parse -q --verify "$parent^{tree}" || echo none)" ]; then
  echo "$ts  aucun changement — pas de backup" >>"$LOG"
  rm -f "$TMPIDX"; unset GIT_INDEX_FILE; exit 0
fi

if [ -n "$parent" ]; then
  commit=$(git commit-tree "$tree" -p "$parent" -m "backup: $ts")
else
  commit=$(git commit-tree "$tree" -m "backup: $ts")
fi
rm -f "$TMPIDX"; unset GIT_INDEX_FILE

if git push -q origin "$commit:refs/heads/$BRANCH" 2>>"$LOG"; then
  echo "$ts  ✓ backup poussé ($commit) sur $BRANCH" >>"$LOG"
else
  echo "$ts  ✗ push échoué (auth GitHub ?)" >>"$LOG"
  exit 1
fi
