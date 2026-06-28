# Rocher Cybersécurité

Plateforme SaaS de cybersécurité B2B — scanner de vulnérabilités, modules de conformité NIS2/ISO 27001/PCA, Dark Web monitoring, simulation phishing, sensibilisation e-learning, RSSI externalisé.

> **Production** : [cyberscanapp.com](https://cyberscanapp.com)
> **Branche prod** : `master` — **branche dev** : `develop`

---

## Stack

| Couche | Technologie | Version |
|--------|-------------|---------|
| Backend | FastAPI + SQLAlchemy async + PostgreSQL | 0.111 / 2.0 / 17 |
| Frontend | Angular standalone + Tailwind CSS + Angular Material | 19 |
| Auth | JWT (access + refresh) + TOTP 2FA | — |
| Chiffrement vault | AES-256-GCM (Web Crypto API côté client) | — |
| Tests | Pytest + Vitest + Playwright | — |
| CI/CD | GitHub Actions → AWS ECS Fargate | — |
| Infra | AWS ECS Fargate + RDS + S3 + CloudFront + Route 53 | — |

---

## Modules

| Module | Description |
|--------|-------------|
| **Scanner** | 21 modules OWASP — SSL/TLS, headers, ports, CVE, threat intel |
| **Code scans** | SAST/SCA via GitHub/GitLab/Bitbucket |
| **NIS2** | Checklist 34 critères, export PDF prêt-à-déposer |
| **ISO 27001** | Auto-évaluation, scoring, export PDF |
| **PCA** | Plan de continuité wizard 4 étapes + export PDF |
| **Dark Web** | Monitoring HIBP + LeakCheck, scoring exposition |
| **Phishing** | Simulation campagnes, 13 scénarios, rapport PDF |
| **Sensibilisation** | 28 modules NIS2 e-learning, attestations SHA-256, gamification |
| **RSSI externalisé** | CRUD missions consultant, livrables S3, rapport PDF |
| **Vault** | Gestionnaire de mots de passe chiffrés côté client |

---

## Lancer en local

### Démarrage rapide (tout-en-un)

```bash
bash scripts/dev-start.sh
```

Le script démarre PostgreSQL (Docker), backend (FastAPI) et frontend (Angular) automatiquement.

### Manuel

**Prérequis** : Python 3.12+, Node.js 20+, Docker

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.prod.txt
cp .env.example .env   # éditer .env avec tes valeurs
python -m alembic upgrade head
uvicorn app.main:app --reload
# → http://localhost:8000/docs

# Frontend (autre terminal)
cd frontend
npm install
npm start
# → http://localhost:4200
```

---

## Tests

```bash
# Backend (nécessite PostgreSQL actif)
cd backend && pytest

# Frontend
cd frontend && npm test

# E2E Playwright
cd frontend && npm run test:e2e
```

Couverture minimale : **81 %** backend (CI bloque en dessous).

---

## Déploiement

Voir [`docs/DEPLOY.md`](docs/DEPLOY.md) pour la procédure complète.

**Résumé** : merger `develop → master` → CI → CD automatique vers ECS Fargate.

---

## Documentation

| Fichier | Contenu |
|---------|---------|
| [`CLAUDE.md`](CLAUDE.md) | Instructions pour Claude Code (AI) |
| [`docs/DEPLOY.md`](docs/DEPLOY.md) | Procédure de déploiement + rollback |
| [`docs/QUIRKS.md`](docs/QUIRKS.md) | Bizarreries connues du codebase |
| [`docs/adr/`](docs/adr/) | Architecture Decision Records |
| [`backend/.env.example`](backend/.env.example) | Variables d'environnement (30+) |

---

## Sécurité

Faille ou vulnérabilité : voir [`SECURITY.md`](SECURITY.md).
