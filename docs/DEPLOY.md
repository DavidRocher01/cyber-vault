# Procédure de déploiement Rocher Cybersécurité

> **Cible de production : AWS uniquement** — ECS Fargate (cluster `cybervault-prod`) + RDS PostgreSQL + S3/CloudFront, région `eu-west-3`. Il n'y a **pas** de Render ni de staging actif (le `render.yaml` et le staging Oracle ont été supprimés).

## Architecture de déploiement

```
GitHub (develop) ──PR──► GitHub (master)
                                │
                    CI ─────────┤
                    (.github/workflows/ci.yml)
                                │
                    CD ─────────┤
                    (.github/workflows/deploy.yml)
                                │
                    AWS ECR (images Docker)
                                │
                    AWS ECS Fargate (backend + frontend)
                                │
                    AWS RDS PostgreSQL 17
```

## Pré-requis

- Accès AWS Console (IAM ou rôle ECS)
- AWS CLI configuré : `aws configure`
- GitHub CLI : `gh auth login`
- Accès au repo : `github.com/DavidRocher01/cyber-vault`

## Déploiement standard (CI/CD automatique)

1. Créer une PR `develop → master`
2. Vérifier que le CI est vert (tests + couverture + E2E)
3. Merger la PR
4. Le workflow `deploy.yml` se déclenche automatiquement
5. Surveiller le déploiement dans GitHub Actions
6. Vérifier `https://rochercybersecurite.com/health` après déploiement

## Migrations Alembic en prod

Les migrations **ne tournent pas automatiquement** au démarrage ECS.
Elles doivent être exécutées manuellement via une ECS task :

```bash
# Déclencher la task de migration (adapter le cluster/task-definition)
aws ecs run-task \
  --cluster cybervault-prod \
  --task-definition cyberscan-migrate \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

Ou via le Makefile (si configuré) :
```bash
make migrate-prod
```

### Checklist avant migration

- **Snapshot DB** d'abord (cf. § Rollback DB) — ⚠️ exempté tant qu'il n'y a
  aucun client réel, cf. § Snapshot manuel pré-déploiement.
- Vérifier une seule tête : `alembic heads`.
- Appliquer la migration **avant** de basculer le nouveau code (l'ordre
  `migrate puis deploy` évite qu'un nouveau code écrive dans une colonne
  pas encore élargie).
- Après : `alembic current` confirme la révision.

### ⚠️ Migration `b7f3e1a9c2d4` (totp_secret chiffré au repos)

- Élargit `users.totp_secret` (64→255) : opération **métadonnée seule** en
  PostgreSQL (instantanée, pas de réécriture, pas de lock long).
- Les graines TOTP existantes **en clair continuent de fonctionner** (fallback
  de déchiffrement) — aucune migration de données requise.
- **SECRET_KEY doit rester stable** : la clé de chiffrement TOTP en dérive. Une
  rotation de SECRET_KEY rendrait les graines chiffrées indéchiffrables → 2FA
  cassée. Si rotation prévue : clé dédiée `TOTP_ENC_KEY` ou re-chiffrement avant.
- **Rollback** : redéployer l'ancien code est sûr (fallback). Ne **pas** lancer
  `alembic downgrade` si des graines chiffrées (~140 car) existent déjà
  (re-rétrécir la colonne les tronquerait).

## Déploiement manuel d'urgence

Si le CD est cassé, déploiement manuel :

```bash
# 1. Récupérer l'ID du dernier déploiement réussi
aws ecs describe-services \
  --cluster cybervault-prod \
  --services cyberscan-backend

# 2. Forcer un nouveau déploiement (même image)
aws ecs update-service \
  --cluster cybervault-prod \
  --service cyberscan-backend \
  --force-new-deployment
```

## Rollback

### Rollback ECS (revenir à la task definition précédente)

```bash
# 1. Lister les task definitions récentes
aws ecs list-task-definitions \
  --family-prefix cyberscan-backend \
  --sort DESC \
  --max-items 5

# 2. Revenir à la révision précédente
aws ecs update-service \
  --cluster cybervault-prod \
  --service cyberscan-backend \
  --task-definition cyberscan-backend:N-1  # remplacer N-1 par le numéro voulu
```

### Rollback DB (snapshot RDS)

```bash
# Créer un snapshot avant tout rollback DB
aws rds create-db-snapshot \
  --db-snapshot-identifier cyberscan-rollback-$(date +%Y%m%d) \
  --db-instance-identifier cybervault-prod

# Restaurer depuis un snapshot (opération longue ~15-30 min)
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier cyberscan-restored \
  --db-snapshot-identifier cyberscan-pre-XXXXX
```

## Snapshot manuel pré-déploiement (bonne pratique)

Avant tout déploiement important :

```bash
aws rds create-db-snapshot \
  --db-snapshot-identifier cyberscan-pre-$(git rev-parse --short HEAD) \
  --db-instance-identifier cybervault-prod
```

> **Statut actuel (décision 2026-07-29) :** le snapshot pré-migration est
> **volontairement sauté** tant qu'il n'y a **aucun client réel** en base (seuls
> des comptes de test + le canari de recette). Rien d'irremplaçable à perdre.
> **Dès le premier client signé, il redevient obligatoire** avant toute
> migration — cette exemption tombe à ce moment-là.

## Variables d'environnement en prod

Gérées via AWS Secrets Manager → injectées dans ECS task definition.
Ne jamais éditer directement dans la task definition (sera écrasé au prochain déploiement).

Pour ajouter/modifier une variable :
1. AWS Console → Secrets Manager → `cybervault/prod`
2. Modifier la valeur JSON
3. Forcer un nouveau déploiement ECS (voir ci-dessus)

## Vérification post-déploiement

```bash
# Health check rapide — renvoie aussi la revision Alembic reellement appliquee
# ({"status":"ok",...,"db_revision":"<rev>"}), ce qui evite un exec ECS.
curl https://rochercybersecurite.com/api/v1/health

# Vérifier les logs récents
aws logs tail /ecs/cybervault-backend --follow --since 5m --region eu-west-3
```

> ⚠️ **Le health check approfondi n'est plus joignable depuis Internet.** Il est
> monté à la racine de l'app (`/health/deep`, cf. `backend/app/main.py`), or
> CloudFront ne route que `/api/*` vers le backend : `…/api/v1/health/deep`
> renvoie 404 et `…/health/deep` renvoie la SPA. Le seul chemin restant était
> l'ALB en direct — **fermé le 2026-07-31** (cf. [S2_INFRA_CHECKLIST.md](S2_INFRA_CHECKLIST.md),
> action B2). Passer désormais par une task ECS :
>
> ```bash
> aws ecs execute-command --cluster cybervault --task <task-id> \
>   --container backend --interactive --region eu-west-3 \
>   --command "curl -s localhost:8000/health/deep"
> ```

## Contacts d'urgence

| Service | Contact |
|---------|---------|
| AWS ECS down | Console AWS > Support |
| RDS inaccessible | Console AWS > RDS > Events |
| Stripe webhook KO | dashboard.stripe.com > Webhooks |
| Resend emails KO | app.resend.com > Logs |
| Domaine expiré | Registrar (voir `docs/QUIRKS.md`) |
