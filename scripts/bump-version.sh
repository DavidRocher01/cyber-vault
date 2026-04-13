#!/usr/bin/env bash
# bump-version.sh — Met à jour la version dans tout le projet et crée un tag Git.
#
# Usage :
#   ./scripts/bump-version.sh 0.7.0
#
# Ce script met à jour :
#   - frontend/package.json          (npm version)
#   - frontend/src/app/core/version.ts
#   - backend/app/__version__.py
#   - CHANGELOG.md                   (ajoute un bloc vide pour la nouvelle version)
# Puis crée un commit + tag Git.

set -euo pipefail

# ── Vérifications ──────────────────────────────────────────────────────────────

if [[ $# -ne 1 ]]; then
  echo "Usage : $0 <nouvelle-version>  (ex: 0.7.0)"
  exit 1
fi

NEW_VERSION="$1"

# Valide le format semver (X.Y.Z)
if ! [[ "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Erreur : '$NEW_VERSION' n'est pas un format semver valide (attendu : X.Y.Z)"
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "Bump vers v$NEW_VERSION..."

# ── 1. frontend/package.json ──────────────────────────────────────────────────

cd "$REPO_ROOT/frontend"
npm version "$NEW_VERSION" --no-git-tag-version --allow-same-version > /dev/null
echo "  [OK] frontend/package.json → $NEW_VERSION"

cd "$REPO_ROOT"

# ── 2. frontend/src/app/core/version.ts ──────────────────────────────────────

VERSION_TS="$REPO_ROOT/frontend/src/app/core/version.ts"
sed -i "s/export const APP_VERSION = '.*';/export const APP_VERSION = '$NEW_VERSION';/" "$VERSION_TS"
echo "  [OK] frontend/src/app/core/version.ts → $NEW_VERSION"

# ── 3. backend/app/__version__.py ─────────────────────────────────────────────

VERSION_PY="$REPO_ROOT/backend/app/__version__.py"
sed -i "s/__version__ = \".*\"/__version__ = \"$NEW_VERSION\"/" "$VERSION_PY"
echo "  [OK] backend/app/__version__.py → $NEW_VERSION"

# ── 4. CHANGELOG.md — ajout d'un bloc vide pour la nouvelle version ──────────

CHANGELOG="$REPO_ROOT/CHANGELOG.md"
TODAY=$(date +%Y-%m-%d)

# Extrait la version précédente depuis le dernier bloc ## [X.Y.Z]
PREV_VERSION=$(grep -m1 '## \[[0-9]' "$CHANGELOG" | grep -oP '\d+\.\d+\.\d+')

NEW_BLOCK="## [$NEW_VERSION] — $TODAY\n\n### Ajouté\n-\n\n### Modifié\n-\n\n### Corrigé\n-\n\n---\n"

# Insère le nouveau bloc juste après la ligne "---" qui suit l'en-tête
sed -i "0,/^---$/s/^---$/$NEW_BLOCK---/" "$CHANGELOG"

# Met à jour les liens de comparaison en bas du fichier
sed -i "s|\[$PREV_VERSION\]: https://github.com/DavidRocher01/cyber-vault/compare/v.*\.\.\.$PREV_VERSION|[$NEW_VERSION]: https://github.com/DavidRocher01/cyber-vault/compare/v$PREV_VERSION...v$NEW_VERSION\n[$PREV_VERSION]: https://github.com/DavidRocher01/cyber-vault/compare/v|" "$CHANGELOG" 2>/dev/null || true

echo "  [OK] CHANGELOG.md — bloc v$NEW_VERSION ajouté (à compléter)"

# ── 5. Commit + tag ───────────────────────────────────────────────────────────

git add \
  frontend/package.json \
  frontend/package-lock.json \
  frontend/src/app/core/version.ts \
  backend/app/__version__.py \
  CHANGELOG.md

git commit -m "chore(release): bump version to v$NEW_VERSION"
git tag "v$NEW_VERSION"

echo ""
echo "Version v$NEW_VERSION créée."
echo ""
echo "Prochaines étapes :"
echo "  1. Complète le bloc ## [$NEW_VERSION] dans CHANGELOG.md"
echo "  2. git push origin develop --tags"
