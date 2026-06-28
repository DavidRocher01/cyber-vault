# Procédure de déploiement Rocher Cybersécurité

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
  --cluster cyberscan-prod \
  --task-definition cyberscan-migrate \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

Ou via le Makefile (si configuré) :
```bash
make migrate-prod
```

### Checklist avant migration

- **Snapshot DB** d'abord (cf. § Rollback DB).
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
  --cluster cyberscan-prod \
  --services cyberscan-backend

# 2. Forcer un nouveau déploiement (même image)
aws ecs update-service \
  --cluster cyberscan-prod \
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
  --cluster cyberscan-prod \
  --service cyberscan-backend \
  --task-definition cyberscan-backend:N-1  # remplacer N-1 par le numéro voulu
```

### Rollback DB (snapshot RDS)

```bash
# Créer un snapshot avant tout rollback DB
aws rds create-db-snapshot \
  --db-snapshot-identifier cyberscan-rollback-$(date +%Y%m%d) \
  --db-instance-identifier cyberscan-prod

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
  --db-instance-identifier cyberscan-prod
```

## Variables d'environnement en prod

Gérées via AWS Secrets Manager → injectées dans ECS task definition.
Ne jamais éditer directement dans la task definition (sera écrasé au prochain déploiement).

Pour ajouter/modifier une variable :
1. AWS Console → Secrets Manager → `cyberscan-prod`
2. Modifier la valeur JSON
3. Forcer un nouveau déploiement ECS (voir ci-dessus)

## Vérification post-déploiement

```bash
# Health check rapide (pour ALB)
curl https://rochercybersecurite.com/api/v1/health

# Health check approfondi (DB + Stripe + Resend + S3)
curl https://rochercybersecurite.com/api/v1/health/deep

# Vérifier les logs récents
aws logs tail /ecs/cyberscan-backend --follow --since 5m
```

## Contacts d'urgence

| Service | Contact |
|---------|---------|
| AWS ECS down | Console AWS > Support |
| RDS inaccessible | Console AWS > RDS > Events |
| Stripe webhook KO | dashboard.stripe.com > Webhooks |
| Resend emails KO | app.resend.com > Logs |
| Domaine expiré | Registrar (voir `docs/QUIRKS.md`) |
