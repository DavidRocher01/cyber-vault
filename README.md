# Rocher Cybersécurité

Plateforme SaaS de cybersécurité pour les PME — scanner de vulnérabilités,
conformité NIS2 / ISO 27001 / PCA, surveillance Dark Web, simulation de
phishing, sensibilisation e-learning et RSSI externalisé.

> **Production** : [rochercybersecurite.com](https://rochercybersecurite.com)
> — `cyberscanapp.com` reste un alias de l'ancienne marque, servi par la même
> distribution CloudFront.
> **Branche prod** : `master` — **branche dev** : `develop`

---

## Les quatre offres de pointe

L'entrée dans le produit se fait par une offre, pas par un module. Chacune a sa
page vitrine **publique**, accessible sans compte.

| Offre | Vitrine | Application |
|-------|---------|-------------|
| **Conformité NIS2** | `/nis2` | Auto-évaluation 34 critères, PDF prêt à déposer |
| **Sensibilisation** | `/awareness-pricing` | Parcours e-learning + attestations vérifiables |
| **RSSI externalisé** | `/rssi-externalise` | Suivi de mission, livrables, rapports client |
| **Dossier Dark Web** | `/darkweb-offre` | Exposition du domaine dans les fuites connues |

> La distinction vitrine / application compte : la vitrine est publique,
> l'application est derrière `authGuard`. Un lien qui les confond envoie les
> prospects sur le formulaire de connexion — c'est déjà arrivé, et
> `landing-liens-publics.spec.ts` en fait désormais un invariant testé.

### Paliers d'abonnement

`free` · `starter` · `pro` · `business` (`Plan.tier_level` 1 à 4). Ce que chaque
palier ouvre est décrit **une seule fois**, dans
[`frontend/src/app/shared/plan-features.ts`](frontend/src/app/shared/plan-features.ts),
et un test croise cette liste avec les gardes réellement appliquées côté serveur
(`require_min_tier`, blocs `if tier >= N`).

Les tarifs font foi dans [`docs/SALES-BRIEF.md`](docs/SALES-BRIEF.md) — ils ne
sont pas répétés ici pour éviter d'avoir deux vérités.

---

## Modules

| Module | Description |
|--------|-------------|
| **Scanner** | 21 modules — SSL/TLS, en-têtes, ports, CMS, WAF, threat intel, TLS approfondi |
| **Analyse de code** | SAST/SCA via Bandit, Semgrep, pip-audit |
| **NIS2** | 34 critères mappés aux articles de la directive, export PDF |
| **ISO 27001** | Auto-évaluation 2022, scoring, export PDF |
| **PCA** | Plan de continuité, export PDF |
| **Dark Web** | Surveillance HIBP / LeakCheck, score d'exposition, dossier B2B |
| **Phishing** | Campagnes de simulation, 13 scénarios, rapport PDF |
| **Sensibilisation** | 28 modules e-learning, attestations vérifiables, gamification |
| **RSSI externalisé** | Missions consultant, livrables S3, rapport en marque blanche |
| **Vault** | Gestionnaire de mots de passe chiffré côté client |

La profondeur du scan dépend du palier : les modules avancés (empreinte
technologique, takeover de sous-domaine, méthodes HTTP) à partir de `pro`, les
contrôles applicatifs (JWT, clickjacking, redirections ouvertes) en `business`.

---

## Stack

| Couche | Technologie | Version |
|--------|-------------|---------|
| Backend | FastAPI + SQLAlchemy async + PostgreSQL | 0.140 / 2.0 / 17 |
| Frontend | Angular standalone + Tailwind CSS + Angular Material | 21 |
| Auth | JWT (access + refresh) + TOTP 2FA | — |
| Chiffrement vault | AES-256-GCM (Web Crypto, côté client) | — |
| Tests | Pytest + Vitest + Playwright | — |
| CI/CD | GitHub Actions → AWS ECS Fargate | — |
| Infra | AWS ECS Fargate + RDS + S3 + CloudFront + Route 53 | — |

Les versions de runtime ont **une seule source de vérité** : `.python-version`
(3.14) et `.nvmrc` (24). `scripts/check_runtime_versions.py` vérifie en CI que le
`Dockerfile` et `engines.node` restent alignés dessus.

---

## Lancer en local

### Démarrage rapide

```bash
bash scripts/dev-start.sh
```

Démarre PostgreSQL (Docker), le backend et le frontend.

### Manuel

**Prérequis** : Python 3.14, Node.js 24, Docker.

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt      # inclut requirements.prod.txt par référence
cp .env.example .env                 # éditer avec vos valeurs
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
cd backend && pytest                 # Docker requis : les tests montent un PostgreSQL
cd frontend && npm test
cd frontend && npm run test:e2e      # Playwright
```

Couverture minimale : **90 %** backend, la CI bloque en dessous.

### Contrôles qui ne sont pas des tests

Certains défauts ne se voient qu'en regardant le résultat. Deux outils les
rendent vérifiables :

```bash
cd backend
python scripts/preview_pdfs.py --png       # un échantillon de chacun des 12 PDF
python scripts/check_pdf_lisibilite.py     # texte invisible, chevauchements
```

Le second tourne en CI. Il existe parce qu'un changement de thème a rendu un
rapport à moitié illisible — en-têtes écrits en blanc sur blanc — pendant que
1454 tests restaient verts.

---

## Déploiement

Voir [`docs/DEPLOY.md`](docs/DEPLOY.md).

**Résumé** : merger `develop` → `master`, la CI puis le CD s'enchaînent vers ECS
Fargate. Une recette post-production sert de garde-fou et déclenche un rollback
automatique si elle échoue.

---

## Documentation

| Fichier | Contenu |
|---------|---------|
| [`CLAUDE.md`](CLAUDE.md) | Conventions du dépôt et instructions pour Claude Code |
| [`docs/SALES-BRIEF.md`](docs/SALES-BRIEF.md) | Offres et tarifs — source de vérité commerciale |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Architecture système et applicative |
| [`docs/DEPLOY.md`](docs/DEPLOY.md) | Déploiement et rollback |
| [`docs/RELEASE_RUNBOOK.md`](docs/RELEASE_RUNBOOK.md) | Checklist de mise en production |
| [`docs/RECETTE.md`](docs/RECETTE.md) | Recette post-production |
| [`docs/RESTE_A_FAIRE.md`](docs/RESTE_A_FAIRE.md) | Dette et chantiers ouverts |
| [`docs/MONTEES_DEPENDANCES.md`](docs/MONTEES_DEPENDANCES.md) | Montées de versions, avec leurs blocages amont |
| [`docs/QUIRKS.md`](docs/QUIRKS.md) | Bizarreries connues du codebase |
| [`docs/adr/`](docs/adr/) | Architecture Decision Records |
| [`backend/.env.example`](backend/.env.example) | Variables d'environnement |

---

## Sécurité

Signalement d'une faille : [`SECURITY.md`](SECURITY.md).
