#!/usr/bin/env bash
# generate-test-report.sh — Génère un rapport de tests complet pour une livraison.
#
# Usage :
#   ./scripts/generate-test-report.sh [version]
#
# Exemple :
#   ./scripts/generate-test-report.sh 0.6.0
#
# Produit : docs/test-reports/v<version>-test-report.md

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

VERSION="${1:-$(grep -oP "APP_VERSION = '\K[^']+" frontend/src/app/core/version.ts)}"
TODAY=$(date +%Y-%m-%d)
REPORT_DIR="$REPO_ROOT/docs/test-reports"
REPORT_FILE="$REPORT_DIR/v${VERSION}-test-report.md"

mkdir -p "$REPORT_DIR"

echo "Génération du rapport de tests v$VERSION..."

# ── Exécution des tests ───────────────────────────────────────────────────────

TMP_BACKEND=$(mktemp)
TMP_FRONTEND=$(mktemp)
TMP_FRONTEND_COV=$(mktemp)

# Backend
echo "  → pytest..."
cd "$REPO_ROOT/backend"
pytest tests/ -v --tb=short --no-header -q 2>&1 > "$TMP_BACKEND" || true

# Frontend
echo "  → vitest..."
cd "$REPO_ROOT/frontend"
npx vitest run --reporter=verbose 2>&1 > "$TMP_FRONTEND" || true
npx vitest run --coverage --reporter=json --outputFile="$TMP_FRONTEND_COV" 2>/dev/null || true

cd "$REPO_ROOT"

# ── Extraction des métriques backend ─────────────────────────────────────────

BACKEND_PASSED=$(grep -oP '\d+(?= passed)' "$TMP_BACKEND" | tail -1 || echo "?")
BACKEND_FAILED=$(grep -oP '\d+(?= failed)' "$TMP_BACKEND" | tail -1 || echo "0")
BACKEND_ERROR=$(grep -oP '\d+(?= error)' "$TMP_BACKEND" | tail -1 || echo "0")
BACKEND_TOTAL=$(( ${BACKEND_PASSED:-0} + ${BACKEND_FAILED:-0} + ${BACKEND_ERROR:-0} ))

# ── Extraction des métriques frontend ────────────────────────────────────────

FRONTEND_PASSED=$(grep -oP '\d+(?= passed)' "$TMP_FRONTEND" | tail -1 || echo "?")
FRONTEND_FAILED=$(grep -oP '\d+(?= failed)' "$TMP_FRONTEND" | tail -1 || echo "0")
FRONTEND_TOTAL=$(( ${FRONTEND_PASSED:-0} + ${FRONTEND_FAILED:-0} ))

# Résultat global
if [[ "$BACKEND_FAILED" == "0" && "$FRONTEND_FAILED" == "0" ]]; then
  GLOBAL_STATUS="SUCCÈS"
  GLOBAL_BADGE="✅"
else
  GLOBAL_STATUS="ÉCHEC"
  GLOBAL_BADGE="❌"
fi

# ── Liste des fichiers de tests backend avec compte ──────────────────────────

BACKEND_FILES=$(grep -E "^(PASSED|FAILED|ERROR) tests/" "$TMP_BACKEND" \
  | awk -F'::' '{print $1}' \
  | sort | uniq -c \
  | awk '{printf "| %s | %d |\n", $2, $1}' || echo "")

# ── Fichiers avec échecs ──────────────────────────────────────────────────────

BACKEND_FAILURES=$(grep -E "^(FAILED|ERROR)" "$TMP_BACKEND" | head -20 || echo "_Aucun_")
FRONTEND_FAILURES=$(grep -E "× |✗ |FAIL " "$TMP_FRONTEND" | head -20 || echo "_Aucun_")

# ── Génération du rapport ─────────────────────────────────────────────────────

cat > "$REPORT_FILE" << REPORT
# Rapport de tests — v${VERSION}

**Date :** ${TODAY}
**Version :** v${VERSION}
**Résultat global :** ${GLOBAL_BADGE} ${GLOBAL_STATUS}

---

## Résumé

| Composant  | Tests | Réussis | Échoués | Statut |
|------------|------:|--------:|--------:|--------|
| Backend    | ${BACKEND_TOTAL} | ${BACKEND_PASSED:-?} | ${BACKEND_FAILED} | $([ "${BACKEND_FAILED}" = "0" ] && echo "✅" || echo "❌") |
| Frontend   | ${FRONTEND_TOTAL} | ${FRONTEND_PASSED:-?} | ${FRONTEND_FAILED} | $([ "${FRONTEND_FAILED}" = "0" ] && echo "✅" || echo "❌") |
| **Total**  | **$(( BACKEND_TOTAL + FRONTEND_TOTAL ))** | **$(( ${BACKEND_PASSED:-0} + ${FRONTEND_PASSED:-0} ))** | **$(( ${BACKEND_FAILED} + ${FRONTEND_FAILED} ))** | ${GLOBAL_BADGE} |

---

## Backend (pytest)

### Fichiers de tests
$(echo "$BACKEND_FILES")

### Sortie complète
\`\`\`
$(cat "$TMP_BACKEND")
\`\`\`

---

## Frontend (Vitest)

### Sortie complète
\`\`\`
$(cat "$TMP_FRONTEND")
\`\`\`

---

## Échecs

### Backend
${BACKEND_FAILURES}

### Frontend
${FRONTEND_FAILURES}

---

_Rapport généré automatiquement par \`scripts/generate-test-report.sh\`_
REPORT

# Nettoyage
rm -f "$TMP_BACKEND" "$TMP_FRONTEND" "$TMP_FRONTEND_COV"

echo ""
echo "${GLOBAL_BADGE} Rapport généré : $REPORT_FILE"
echo "   Backend  : ${BACKEND_PASSED:-?}/${BACKEND_TOTAL} tests réussis"
echo "   Frontend : ${FRONTEND_PASSED:-?}/${FRONTEND_TOTAL} tests réussis"
