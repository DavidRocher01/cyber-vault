.PHONY: help install install-backend install-frontend \
        dev dev-backend dev-frontend \
        test test-backend test-frontend test-e2e \
        lint lint-backend lint-frontend \
        format format-backend format-frontend \
        typecheck typecheck-backend typecheck-frontend \
        security check \
        migrate migrate-rollback migrate-new migrate-reset \
        prod-check prod-check-logs docker-down \
        frontend-check edge edge-down build clean

# ── Couleurs ────────────────────────────────────────────────────────────────────
CYAN  := \033[0;36m
GREEN := \033[0;32m
RESET := \033[0m

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-22s$(RESET) %s\n", $$1, $$2}'

# ── Installation ────────────────────────────────────────────────────────────────

install: install-backend install-frontend ## Installe toutes les dépendances
	pre-commit install
	pre-commit install --hook-type commit-msg
	@echo "$(GREEN)✓ Installation complète$(RESET)"

install-backend: ## Installe les dépendances Python
	cd backend && pip install -r requirements.txt

install-frontend: ## Installe les dépendances Node.js
	cd frontend && npm install

# ── Développement ───────────────────────────────────────────────────────────────

dev-backend: ## Lance le backend en mode dev
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Lance le frontend en mode dev
	cd frontend && npm start

# ── Tests ───────────────────────────────────────────────────────────────────────

test: test-backend test-frontend ## Lance tous les tests (backend + frontend)

test-backend: ## Lance les tests backend avec couverture
	cd backend && pytest

test-frontend: ## Lance les tests frontend (Vitest)
	cd frontend && npm test

test-e2e: ## Lance les tests E2E Playwright
	cd frontend && npm run test:e2e

test-backend-fast: ## Lance les tests backend sans couverture (plus rapide)
	cd backend && pytest --no-cov -x

# ── Qualité code ────────────────────────────────────────────────────────────────

lint: lint-backend lint-frontend ## Lint backend + frontend

lint-backend: ## Lint Python (ruff)
	cd backend && ruff check app/ tests/

lint-frontend: ## Lint TypeScript/Angular (ESLint)
	cd frontend && npm run lint

format: format-backend format-frontend ## Formate backend + frontend

format-backend: ## Formate Python (ruff format)
	cd backend && ruff format app/ tests/

format-frontend: ## Formate TypeScript/HTML/SCSS (Prettier)
	cd frontend && npm run format

typecheck: typecheck-backend typecheck-frontend ## Vérifie les types backend + frontend

typecheck-backend: ## Vérification des types Python (mypy)
	cd backend && mypy app/ --ignore-missing-imports --no-strict-optional

typecheck-frontend: ## Vérification des types TypeScript
	cd frontend && npx tsc --noEmit

security: ## Audit de sécurité (bandit + npm audit)
	cd backend && bandit -ll -r app/
	cd frontend && npm audit --audit-level=high

check: lint typecheck security test ## Vérification complète (lint + types + sécurité + tests)
	@echo "$(GREEN)✓ Toutes les vérifications sont passées$(RESET)"

pre-commit-run: ## Lance pre-commit sur tous les fichiers
	pre-commit run --all-files

# ── Base de données ─────────────────────────────────────────────────────────────

migrate: ## Applique les migrations Alembic
	cd backend && alembic upgrade head

migrate-rollback: ## Annule la dernière migration
	cd backend && alembic downgrade -1

migrate-new: check-migrations ## Crée une nouvelle migration (MSG="description") — vérifie le DAG avant
	cd backend && alembic revision --autogenerate -m "$(MSG)"

migrate-reset: ## Remet la DB à zéro (⚠️ destructif)
	@echo "$(CYAN)⚠️  Remise à zéro de la base de données...$(RESET)"
	cd backend && alembic downgrade base && alembic upgrade head

migrate-status: ## Affiche le statut des migrations
	cd backend && alembic current && alembic heads

check-migrations: ## Vérifie la santé du DAG Alembic (IDs uniques, pas de fantômes, une tête)
	python scripts/check_migrations.py

# ── Docker : parité prod ──────────────────────────────────────────────────────
# Backend dans la MÊME image que la prod (Linux, Python 3.14, nmap/bearer),
# même commande uvicorn, migrations jouées comme en prod. Pas de hot-reload :
# c'est pour VALIDER avant un déploiement, pas pour le dev quotidien (reste en
# natif : `make dev-backend`). Base isolée/jetable (port 5433), pas de Redis (= prod).

prod-check: ## Parité prod : build l'image, migre, lance le backend et smoke-teste (arrêter l'uvicorn natif d'abord)
	docker compose -f docker-compose.dev.yml up -d --build
	@echo "$(CYAN)Attente du backend...$(RESET)"
	@for i in $$(seq 1 30); do curl -sf http://localhost:8000/health >/dev/null 2>&1 && break || sleep 2; done
	@curl -sf http://localhost:8000/health >/dev/null && echo "$(GREEN)✓ /health OK$(RESET)" || echo "backend KO"
	@docker exec cybervault_dev_backend sh -c "command -v nmap >/dev/null && echo '$(GREEN)✓ nmap présent (scans testables)$(RESET)'"
	@echo "$(CYAN)Front : lance 'make dev-frontend' — il proxie /api vers ce backend.$(RESET)"

prod-check-logs: ## Suit les logs du backend dockerisé
	docker compose -f docker-compose.dev.yml logs -f backend

docker-down: ## Arrête et supprime le stack de parité prod
	docker compose -f docker-compose.dev.yml down

# ── Build ───────────────────────────────────────────────────────────────────────

build: ## Build le frontend Angular
	cd frontend && npm run build

frontend-check: ## Build le frontend EXACTEMENT comme la prod (configuration=production)
	# `ng serve` (dev-server) n'exécute ni les optimisations ni les vérifs de template
	# du build de prod. Ce build (le même que deploy.yml) attrape ce que le dev cache :
	# erreurs AOT, directives non importées (ex. *ngIf sans NgIf), budgets dépassés.
	# À lancer avant un déploiement front. Pour SERVIR l'artefact en iso-prod, voir
	# le reverse proxy (make edge-*).
	cd frontend && npm run build -- --configuration=production

# ── Edge : reverse proxy iso-prod (Caddy) ──────────────────────────────────────
# Sert le SPA BUILDÉ derrière un proxy qui reproduit CloudFront+ALB (https, split
# /api, X-Forwarded-*). Voir infra/Caddyfile. Nécessite un backend sur :8000
# (`make prod-check` recommandé pour que l'IP forwarded soit honorée).

edge: ## Sert le frontend buildé derrière Caddy (https://localhost, /api -> :8000)
	@test -d frontend/dist/cyber-vault-frontend/browser || { echo "$(CYAN)Build d'abord : make frontend-check$(RESET)"; exit 1; }
	docker compose -f docker-compose.edge.yml up -d
	@echo "$(GREEN)✓ Edge en ligne : https://localhost$(RESET) (accepter le certificat interne au 1er accès)"

edge-down: ## Arrête le reverse proxy edge
	docker compose -f docker-compose.edge.yml down

# ── Nettoyage ───────────────────────────────────────────────────────────────────

clean: ## Nettoie les artefacts de build et tests
	rm -rf backend/htmlcov backend/test-results backend/.pytest_cache
	rm -rf frontend/dist frontend/coverage frontend/test-results
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)✓ Nettoyage terminé$(RESET)"
