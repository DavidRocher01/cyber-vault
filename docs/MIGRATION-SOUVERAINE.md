# Runbook — Migration vers un hébergeur souverain (Scaleway / OVH)

> Plan de sortie d'AWS vers un cloud français, **au cas où** un client exige une souveraineté
> totale (hors CLOUD Act US). **À déclencher sur besoin réel, pas spéculativement.**
> Aujourd'hui l'hébergement AWS Paris (eu-west-3) est déjà conforme RGPD (données en France).

## 1. Verdict de portabilité (audit du code, 2026)

**L'application est ~95 % portable.** Verrouillage AWS quasi nul :

| Élément | Couplage AWS | Portable ? |
|---|---|---|
| Code applicatif (FastAPI, Angular) | aucun | ✅ |
| Docker | `python:3.12-slim` standard | ✅ |
| Secrets / config | lus en **variables d'environnement** (aucun appel Secrets Manager dans le code) | ✅ |
| CloudWatch / SNS | **aucun appel SDK** (juste des logs stdout + des alarmes définies côté infra) | ✅ |
| Base de données | PostgreSQL standard (pas de service AWS propriétaire) | ✅ |
| **Stockage S3** | `boto3.client("s3")` **sans `endpoint_url`** → codé sur AWS | 🟠 **1 modif** |
| `deploy.yml` | 15 commandes `aws` (ECS/S3/CloudFront/ECR) | 🟠 à réécrire (cible) |
| Auth S3 | rôle IAM de tâche (pas de clés) | 🟠 → clés statiques (env) |

**Le seul changement de code** = rendre l'endpoint S3 configurable (voir §3). Tout le reste est
du provisioning d'infra + une réécriture du pipeline de déploiement.

## 2. Reco : Scaleway plutôt qu'OVH pour CETTE stack

| Besoin | AWS actuel | **Scaleway** (reco) | OVH |
|---|---|---|---|
| Conteneurs | ECS Fargate | **Serverless Containers** (≈ Fargate, pas de K8s) | Kubernetes managé ou VM+Docker |
| PostgreSQL | RDS | Managed Database PostgreSQL | Managed Databases |
| Stockage objet | S3 | Object Storage (S3-compatible) | Object Storage (S3-compatible) |
| Secrets | Secrets Manager | **Secret Manager** natif | ❌ (env / Vault self-hosted) |
| Registry Docker | ECR | Container Registry | Managed Private Registry (Harbor) |
| CDN + TLS | CloudFront | Edge Services / LB + Let's Encrypt | CDN OVH / reverse-proxy |
| DNS | Route 53 | Scaleway DNS | OVH DNS |

→ **Scaleway** (français, datacenters Paris) reproduit presque le modèle AWS (serverless
containers + secret manager + S3-compatible) **sans passer à Kubernetes**. Migration la plus douce.

## 3. Le seul changement de code — endpoint S3 configurable

Aujourd'hui (3-4 appels, `storage.py`, `awareness_certificate_service.py`, `main.py`) :
```python
s3 = boto3.client("s3", region_name=settings.AWS_REGION)
```
À rendre configurable (comportement AWS inchangé quand la variable est vide) :
```python
# config.py — ajouter :
S3_ENDPOINT_URL: str = ""   # ex. https://s3.fr-par.scw.cloud (vide = AWS par défaut)

# chaque appel boto3 :
s3 = boto3.client(
    "s3",
    region_name=settings.AWS_REGION,
    endpoint_url=settings.S3_ENDPOINT_URL or None,
)
```
+ fournir `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (clés Object Storage du fournisseur) en
variables d'environnement — `boto3` les prend automatiquement. **C'est tout, côté code.**

## 4. Étapes de migration (le jour venu)

1. **Provisionner** chez le fournisseur : PostgreSQL managé, Object Storage (2 buckets : front + livrables),
   Container Registry, compute (Serverless Containers), Secret Manager, LB/CDN + TLS.
2. **Adapter le code** : `S3_ENDPOINT_URL` (§3), retirer toute hypothèse CloudWatch (déjà quasi rien).
3. **Réécrire le pipeline** : `deploy.yml` → build image → push registry → déploiement conteneur.
   (GitHub Actions reste ; seules les commandes de déploiement changent.)
4. **Migrer les données** :
   - Base : `pg_dump` (RDS) → `pg_restore` (PG managé). Fenêtre de bascule courte.
   - Fichiers : copie S3 → Object Storage (`rclone` ou `aws s3 sync` avec double endpoint).
5. **Secrets** : recopier dans le Secret Manager cible (mêmes clés qu'aujourd'hui).
6. **Monitoring** : recréer les alarmes (Grafana/uptime) ; Sentry reste inchangé (SaaS indépendant).
7. **Bascule DNS** : baisser le TTL J-1, basculer les enregistrements, garder AWS chaud pour rollback.
8. **Vérifier** : smoke tests (racine, /plans, /vault 401), parcours paiement, upload livrable.

## 5. Effort & risques
- **Effort** : ~2-4 jours (surtout : pipeline, provisioning, tests de bascule). Pas une réécriture.
- **Risque principal** : la bascule DNS + la cohérence des données pendant la migration → faire une
  répétition sur un environnement de staging avant la prod.
- **Réversibilité** : garder l'infra AWS active jusqu'à validation complète (rollback DNS immédiat).

## 6. Hedge à coût nul (optionnel, dès aujourd'hui)
La seule chose qui vaut la peine d'être faite **avant** un besoin réel : appliquer le §3
(`S3_ENDPOINT_URL` configurable). Zéro impact en prod (vide = AWS), mais rend le stockage
100 % agnostique. Le reste ne doit PAS être fait spéculativement.
