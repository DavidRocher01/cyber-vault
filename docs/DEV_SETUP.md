# DEV_SETUP — Installer l'environnement de dev sur un nouveau poste

Guide de reprise du projet **Cyber-Vault** sur une nouvelle machine
(Windows / Linux / macOS). Le code vit sur GitHub ; ce doc reconstruit tout ce
qui n'est **pas** versionné (secrets `.env`, base locale, outillage).

> Branche de travail : toujours `develop`, **jamais** committer directement sur
> `master` (merge prod uniquement sur confirmation explicite). Voir `CLAUDE.md`.

---

## 0. Check-list « quoi apporter » (ce qui ne suit pas git)

`git clone` ramène tout le code (y compris `cyber-scanner/`). Hors git, seules
**3 catégories** comptent — tout le reste se régénère.

> ⚡ **Le plus simple** : installe les prérequis (§1), clone, puis lance
> `make setup`. Il fait A (le `.env`), la base + migrations et toutes les deps
> automatiquement, et te **liste** ce qui reste (B: auth, C: outils absents).

### A. Secrets — apporter par canal sûr OU régénérer

- [ ] `backend/.env` : le plus simple = **ne rien transférer** et lancer
  `make bootstrap-env` sur le nouveau poste (cf. §3). Ne le copier (USB /
  gestionnaire de mots de passe) **que** pour garder tes clés *test* tierces
  (Stripe test, Resend test, HIBP). ⚠️ **Jamais** par email, chat ou git.

### B. Ré-authentifier les identités machine (ne suivent jamais git) — cf. §10

- [ ] **AWS CLI** (`aws configure` / `aws sso login`, région `eu-west-3`) —
  indispensable pour le travail prod (deploy checks, ECS run-task, Secrets
  Manager, recette).
- [ ] **GitHub CLI** (`gh auth login`) — PR, merge, relance CI.
- [ ] **Identité git** (`git config --global user.name` / `user.email`).

### C. Outils absents de git à installer — cf. §1 et §9

- [ ] Docker Desktop, Node 24, Python 3.14, PostgreSQL 17, `pre-commit`.
- [ ] **`nmap`** — requis pour `make prod-check` (scan iso-prod). Installe-le si
  tu veux les scans locaux (souvent absent par défaut).
- [ ] `psql` (client Postgres CLI) — optionnel.
- [ ] **`cyber-scanner/.venv`** à recréer (venv séparé du backend). ⚠️ Veille à
  ce que `python` par défaut pointe sur `backend/.venv`, pas sur celui du
  cyber-scanner.

### D. Régénérable — RIEN à transférer

`node_modules`, `.venv`, `dist`, `.angular`, caches (→ `make install`) ; **base
de dev locale** (→ `alembic upgrade head` + `python scripts/seed_test_db.py`) ;
PDFs de preview, `htmlcov/`, `uploads/`, `test-results/`, `docs/architecture.html`
(jetables). Les comptes de test **locaux** sont perdus mais régénérables ; le
compte démo **prod** vit en prod, pas en local.

---

## 1. Prérequis à installer

| Outil | Version | Rôle |
|-------|---------|------|
| Git | récent | cloner / committer |
| Python | **3.14** (cf. `.python-version`) | backend FastAPI |
| Node.js | **24** (cf. `.nvmrc`) | frontend Angular 21 |
| PostgreSQL | **17** | base de dev native (port 5432) |
| Docker Desktop | récent | parité prod / edge (voir §8) |
| `gh` (GitHub CLI) | récent | PRs, relance CI |
| AWS CLI v2 | récent | Secrets Manager, ECS (prod) |
| `make` | — | raccourcis (`make help`) |
| `pre-commit` | via pip | hooks qualité |

Sur Windows, `make` et les scripts shell tournent sous **Git Bash** (fourni avec
Git). Les commandes `make` du projet supposent un shell POSIX.

---

## 2. Cloner le code

```bash
git clone https://github.com/DavidRocher01/cyber-vault.git
cd cyber-vault
git checkout develop
```

> **Raccourci tout-en-un** — une fois les prérequis §1 installés et le repo
> cloné, `make setup` (ou `bash scripts/setup_dev.sh`) automatise §3→§7 : venv
> backend + deps, `npm install`, hooks pre-commit, `backend/.env` de dev, base
> locale + migrations. Il **détecte** ce qui manque (Docker, nmap, auth AWS/gh)
> et affiche la commande exacte à lancer, sans rien forcer. Idempotent.
> Options : `make setup ARGS="--seed --with-scanner"`. Les sections détaillées
> ci-dessous restent utiles pour comprendre / dépanner.

`git config core.autocrlf` : sous Windows, laisser le défaut. Des diffs
« fantômes » CRLF↔LF peuvent apparaître sur des fichiers front — c'est du bruit,
`git diff --ignore-all-space` doit être vide. Ne pas les committer.

---

## 3. Secrets `.env` (le point à ne pas rater)

`backend/.env` n'est **pas** versionné. Deux méthodes :

- **Rapide** : recopier ton `backend/.env` existant depuis l'ancien poste via un
  canal sûr (clé USB, gestionnaire de mots de passe). ⚠️ **Jamais** par email,
  chat ou git.
- **Propre** : repartir de `backend/.env.example` avec des **valeurs de dev
  locales** (Postgres local, clés Stripe *test*, Resend de test). Les vraies
  valeurs **prod** sont dans **AWS Secrets Manager** (`cybervault/prod`,
  `eu-west-3`) — à ne **pas** mettre en dev.
- **Assisté (recommandé)** : `make bootstrap-env` (ou
  `python scripts/bootstrap_dev_env.py`) génère un `backend/.env` de dev prêt à
  l'emploi — `SECRET_KEY` aléatoire, Postgres local, CORS
  `localhost:4200`, Sentry off, phishing local. Refuse d'écraser un `.env`
  existant sans `--force` ; `--print` pour prévisualiser. Les secrets de services
  tiers (Stripe/Resend/HIBP…) restent **vides**, à compléter seulement si besoin.

Clés attendues (cf. `backend/.env.example`) : `SECRET_KEY` (≥64 chars),
`DATABASE_URL`, `ALLOWED_ORIGINS`, `FRONTEND_URL`, `STRIPE_*`,
`RESEND_API_KEY` / `RESEND_FROM`, `SENTRY_DSN`, `HIBP_API_KEY`, `AWS_REGION`,
`PHISHING_*`, (`REDIS_URL` optionnel — absent = APScheduler/limiter in-memory,
comme la prod).

Exemple minimal de `DATABASE_URL` pour une base native locale :
`postgresql+asyncpg://postgres:password@localhost:5432/cybervault`

---

## 4. Base de données native (dev quotidien)

Créer la base locale (port **5432**) :

```bash
# avec psql
createdb cybervault           # ou CREATE DATABASE cybervault;
cd backend && alembic upgrade head   # applique jusqu'à la tête (ex. d3b47ded55b3)
```

> ⚠️ Ne pas confondre cette base **native 5432** avec la base **Docker isolée
> 5433** du mode parité prod (§8). Piège vécu : vérifier toujours quel process
> écoute sur `:8000` et quel `DATABASE_URL` il utilise vraiment.

---

## 5. Backend

```bash
cd backend
# ⚠️ Créer le venv avec la version de .python-version (3.14) — la même que la
# prod et la CI. Sur Windows : py -3.14 -m venv .venv
python3.14 -m venv .venv
# Windows : .venv\Scripts\activate     |  Linux/macOS : source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000   # ou : make dev-backend
```

Tests : `cd backend && pytest` (la suite complète ~11-12 min, seuil couverture
≥90 %). Rapide : `make test-backend-fast`.

Note : `test_scans_unit.py::test_remediation_import_error_raises_404` échoue en
local (cyber-scanner absent du PATH) — normal, il passe en CI.

---

## 6. Frontend

```bash
cd frontend
npm install
npm start        # http://localhost:4200, proxie /api -> :8000   | ou : make dev-frontend
```

Tests : `npm test` (Vitest). Build iso-prod (à faire avant un déploiement front,
attrape les erreurs AOT que `ng serve` cache) : `make frontend-check`.

---

## 7. Hooks qualité (obligatoire avant de committer)

```bash
pip install pre-commit
pre-commit install
pre-commit install --hook-type commit-msg
# ou, tout d'un coup : make install   (install-backend + install-frontend + hooks)
```

Les hooks lancent ruff / ruff format / mypy / bandit / détection de secrets, et
imposent le **Conventional Commit** (`feat|fix|refactor|test|docs|chore|perf|ci|build:`).
Sauter ces hooks fait échouer la CI.

### Windows — mypy bloqué par Smart App Control

Symptôme, constaté le 2026-08-03 :

```
ImportError: DLL load failed while importing 08ae81f72d5a2b5fa9e0__mypyc:
Une stratégie de contrôle d'application a bloqué ce fichier.
```

**Ce n'est ni un bug de mypy ni une erreur de code.** Smart App Control est
actif sur ce poste (`HKLM:\SYSTEM\CurrentControlSet\Control\CI\Policy` →
`VerifiedAndReputablePolicyState = 1`) et refuse de charger les binaires non
signés qui n'ont pas de réputation établie. La roue officielle de mypy embarque
une extension compilée par mypyc, non signée. Le journal
`Microsoft-Windows-CodeIntegrity/Operational` le confirme (événements 3033/3077).

Détail révélateur : le mypy du cache pre-commit, **construit pour Python 3.12**,
passe sans problème, alors que celui du venv, construit pour **Python 3.14**,
est bloqué. Même fichier logique, réputation différente — la 3.14 est trop
récente pour être connue du service de réputation.

**Correctif, sans dégrader la sécurité du poste :**

```bash
cd backend
python -m pip install --no-binary mypy --force-reinstall --no-cache-dir mypy
```

L'archive source donne un mypy **pur Python**, sans extension compilée, donc
rien à bloquer. Même version (2.3.0, celle épinglée dans `requirements.txt`),
environ 38 s sur l'ensemble de `app/` au lieu de quelques secondes.

⚠️ **Un `pip install -r requirements.txt` réinstalle la roue compilée** et
ramène le blocage. Rejouer la commande ci-dessus après coup.

Ne **pas** désactiver Smart App Control pour contourner : la bascule est
irréversible sans réinstallation de Windows, et affaiblir le poste de
développement d'une entreprise qui vend de la cybersécurité se défendrait mal.

---

## 8. VS Code — extensions & config

La config est **déjà versionnée** dans `.vscode/` (settings + extensions
recommandées). À l'ouverture du dossier, VS Code propose d'installer les
extensions recommandées → **Installer tout**.

### Extensions recommandées du projet (`.vscode/extensions.json`)

| ID | Extension | Rôle |
|----|-----------|------|
| `charliermarsh.ruff` | Ruff | lint + format Python (remplace black/isort), aligné pre-commit |
| `ms-python.python` | Python | interpréteur, debug, tests (détecte `backend/.venv`) |
| `esbenp.prettier-vscode` | Prettier | format TS / HTML / SCSS |
| `dbaeumer.vscode-eslint` | ESLint | lint TypeScript / Angular |
| `angular.ng-template` | Angular Language Service | templates, autocomplétion, erreurs de binding |

### Extras utiles pour la stack complète (facultatif)

| ID | Extension | Pourquoi |
|----|-----------|----------|
| `ms-azuretools.vscode-docker` | Docker | gère les compose dev/edge, images, logs |
| `ms-azuretools.vscode-containers` | Container Tools | complément au-dessus de Docker Desktop |
| `ms-playwright.playwright` | Playwright | lance/debug les tests E2E |
| `redhat.vscode-yaml` | YAML | workflows GitHub Actions, compose |
| `tamasfe.even-better-toml` | TOML | `pyproject.toml`, config ruff |
| `eamodio.gitlens` | GitLens | blame/historique par lot (S1→S7) |
| `editorconfig.editorconfig` | EditorConfig | cohérence fins de ligne (évite le bruit CRLF) |

Réglages clés déjà posés dans `.vscode/settings.json` : format-on-save (ruff pour
Python, prettier pour TS/HTML), `source.fixAll.ruff` à la sauvegarde, règle à 88
colonnes, `extraPaths` vers `backend/`. **Sélectionne l'interpréteur** au premier
lancement si besoin : `Python: Select Interpreter` → `backend/.venv`.

---

## 9. Docker Desktop — config locale

Le dev **quotidien** reste **natif** (`make dev-backend` + `make dev-frontend`,
hot-reload). Docker sert à deux choses : **valider en parité prod** avant un
déploiement, et **tester ce que le natif ne peut pas** (les scans nmap/bearer,
présents seulement dans l'image).

### Installer & configurer Docker Desktop

1. Installer Docker Desktop.
2. **Windows** : activer le **backend WSL2** (Settings → General → *Use the WSL 2
   based engine*) et l'intégration WSL sur ta distro (Settings → Resources → WSL
   Integration). Bien plus rapide que Hyper-V pour ces images.
3. **Ressources** (Settings → Resources) : prévoir au moins **4 Go de RAM** et
   **2 CPU** — l'image backend build nmap/bearer + un Postgres 17.
4. **File sharing** : sur macOS/Windows-Hyper-V, autoriser le partage du disque
   où se trouve le repo. En WSL2, garder le projet dans le FS Linux évite les
   lenteurs de montage.
5. Vérifier : `docker version` et `docker compose version` répondent.

### Les trois fichiers compose

| Fichier | But | Ne pas |
|---------|-----|--------|
| `docker-compose.dev.yml` | **Parité prod** : backend dans l'image prod (Linux, Python 3.14, nmap/bearer), migrations jouées comme en prod, **Postgres isolé port 5433**, **pas de Redis** (= prod) | confondre sa base 5433 avec la native 5432 |
| `docker-compose.edge.yml` | **Iso-edge** : Caddy reproduit CloudFront+ALB (https://localhost, split `/api`, en-têtes forwarded) devant le SPA **buildé** | oublier `make frontend-check` d'abord |
| `docker-compose.production.yml` | Config **prod** AWS | **modifier** (fichier protégé) |

### Parité prod (backend dockerisé)

```bash
# 1. arrêter l'uvicorn natif (il occupe le port 8000)
make prod-check          # docker compose -f docker-compose.dev.yml up -d --build + smoke /health + check nmap
make dev-frontend        # le front natif proxie /api -> :8000 (backend dockerisé)
make prod-check-logs     # suivre les logs du backend
make docker-down         # tout arrêter
```

Points clés (documentés dans l'en-tête de `docker-compose.dev.yml`) :
- **Pas de hot-reload** : comme en prod, un changement de code exige un rebuild
  → toujours `up -d --build` (jamais un simple `restart`, qui garderait le code
  périmé).
- Base **jetable/isolée** (port hôte **5433**, volume `postgres_dev_data`), migrée
  à neuf ; rôle applicatif non-superuser créé via `infra/dev-db-init.sql` (comme
  en prod).
- `APP_ENV=development` volontaire : en `production`, les cookies passeraient en
  `Secure` (cassés sur http local). La parité visée est OS/runtime/deps/binaires,
  pas les flags de sécurité prod.

### Edge iso-prod (SPA derrière Caddy)

```bash
make frontend-check      # produit dist/cyber-vault-frontend/browser (build prod)
# un backend doit écouter sur :8000 (make prod-check recommandé pour l'IP forwarded)
make edge                # -> https://localhost (accepter le certificat interne au 1er accès)
make edge-down
```

---

## 10. Authentifier les CLI

```bash
gh auth login                       # GitHub : PRs, gh run rerun <id> --failed
aws configure   # ou : aws sso login # AWS : Secrets Manager, ECS (piloter la prod)
```

La session AWS peut expirer : si une commande AWS redemande une auth, relancer
la connexion.

---

## 11. Workflow quotidien (rappel `make help`)

```bash
make dev-backend         # uvicorn --reload :8000
make dev-frontend        # ng serve :4200
make test                # backend + frontend
make check               # lint + types + sécurité + tests (avant push)
make migrate             # alembic upgrade head
make migrate-status      # alembic current + heads (garder UNE seule tête)
make prod-check          # parité prod avant un déploiement
```

Migrations Alembic : toujours `make migrate-new MSG="..."` (autogenerate, IDs
uniques) ; vérifier **une seule tête** (`make migrate-status`) avant tout push.

---

## 12. Pièges connus

- **5432 (natif) ≠ 5433 (Docker parité prod)** : deux bases distinctes. Vérifier
  le `DATABASE_URL` **effectif** du process et l'`alembic current` de la bonne DB.
- **Bruit CRLF↔LF** sous Windows : `git diff --ignore-all-space` doit être vide ;
  ne pas committer ces diffs de fin de ligne.
- **Gate couverture front** sensible (~0.15 % d'écart Win↔Linux) : viser une
  marge ≥0.3 % en local avant de pousser.
- **Avant un push** : suite backend complète + build front prod (`make
  frontend-check`) + E2E, pas seulement les tests modifiés.
- **Docker** : `up -d --build` (jamais `restart`) pour ne pas servir du code
  périmé en parité prod.

---

## 13. Repères dans le repo

- `CLAUDE.md` — règles projet (branches, archi couches, sécurité, Alembic).
- `docs/ETAT_DES_LIEUX.md` — **état des lieux** : où en est le projet (dev/prod),
  décisions et actions en attente. À lire en premier pour reprendre le contexte.
- `docs/SECURITY_AUDIT_2026-07-27.md` — audit de sécurité en cours de remédiation.
- `docs/S2_INFRA_CHECKLIST.md` — action infra en attente (ElastiCache/Redis).
  `docs/S6_INFRA_CHECKLIST.md` est soldé : la bascule vers le rôle admin est
  faite, la clé partagée n'existe plus.
- `docs/S7_RISK_ACCEPTANCE.md` — registre des risques acceptés/différés.
- `docs/GITHUB_SECRETS.md` — secrets CI/CD.
- `infra/` — `Caddyfile`, `dev-db-init.sql`, `CSP.md`, alerting.
