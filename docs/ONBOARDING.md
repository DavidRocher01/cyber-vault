# Reprise sur un autre poste

Checklist pour repartir de zéro sur une nouvelle machine. Le **code** est dans
git (branche `develop`) ; il ne manque que l'**environnement local** (jamais
versionné) et, si tu y tiens, le **contexte Claude** (voir la fin).

## 1. Prérequis à installer

| Outil | Version | Pourquoi |
|---|---|---|
| Git | — | cloner le repo |
| Python | **3.14** | backend (iso-prod) |
| Node.js | **20** | frontend Angular 20 |
| PostgreSQL | **17** | base locale (iso-prod) |
| Docker | — | `make prod-check` (parité prod Linux) — optionnel |
| AWS CLI | v2 | ops prod (ECS, logs, alarmes, Secrets Manager) |
| GitHub CLI (`gh`) | — | CI, PR, `gh run` |

> Pas de fichier de version épinglé (`.nvmrc`/`.python-version`) : se fier à ce tableau et à `CLAUDE.md`.

## 2. Cloner + se placer sur develop

```bash
git clone https://github.com/DavidRocher01/cyber-vault.git
cd cyber-vault
git checkout develop
```

## 3. Backend

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash ; Linux/Mac : source .venv/bin/activate
pip install -r requirements.txt    # = deps prod + outils de test/lint
cp .env.example .env               # puis EDITER (voir ci-dessous)
alembic upgrade head               # applique le schéma sur la base locale
uvicorn app.main:app --reload      # http://localhost:8000
```

`.env` local **minimal pour démarrer** (⚠️ secrets **jamais** dans git — les vraies
valeurs prod sont dans AWS Secrets Manager `cybervault/prod`) :

```env
APP_ENV=development                # active is_dev_mode (endpoints /dev/*, checkout test)
SECRET_KEY=<openssl rand -hex 32>  # min 64 chars
DATABASE_URL=postgresql+asyncpg://cybervault:cybervault@localhost:5432/cybervault
ALLOWED_ORIGINS=["http://localhost:4200"]
FRONTEND_URL=http://localhost:4200
ADMIN_API_KEY=<openssl rand -hex 32>
# REDIS_URL vide => APScheduler/limiter in-memory (comme la prod, mono-instance)
```

Ces 6 variables suffisent à **booter** l'app et lancer les tests. **`backend/.env.example`
est la référence complète (34 variables)** : les fonctionnalités suivantes ne
marchent que si tu renseignes leurs clés (sinon elles sont inertes ou en mode dev) :
- **Stripe** (`STRIPE_*`, addons) — paiement/checkout (en dev, checkout mock via `is_dev_mode`).
- **Email** : `RESEND_API_KEY` (+ `RESEND_FROM`) ou `SMTP_*` — invitations RSSI, resets, contact.
- **Dark Web** : `HIBP_API_KEY` — scans HIBP (payant).
- **Phishing** : `PHISHING_BASE_URL` (doit inclure `/api/v1`), `PHISHING_FROM_*`.
- **Sentry** : `SENTRY_DSN` (laisser vide en dev).

Créer la base au préalable (Postgres natif) : une base `cybervault` + un rôle
`cybervault`. Pour une **parité exacte** avec la prod (collation `en_US.UTF-8`,
rôle non-superuser), utiliser plutôt `make prod-check` (backend dans l'image prod
Docker) — cf `docs/` et le Makefile.

## 4. Frontend

```bash
cd frontend
npm install
npm start          # http://localhost:4200 ; proxifie /api -> http://localhost:8000
```

## 5. Outils d'ops (pour agir sur la prod)

```bash
aws configure       # ou SSO ; région eu-west-3, compte 328646895533
gh auth login
```

## 6. Vérifier que tout tourne

```bash
make install        # (à la racine) deps back+front + hooks pre-commit
make test-backend-fast          # tests backend rapides
cd frontend && npm test         # tests front (Vitest)
make prod-check                 # OPTIONNEL : backend en image prod + smoke (avant un deploy sensible)
make recette                    # recette post-prod contre la PROD (creds canari depuis Secrets Manager)
```

## 6b. Config de dev déjà versionnée (rien à faire)

Ces éléments **arrivent avec le `git clone`**, aucune reconfiguration :
- Configs qualité : ruff / mypy / bandit (backend), ESLint / Prettier (frontend).
- `.pre-commit-config.yaml` (14 hooks) — activés par `make install`.
- `docker-compose.dev.yml` (parité prod : `make prod-check`), `docker-compose.edge.yml`
  (reverse proxy iso-edge : `make edge`), `infra/dev-db-init.sql` (rôle/collation).
- `Makefile` = hub des commandes → `make help` liste tout.

Machine-spécifique / non versionné (à refaire) : `.venv`, `node_modules`,
navigateurs Playwright (`npx playwright install chromium` pour les E2E/recette UI),
`.env`, creds AWS/gh, et **la config VS Code** (`.vscode/` est gitignoré — voir ci-dessous).

### VS Code (`.vscode/` est gitignoré → à recréer)

`.vscode/settings.json` recommandé (formateur = **ruff**, cohérent avec le
pre-commit ; sur Linux/Mac remplacer l'interpréteur par `.venv/bin/python`) :

```jsonc
{
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/.venv/Scripts/python.exe",
  "python.terminal.activateEnvironment": true,
  "python.analysis.extraPaths": ["${workspaceFolder}/backend"],
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": { "source.fixAll.ruff": "explicit" }
  },
  "[typescript]": { "editor.defaultFormatter": "esbenp.prettier-vscode", "editor.formatOnSave": true },
  "[html]":       { "editor.defaultFormatter": "esbenp.prettier-vscode", "editor.formatOnSave": true },
  "editor.rulers": [88],
  "files.exclude": {
    "**/__pycache__": true, "**/.pytest_cache": true,
    "**/node_modules": true, "**/.angular": true, "**/dist": true
  }
}
```

Extensions à installer : **Ruff** (`charliermarsh.ruff`), **Python** (`ms-python.python`),
**Prettier** (`esbenp.prettier-vscode`), **ESLint** (`dbaeumer.vscode-eslint`),
**Angular Language Service** (`angular.ng-template`).

## 7. Repères

- `CLAUDE.md` — règles du projet (branches, Alembic, archi, sécurité).
- `docs/RECETTE.md` — recette post-prod + gate/rollback.
- `docs/ALERTING.md` — alarmes CloudWatch.
- `infra/alerting/setup.sh` — provisioning alerting (idempotent).
- Workflow : bosser sur `develop`, merger sur `master` = déploiement prod (voir CLAUDE.md).

## 8. (Optionnel) Reprendre le contexte Claude Code

La conversation et la mémoire Claude sont **locales** (`~/.claude/…`), pas dans le
repo. Pour les transférer :

- **Mémoire** (décisions non-évidentes : pièges DB, recette, alerting, RSSI…) :
  copier le dossier `memory/` depuis
  `…/.claude/projects/<hash-du-chemin-projet>/memory/` vers le dossier équivalent
  sur la nouvelle machine. Le `<hash>` dérive du **chemin absolu du projet** →
  mettre le projet au même chemin, ou lancer d'abord une session (Claude crée le
  dossier) puis y déposer les fichiers.
- **Conversation exacte** : copier aussi le `.jsonl` de session puis `claude --resume`.

> ⚠️ Ne **jamais** committer le dossier `memory/` : le repo est public.

Le plus simple si l'historique t'importe peu : cloner + **nouvelle session** dans
le dossier — `CLAUDE.md` + le code donnent déjà l'essentiel du contexte.
