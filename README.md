# Cyber-Vault

Gestionnaire de mots de passe sécurisé **zero-knowledge** — les mots de passe sont chiffrés côté client avant d'être envoyés au serveur.

## Stack

| Couche | Technologie |
|--------|-------------|
| Backend | FastAPI + SQLAlchemy async + PostgreSQL |
| Frontend | Angular 17 standalone + NgRx ComponentStore |
| Chiffrement | PBKDF2 (100k iter) + AES-256-GCM (Web Crypto API) |
| Auth | JWT access token + refresh token (DB) |
| Tests | Pytest + Vitest + Playwright |
| CI | GitHub Actions |

## Lancer en local

### Prérequis
- Python 3.12+
- Node.js 20+
- PostgreSQL 17

### Backend
```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
```

Créer `backend/.env` :
```env
SECRET_KEY=votre-clé-secrète-64-chars
DATABASE_URL=postgresql+asyncpg://postgres:MOT_DE_PASSE@localhost:5432/cybervault
ALLOWED_ORIGINS=["http://localhost:4200"]
```

```bash
python scripts/migrate.py upgrade head
uvicorn app.main:app --reload
# API : http://localhost:8000
# Docs : http://localhost:8000/docs
```

### Frontend
```bash
cd frontend
npm install
npm start
# App : http://localhost:4200
```

### Tous les tests
```bash
run_tests.bat
```

## Parcours utilisateur

1. **S'inscrire** → `/auth/register`
2. **Se connecter** → JWT + refresh token stockés localement
3. **Mot de passe maître** → dérivation clé AES (reste en mémoire, jamais envoyé)
4. **Vault** → ajout, recherche, affichage, copie (auto-effacement 30s), suppression, export

## Sécurité

- Chiffrement **zero-knowledge** : le serveur ne voit jamais les mots de passe en clair
- **Verrouillage de compte** après 5 tentatives échouées (15 min)
- **Refresh tokens** révocables stockés en base
- **Rate limiting** : 60 req/min (lecture), 30 req/min (écriture)
- **Headers de sécurité** : X-Frame-Options, CSP, HSTS (prod), etc.
- **Hachage bcrypt** des mots de passe utilisateur

## Scripts

```bash
python scripts/backup_db.py          # Backup PostgreSQL (rétention 7 jours)
python scripts/seed_test_db.py       # Injecter données de test
python scripts/migrate.py upgrade head  # Appliquer les migrations
```

## CI/CD

Chaque push sur `main` ou `develop` déclenche :
1. **Backend** : Bandit + pip-audit + migrations Alembic + Pytest
2. **Frontend** : ESLint + Vitest (couverture 70%+) + Build Angular
3. **E2E** : Playwright (Chromium) sur login + vault complets

## Variables d'environnement

| Variable | Obligatoire | Description |
|----------|-------------|-------------|
| `SECRET_KEY` | ✅ | Clé JWT (min 64 chars) |
| `DATABASE_URL` | ✅ | URL PostgreSQL asyncpg |
| `ALLOWED_ORIGINS` | ✅ | Liste JSON des origines CORS |
| `MAX_LOGIN_ATTEMPTS` | — | Tentatives avant verrouillage (défaut: 5) |
| `LOCKOUT_MINUTES` | — | Durée verrouillage en minutes (défaut: 15) |
| `SENTRY_DSN` | — | DSN Sentry pour le monitoring |
| `APP_ENV` | — | `development` ou `production` |
