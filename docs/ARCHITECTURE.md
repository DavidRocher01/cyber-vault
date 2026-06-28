# Architecture Rocher Cybersécurité

## Vue d'ensemble

Rocher Cybersécurité est un SaaS de cybersécurité B2B/B2C déployé sur AWS.

```
Internet
    │
    ▼
CloudFront (CDN)
    │
    ├── /                  → S3 (Angular SPA)
    └── /api/v1/*          → ALB → ECS Fargate (FastAPI)
                                         │
                                    ┌────┴────┐
                                    │  Redis  │  APScheduler jobs
                                    │  RDS    │  PostgreSQL 17
                                    │  S3     │  PDF + livrables
                                    └─────────┘
```

## Stack technique

| Couche | Techno |
|--------|--------|
| Frontend | Angular 19 standalone, Tailwind CSS, Vitest, Playwright |
| Backend | FastAPI, SQLAlchemy 2.0 async, Pydantic v2, Alembic |
| Base de données | PostgreSQL 17 (RDS t4g.micro en prod) |
| Cache / jobs | Redis 7 (APScheduler jobstore) |
| Stockage fichiers | S3 (PDFs, livrables RSSI, certificats) |
| Email | Resend (transactionnel) |
| Paiement | Stripe (abonnements + factures) |
| Auth | JWT (access sessionStorage + refresh httpOnly cookie) + TOTP 2FA |
| Vault | Zero-knowledge AES-GCM 256 bits, clé dérivée PBKDF2 côté client |
| CI/CD | GitHub Actions → ECR → ECS Fargate |
| Monitoring | Sentry (erreurs), Plausible (analytics) |

## Structure backend

```
backend/app/
├── api/v1/endpoints/     # Routing + validation Pydantic uniquement
│   ├── awareness/        # E-learning NIS2 (10 fichiers)
│   └── rssi/             # RSSI externalisé (5 fichiers)
├── services/             # Logique métier
│   ├── email_service/    # Emails transactionnels (6 fichiers)
│   └── code_scan/        # Scanner de code (multi-outils)
├── models/               # SQLAlchemy ORM
│   └── enums.py          # StrEnum centralisés
├── schemas/              # Pydantic I/O
└── core/                 # Config, sécurité, DB, utilitaires
```

**Règle stricte des couches** :
- Endpoints → délèguent aux services (pas d'accès DB direct)
- Services → logique métier (pas de schémas HTTP)
- Modèles → pas de logique métier

## Modules fonctionnels

| Module | Description | Audience |
|--------|-------------|----------|
| Scanner | Scan vulnérabilités sites web | B2C + B2B |
| Dark Web | Surveillance fuites email | B2C + B2B |
| Phishing | Campagnes de simulation | B2B |
| RSSI Externalisé | Gestion de missions consultant | B2B |
| Sensibilisation NIS2 | E-learning conformité | B2B |
| Code Scan | Analyse sécurité code source | B2B |
| ISO 27001 / NIS2 | Évaluation conformité | B2B |
| Vault | Gestionnaire mots de passe zero-knowledge | B2C |

## Sécurité

- **SSRF** : `assert_no_ssrf()` avant toute requête HTTP vers URL utilisateur
- **SQL injection** : ORM uniquement, jamais de concaténation SQL
- **XSS** : access_token en sessionStorage, refresh_token httpOnly cookie
- **Vault** : chiffrement AES-GCM côté client, backend stocke blobs opaques
- **Rate limiting** : slowapi (10/min login, 5/min register)
- **2FA** : TOTP RFC 6238

## Déploiement

Voir [DEPLOY.md](DEPLOY.md) pour la procédure complète.
Voir [GITHUB_SECRETS.md](GITHUB_SECRETS.md) pour les secrets CI/CD.
