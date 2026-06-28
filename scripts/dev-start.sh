#!/usr/bin/env bash
# Démarrage complet de CyberScan en local (DB + backend + frontend)
# Usage : bash scripts/dev-start.sh
set -e
cd "$(dirname "$0")/.."

# ── Prérequis ──────────────────────────────────────────────────────────────────
command -v docker >/dev/null 2>&1 || { echo "❌ Docker requis"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 requis"; exit 1; }
command -v node >/dev/null 2>&1   || { echo "❌ Node.js requis"; exit 1; }

echo "🚀 Démarrage CyberScan en local..."

# ── 1. PostgreSQL via Docker ───────────────────────────────────────────────────
echo "→ PostgreSQL..."
docker run -d --name cybervault-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=cybervault \
  -p 5432:5432 \
  postgres:17-alpine 2>/dev/null || echo "  (container déjà en cours)"

# Attendre que PostgreSQL soit prêt
until docker exec cybervault-postgres pg_isready -U postgres -q 2>/dev/null; do
  sleep 0.5
done
echo "  ✓ PostgreSQL prêt"

# ── 2. Backend ─────────────────────────────────────────────────────────────────
echo "→ Backend..."
cd backend

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

# Activer le venv (Linux/macOS)
source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null

pip install -q -r requirements.prod.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "  ⚠️  backend/.env créé depuis .env.example — édite-le puis relance"
  exit 0
fi

python -m alembic upgrade head
python seed_plans.py 2>/dev/null || true

uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..
echo "  ✓ Backend : http://localhost:8000/docs"

# ── 3. Frontend ────────────────────────────────────────────────────────────────
echo "→ Frontend..."
cd frontend
npm install -q
npm start &
FRONTEND_PID=$!
cd ..
echo "  ✓ Frontend : http://localhost:4200"

echo ""
echo "────────────────────────────────────────────"
echo "  CyberScan en cours d'exécution"
echo "  Frontend : http://localhost:4200"
echo "  Backend  : http://localhost:8000/docs"
echo "  Ctrl+C pour arrêter tout"
echo "────────────────────────────────────────────"

cleanup() {
  echo ""
  echo "→ Arrêt..."
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
  docker stop cybervault-postgres 2>/dev/null || true
}
trap cleanup EXIT INT TERM
wait
