# ADR 0001 — Choix de FastAPI pour le backend

**Statut** : Accepté
**Date** : 2024-01

---

## Contexte

Le backend de Cyber-Vault doit exposer une API REST consommée par un frontend Angular et potentiellement par des clients tiers. Les contraintes principales sont :

- Performances élevées (vault chiffré, nombreux appels API)
- Validation stricte des données entrantes
- Documentation API auto-générée (OpenAPI)
- Support async natif (opérations I/O intensives : DB, emails, S3, APIs externes)
- Typage Python pour la maintenabilité

## Options évaluées

| Framework | Avantages | Inconvénients |
|-----------|-----------|---------------|
| **FastAPI** | Async natif, Pydantic intégré, OpenAPI auto, performances | Moins mature qu'alternatives |
| **Django REST Framework** | Très mature, ORM intégré, admin | WSGI par défaut, plus lourd |
| **Flask** | Simple, flexible | Peu opinionated, validation manuelle |

## Décision

**FastAPI** est retenu pour les raisons suivantes :

1. **Async natif** : SQLAlchemy 2.0 async + asyncpg permettent des connexions DB non-bloquantes, indispensable pour la scalabilité
2. **Pydantic** : validation des données et sérialisation intégrées, typage strict des schémas
3. **OpenAPI automatique** : documentation interactive générée sans effort, utile pour le debugging et les intégrations
4. **Performances** : comparable à Node.js/Go sur les benchmarks I/O-bound

## Conséquences

**Positives :**
- Validation des données centralisée et typée
- Documentation API toujours synchronisée avec le code
- Code async cohérent du endpoint jusqu'à la DB

**Négatives :**
- Pas d'ORM intégré → SQLAlchemy 2.0 ajouté séparément
- Migrations manuelles via Alembic
- Courbe d'apprentissage pour les patterns async

**Mitigation :**
- SQLAlchemy 2.0 + Alembic = solution mature et bien documentée
- Patterns async bien établis dans le projet (voir `app/core/database.py`)
