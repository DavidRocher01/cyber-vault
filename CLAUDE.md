# CLAUDE.md — Instructions pour Claude Code

## Contexte projet

**Cyber-Vault** est une plateforme SaaS de cybersécurité B2B/B2C déployée sur AWS ECS Fargate.
Elle combine un gestionnaire de mots de passe zero-knowledge, des modules de conformité (NIS2, ISO 27001, PCA), un scanner de vulnérabilités, un module Dark Web, un RSSI externalisé, et des outils de sensibilisation.

Stack : **FastAPI 0.111** + **SQLAlchemy 2.0 async** + **PostgreSQL 17** (backend) / **Angular 19 standalone** (frontend) / **GitHub Actions** (CI) / **AWS ECS Fargate + RDS** (prod).

---

## Règles de développement

### Branche
- Toujours travailler sur `develop` — **jamais committer directement sur `master`**
- Merger sur `master` uniquement après confirmation explicite de l'utilisateur

### CI
- Relancer uniquement les tests KO : `gh run rerun <id> --failed`
- Ne jamais relancer tout le pipeline sans raison

### Alembic
- Toujours maintenir **une seule tête** : `alembic upgrade head` (singulier)
- Vérifier `alembic heads` avant toute nouvelle migration

---

## Architecture backend

```
backend/app/
├── api/v1/endpoints/   # Routing + validation Pydantic uniquement
├── services/           # Logique métier (pas d'accès DB direct)
├── models/             # SQLAlchemy ORM
├── schemas/            # Pydantic (input/output)
└── core/               # Config, sécurité, DB, utilitaires
```

**Règle stricte des couches :**
- Les endpoints ne font **jamais** d'accès DB direct — ils délèguent aux services
- Les services ne connaissent **pas** les schémas HTTP (Request/Response)
- Les modèles ne contiennent **pas** de logique métier (sauf propriétés simples)

### Patterns obligatoires
- Sessions DB : `AsyncSession` via `Depends(get_db)` — jamais d'`AsyncSessionLocal()` direct dans les endpoints
- Authentification : `Depends(get_current_user)` — jamais de logique JWT dans les endpoints
- Schémas : `model_config = ConfigDict(from_attributes=True)` sur tous les schémas ORM

---

## Architecture frontend

```
frontend/src/app/
├── core/               # Guards, interceptors, services globaux
├── features/           # Un dossier par module fonctionnel
└── shared/             # Composants/pipes/directives réutilisables
```

**Règle :** Chaque nouvelle page doit inclure `app-nav-buttons` (NavButtonsComponent).

**Navigation auth :**
- Login/inscription → redirection vers `/cyberscan`
- Déconnexion → redirection vers `/cyberscan`
- Guard `cryptoGuard` uniquement sur `/vault`

---

## Sécurité — contraintes absolues

- **Jamais de secrets dans le code** (clés, tokens, passwords) — utiliser `.env` + `Settings`
- **SSRF** : toujours appeler `assert_no_ssrf(url)` avant toute requête HTTP vers une URL fournie par l'utilisateur
- **SQL** : uniquement ORM SQLAlchemy — jamais de concaténation de chaînes SQL
- **Logs** : jamais de passwords, tokens JWT, clés, PII dans les logs
- **Validation** : `extra='forbid'` sur les schémas Pydantic exposés publiquement

---

## Tests

- Framework : **pytest** avec `asyncio_mode = auto`
- Isolation : fixture `setup_db` (autouse) — `TRUNCATE … RESTART IDENTITY CASCADE` avant chaque test
- Seuil de couverture : **84%** minimum (CI Python 3.12)
- Relancer uniquement les KO : `gh run rerun <id> --failed`

```bash
# Lancer les tests backend
cd backend && pytest

# Lancer les tests frontend
cd frontend && npm test
```

---

## Commandes utiles

```bash
# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm start

# Pre-commit (vérifier avant commit)
pre-commit run --all-files

# Tests complets
pytest --cov=app --cov-report=term-missing
```

---

## Fichiers à ne pas modifier sans raison

- `backend/alembic/` — migrations DB (toujours générer via `alembic revision`)
- `backend/app/core/database.py` — configuration connexion DB
- `docker-compose.production.yml` — config prod AWS
- `.github/workflows/` — CI/CD (modifier avec précaution)

---

## Variables d'environnement obligatoires

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Clé JWT (min 64 chars) |
| `DATABASE_URL` | `postgresql+asyncpg://...` |
| `ALLOWED_ORIGINS` | Liste JSON des origines CORS |
| `ADMIN_API_KEY` | Clé admin API interne |

Voir `.env.example` pour la liste complète.
