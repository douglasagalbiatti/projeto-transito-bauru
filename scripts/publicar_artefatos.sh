#!/usr/bin/env bash
# Substitui a branch 'artefatos' por um único commit com os arquivos gerados agora.
# As versões anteriores deixam de fazer parte da branch; as demais branches não são alteradas.
set -euo pipefail

BRANCH="artefatos"
ARQUIVOS=(output/graficos)

# Índice temporário: não toca no índice nem nos arquivos da branch atual
export GIT_INDEX_FILE
GIT_INDEX_FILE="$(mktemp -u)"
trap 'rm -f "$GIT_INDEX_FILE"' EXIT

git add --force "${ARQUIVOS[@]}"
ARVORE="$(git write-tree)"
COMMIT="$(git commit-tree "$ARVORE" -m "Artefatos gerados em $(date -u +%Y-%m-%d)")"
git push --force origin "$COMMIT:refs/heads/$BRANCH"
