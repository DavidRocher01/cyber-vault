# CLAUDE.md — Instructions pour Claude Code

## Contexte projet

**Cyber-Vault** est une plateforme SaaS de cybersécurité B2B/B2C déployée sur AWS ECS Fargate.
Elle combine un gestionnaire de mots de passe zero-knowledge, des modules de conformité (NIS2, ISO 27001, PCA), un scanner de vulnérabilités, un module Dark Web, un RSSI externalisé, et des outils de sensibilisation.

Stack : **FastAPI 0.115.14** + **SQLAlchemy 2.0 async** + **PostgreSQL 17** (backend) / **Angular 20 standalone** (frontend) / **GitHub Actions** (CI) / **AWS ECS Fargate + RDS** (prod).

---

## Règles de développement

### Branche
- Toujours travailler sur `develop` — **jamais committer directement sur `master`**
- Merger sur `master` uniquement après confirmation explicite de l'utilisateur

### CI
- Relancer uniquement les tests KO : `gh run rerun <id> --failed`
- Ne jamais relancer tout le pipeline sans raison

### Alembic — règles critiques
- Toujours maintenir **une seule tête** : vérifier avec `alembic heads` avant toute nouvelle migration
- **Avant de créer une migration avec un ID custom** : vérifier que l'ID n'existe pas déjà :
  ```bash
  ls backend/alembic/versions/ | grep "^<id>"
  ```
  Le repo a ~70 migrations avec des IDs courts (ex: `a1b2c3d4e5f6`). Les collisions sont fréquentes.
- **Toujours utiliser** `alembic revision --autogenerate` pour générer des IDs uniques, jamais les écrire manuellement.
- Migration fantôme (upgrade=pass, downgrade=pass) = supprimer et recoller la chaîne.

---

## Architecture backend

```
backend/app/
├── api/v1/endpoints/   # Routing + validation Pydantic uniquement
│   ├── awareness/      # Package (10 fichiers)
│   └── rssi/           # Package (5 fichiers)
├── services/           # Logique métier
│   ├── email_service/  # Package : base, auth, scan, alerts, awareness
│   ├── code_scan/      # Package : runner, utils, tasks
│   └── darkweb_dossier/ # Package : ingestion, enrichment, reporting
├── models/             # SQLAlchemy ORM
│   └── enums.py        # StrEnum centralisés (ScanStatus, CampaignStatus, etc.)
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
- Startup/shutdown : pattern `lifespan` (pas `on_startup`/`on_shutdown` — déprécié Starlette 1.0)

### Refacto de services en packages — règle mock
Quand un service `foo_service.py` est découpé en `foo_service/` :
- Les tests qui patchent `app.services.foo_service.X` doivent migrer vers `app.services.foo_service.submodule.X`
- **Toujours grep les tests existants** avant de committer un refacto de service :
  ```bash
  grep -r "patch.*foo_service" backend/tests/
  ```

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

**SSR / Prerendering :**
- `@angular/ssr` est configuré avec prerendering statique (pas de serveur Node en runtime)
- Tout accès à `localStorage`, `sessionStorage`, `window`, `document` doit être derrière `isPlatformBrowser()`
- `AuthService` utilise des getters `session`/`local` SSR-safe — ne pas utiliser `localStorage` directement

---

## Sécurité — contraintes absolues

- **Jamais de secrets dans le code** — utiliser `.env` + `Settings`. L'ARN Secrets Manager est dans `secrets.AWS_SM_ARN`.
- **SSRF** : toujours appeler `assert_no_ssrf(url)` avant toute requête HTTP vers une URL fournie par l'utilisateur
- **SQL** : uniquement ORM SQLAlchemy — jamais de concaténation de chaînes SQL
- **Logs** : jamais de passwords, tokens JWT, clés, PII dans les logs
- **Validation** : `extra='forbid'` sur les schémas Pydantic exposés publiquement
- **Tokens** : access_token en `sessionStorage`, refresh_token en cookie httpOnly (jamais localStorage)
- **Vault** : les champs `title`, `username`, `url`, `notes` sont chiffrés AES-GCM côté client via `VaultStore` — le backend stocke des blobs opaques

---

## Tests

- Framework : **pytest** avec `asyncio_mode = auto`
- Isolation : fixture `setup_db` (autouse) — `TRUNCATE … RESTART IDENTITY CASCADE` avant chaque test
- Seuil de couverture : **81%** minimum (CI Python 3.12, `--cov-fail-under=81`)
- Relancer uniquement les KO : `gh run rerun <id> --failed`
- Le test `test_scans_unit.py::test_remediation_import_error_raises_404` échoue en local (cyber-scanner absent du PATH) — c'est normal, il passe en CI.

```bash
# Lancer les tests backend
cd backend && pytest

# Avec couverture
pytest --cov=app --cov-report=term-missing

# Vérifier les migrations avant de committer
python scripts/check_migrations.py
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

# Vérifier santé migrations Alembic
cd backend && python ../scripts/check_migrations.py

# Tests complets
pytest --cov=app --cov-report=term-missing
```

---

## Fichiers à ne pas modifier sans raison

- `backend/alembic/` — migrations DB (toujours générer via `alembic revision --autogenerate`)
- `backend/app/core/database.py` — configuration connexion DB
- `docker-compose.production.yml` — config prod AWS
- `.github/workflows/` — CI/CD (modifier avec précaution)
- `backend/app/services/email_service/__init__.py` — re-exports publics email

---

## Variables d'environnement obligatoires

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Clé JWT (min 64 chars) |
| `DATABASE_URL` | `postgresql+asyncpg://...` |
| `ALLOWED_ORIGINS` | Liste JSON des origines CORS |
| `ADMIN_API_KEY` | Clé admin API interne |
| `REDIS_URL` | `redis://...` (optionnel — APScheduler fallback in-memory si absent) |

Voir `.env.example` pour la liste complète. Voir `docs/GITHUB_SECRETS.md` pour les secrets CI/CD.
