#!/usr/bin/env bash
# =============================================================================
# setup_dev.sh — Prépare l'environnement de dev Cyber-Vault sur un nouveau poste.
#
# Automatise TOUT ce qui ne demande ni droits admin ni auth interactive :
#   venv backend + deps, npm install, hooks pre-commit, backend/.env de dev,
#   base locale + migrations, (option) seed, (option) venv cyber-scanner.
# Pour le reste (installer Docker/Node/Postgres, se logger AWS/GitHub), il
# DÉTECTE l'état et affiche la commande exacte à lancer — sans rien forcer.
#
# Idempotent : relançable sans risque (ne réinstalle que ce qui manque).
#
# Usage :
#   bash scripts/setup_dev.sh                 # setup standard
#   bash scripts/setup_dev.sh --seed          # + peuple la base de dev locale
#   bash scripts/setup_dev.sh --with-scanner  # + venv du cyber-scanner
#   bash scripts/setup_dev.sh --force-env     # écrase un backend/.env existant
#   bash scripts/setup_dev.sh --help
# =============================================================================
set -u

# ── Options ──────────────────────────────────────────────────────────────────
DO_SEED=0
DO_SCANNER=0
FORCE_ENV=0
for arg in "$@"; do
  case "$arg" in
    --seed) DO_SEED=1 ;;
    --with-scanner) DO_SCANNER=1 ;;
    --force-env) FORCE_ENV=1 ;;
    -h|--help)
      sed -n '2,19p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "Option inconnue : $arg (voir --help)"; exit 2 ;;
  esac
done

# ── Contexte ─────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) OS=windows ;;
  Linux) OS=linux ;;
  Darwin) OS=macos ;;
  *) OS=unknown ;;
esac

# Marqueurs ASCII (pas d'emoji : la console Windows cp1252 casse dessus).
ok()   { printf '  [OK]   %s\n' "$1"; }
warn() { printf '  [!!]   %s\n' "$1"; }
info() { printf '  [..]   %s\n' "$1"; }
step() { printf '\n== %s\n' "$1"; }

MISSING_REQUIRED=0
MANUAL_STEPS=""
add_manual() { MANUAL_STEPS="${MANUAL_STEPS}  - $1\n"; }

have() { command -v "$1" >/dev/null 2>&1; }

# Hint d'installation selon l'OS.
install_hint() {
  case "$1:$OS" in
    *:windows) echo "winget install $2" ;;
    *:linux)   echo "sudo apt install $3" ;;
    *:macos)   echo "brew install $3" ;;
    *)         echo "installer $1 manuellement" ;;
  esac
}

# ── 1. Prérequis ─────────────────────────────────────────────────────────────
step "1/8  Vérification des prérequis"

# Python (requis)
PYTHON_CMD=""
for c in python3 python; do
  if have "$c" && "$c" -c 'import sys; sys.exit(0 if sys.version_info>=(3,12) else 1)' 2>/dev/null; then
    PYTHON_CMD="$c"; break
  fi
done
if [ -n "$PYTHON_CMD" ]; then ok "Python 3.12+ ($PYTHON_CMD)"; else
  warn "Python 3.12+ absent — REQUIS. $(install_hint python 'Python.Python.3.12' python3)"
  MISSING_REQUIRED=1
fi

# Node/npm (requis pour le frontend)
if have node && have npm; then ok "Node/npm ($(node --version))"; else
  warn "Node.js 20 absent — REQUIS (frontend). $(install_hint node 'OpenJS.NodeJS.LTS' nodejs)"
  MISSING_REQUIRED=1
fi

# make (requis pour les raccourcis)
if have make; then ok "make"; else warn "make absent (raccourcis make indispo)"; fi

# git (requis — mais on est déjà dans le repo cloné)
have git && ok "git" || warn "git absent"

# Optionnels
have docker && ok "Docker ($(docker --version 2>/dev/null | head -c 40))" || {
  warn "Docker absent (parité prod / edge indispo). $(install_hint docker 'Docker.DockerDesktop' docker.io)"
  add_manual "Docker Desktop : $(install_hint docker 'Docker.DockerDesktop' docker.io) puis activer WSL2"
}
if have psql || have createdb; then ok "client Postgres (psql/createdb)"; else
  warn "psql/createdb absent : la base locale devra être créée à la main"
  add_manual "PostgreSQL 17 + créer la base : $(install_hint psql 'PostgreSQL.PostgreSQL.17' postgresql)"
fi
have nmap && ok "nmap" || {
  warn "nmap absent (make prod-check / scans locaux indispo)"
  add_manual "nmap (scans locaux) : $(install_hint nmap 'Insecure.Nmap' nmap)"
}
have gh && ok "GitHub CLI" || add_manual "GitHub CLI : $(install_hint gh 'GitHub.cli' gh)"
have aws && ok "AWS CLI v2" || add_manual "AWS CLI v2 : $(install_hint aws 'Amazon.AWSCLI' awscli)"

if [ "$MISSING_REQUIRED" = "1" ]; then
  printf '\n[STOP] Des prérequis REQUIS manquent (voir ci-dessus). Installe-les puis relance.\n'
  exit 1
fi

# ── 2. Backend : venv + deps ─────────────────────────────────────────────────
step "2/8  Backend — venv + dépendances"
if [ ! -d backend/.venv ]; then
  info "création de backend/.venv"
  "$PYTHON_CMD" -m venv backend/.venv || { warn "échec création venv"; exit 1; }
else
  ok "backend/.venv déjà présent"
fi
if [ -f backend/.venv/Scripts/python.exe ]; then VENV_PY="backend/.venv/Scripts/python.exe"
else VENV_PY="backend/.venv/bin/python"; fi
info "pip install -r backend/requirements.txt (peut prendre 1-2 min)"
"$VENV_PY" -m pip install --quiet --upgrade pip >/dev/null 2>&1
if "$VENV_PY" -m pip install --quiet -r backend/requirements.txt; then
  ok "dépendances backend installées"
else
  warn "échec pip install backend — voir la sortie ci-dessus"
fi

# ── 3. Frontend : npm install ────────────────────────────────────────────────
step "3/8  Frontend — npm install"
if [ -d frontend/node_modules ]; then
  ok "frontend/node_modules déjà présent (npm ci non forcé)"
else
  info "npm install dans frontend/ (peut prendre 2-3 min)"
  ( cd frontend && npm install --no-fund --no-audit ) && ok "dépendances frontend installées" \
    || warn "échec npm install"
fi

# ── 4. Hooks pre-commit ──────────────────────────────────────────────────────
step "4/8  Hooks qualité (pre-commit)"
if "$VENV_PY" -m pre_commit --version >/dev/null 2>&1; then PC=("$VENV_PY" -m pre_commit)
elif have pre-commit; then PC=(pre-commit)
else PC=(); fi
if [ "${#PC[@]}" -gt 0 ]; then
  "${PC[@]}" install >/dev/null 2>&1
  "${PC[@]}" install --hook-type commit-msg >/dev/null 2>&1
  ok "hooks pre-commit + commit-msg installés"
else
  warn "pre-commit introuvable — installe-le : $VENV_PY -m pip install pre-commit"
fi

# ── 5. backend/.env de dev ───────────────────────────────────────────────────
step "5/8  Fichier backend/.env (dev)"
if [ -f backend/.env ] && [ "$FORCE_ENV" != "1" ]; then
  ok "backend/.env déjà présent (relance avec --force-env pour régénérer)"
else
  ENV_ARGS=""
  [ "$FORCE_ENV" = "1" ] && ENV_ARGS="--force"
  if "$VENV_PY" scripts/bootstrap_dev_env.py $ENV_ARGS; then
    ok "backend/.env généré (secrets locaux aléatoires)"
  else
    warn "échec génération .env"
  fi
fi

# ── 6. Base de données locale + migrations ───────────────────────────────────
step "6/8  Base de données locale (port 5432) + migrations"
DB_READY=0
if have createdb; then
  if createdb cybervault 2>/dev/null; then ok "base 'cybervault' créée"; DB_READY=1
  else info "base 'cybervault' déjà là (ou createdb a refusé) — on tente les migrations"; DB_READY=1; fi
elif have psql; then
  if psql -lqt 2>/dev/null | cut -d'|' -f1 | grep -qw cybervault; then ok "base 'cybervault' présente"; DB_READY=1
  else warn "base 'cybervault' absente — crée-la : createdb cybervault (ou CREATE DATABASE cybervault;)"; fi
else
  warn "pas de client Postgres — crée la base à la main, puis : (cd backend && ../$VENV_PY -m alembic upgrade head)"
  add_manual "Créer la base 'cybervault' (5432) et lancer : cd backend && alembic upgrade head"
fi
if [ "$DB_READY" = "1" ]; then
  info "alembic upgrade head"
  if ( cd backend && "../$VENV_PY" -m alembic upgrade head ) ; then
    ok "migrations appliquées (tête à jour)"
  else
    warn "échec alembic — vérifie DATABASE_URL dans backend/.env (postgres/password@localhost:5432) et que Postgres tourne"
    add_manual "Ajuster backend/.env (DATABASE_URL) puis : cd backend && alembic upgrade head"
  fi
fi

# ── 7. Options : seed + cyber-scanner ────────────────────────────────────────
step "7/8  Options"
if [ "$DO_SEED" = "1" ] && [ "$DB_READY" = "1" ]; then
  info "seed de la base de dev (scripts/seed_test_db.py)"
  "$VENV_PY" scripts/seed_test_db.py && ok "base peuplée" || warn "échec seed"
else
  info "seed non demandé (ajoute --seed pour peupler la base de dev)"
fi
if [ "$DO_SCANNER" = "1" ] && [ -d cyber-scanner ]; then
  info "venv cyber-scanner"
  if [ ! -d cyber-scanner/.venv ]; then "$PYTHON_CMD" -m venv cyber-scanner/.venv; fi
  if [ -f cyber-scanner/.venv/Scripts/python.exe ]; then SPY="cyber-scanner/.venv/Scripts/python.exe"
  else SPY="cyber-scanner/.venv/bin/python"; fi
  "$SPY" -m pip install --quiet -r cyber-scanner/requirements.txt \
    && ok "cyber-scanner prêt" || warn "échec deps cyber-scanner"
else
  info "cyber-scanner non demandé (ajoute --with-scanner si besoin)"
fi

# ── 8. Auth machine (jamais automatisable : interactif) ──────────────────────
step "8/8  Identités machine (à faire toi-même)"
# git identity
if git config user.name >/dev/null 2>&1 && git config user.email >/dev/null 2>&1; then
  ok "git identity : $(git config user.name) <$(git config user.email)>"
else
  warn "git identity non configurée"
  add_manual 'git config --global user.name "..."  &&  git config --global user.email "..."'
fi
# GitHub
if have gh; then
  if gh auth status >/dev/null 2>&1; then ok "GitHub CLI authentifié"; else
    warn "GitHub CLI non authentifié"; add_manual "gh auth login"; fi
fi
# AWS (indispensable pour le travail prod)
if have aws; then
  if aws sts get-caller-identity >/dev/null 2>&1; then
    ok "AWS authentifié ($(aws configure get region 2>/dev/null || echo 'region ?'))"
  else
    warn "AWS non authentifié (requis pour deploy/ECS/Secrets Manager)"
    add_manual "aws configure   (ou : aws sso login)   — région eu-west-3"
  fi
fi

# ── Récapitulatif ────────────────────────────────────────────────────────────
printf '\n=============================================================\n'
printf 'Setup terminé.\n'
if [ -n "$MANUAL_STEPS" ]; then
  printf '\nIl te reste à faire MANUELLEMENT :\n'
  printf "$MANUAL_STEPS"
else
  printf 'Aucune action manuelle détectée — tout est prêt.\n'
fi
printf '\nDémarrer le dev :\n'
printf '  Backend  : make dev-backend      (http://localhost:8000)\n'
printf '  Frontend : make dev-frontend     (http://localhost:4200)\n'
printf 'Contexte projet : docs/ETAT_DES_LIEUX.md   |   Détails : docs/DEV_SETUP.md\n'
printf '=============================================================\n'
