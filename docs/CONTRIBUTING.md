# Contribuer à CyberScan

## Workflow git

- **Branche de travail** : `develop` — jamais committer directement sur `master`
- **Merge sur master** : uniquement après confirmation explicite (déploiement prod)
- **Commits** : format Conventional Commits (`feat:`, `fix:`, `chore:`, `refactor:`, `test:`, `docs:`)

```bash
git checkout develop
git pull origin develop
# ... travailler ...
git add <fichiers spécifiques>
git commit -m "feat(module): description courte"
git push origin develop
```

## Setup local

```bash
# Backend
cd backend
pip install -r requirements.txt          # inclut requirements.prod.txt
cp .env.example .env                     # compléter les valeurs
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm start                                # http://localhost:4200
```

## Tests

```bash
# Backend (depuis backend/)
pytest                                   # tous les tests
pytest tests/test_auth.py -x            # un fichier, stop au premier échec
pytest --cov=app --cov-report=term      # avec couverture
gh run rerun <id> --failed              # relancer uniquement les KO en CI

# Frontend (depuis frontend/)
npm test                                 # Vitest en mode watch
npm run test:coverage                    # avec couverture
npm run test:e2e                         # Playwright E2E (backend doit tourner)
```

**Seuil de couverture** : 84% minimum backend. Le CI bloque si non atteint.

## Linting & formatage

```bash
# Backend
ruff check app/                          # lint
ruff format app/                         # format
mypy app/                                # type checking

# Frontend
npm run lint                             # ESLint
```

Les hooks `pre-commit` lancent ruff, mypy, bandit, prettier et ESLint automatiquement.

```bash
pre-commit install                       # à faire une fois après clone
pre-commit run --all-files               # lancer manuellement
```

## Migrations Alembic

```bash
# Toujours vérifier une seule tête avant de générer
alembic heads                            # doit retourner une seule ligne
alembic revision --autogenerate -m "description courte"
alembic upgrade head                     # appliquer
```

## Architecture

Voir [ARCHITECTURE.md](ARCHITECTURE.md) pour la vue d'ensemble.

Voir [GITHUB_SECRETS.md](GITHUB_SECRETS.md) pour configurer les secrets CI/CD.
