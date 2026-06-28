# GitHub Secrets requis

Secrets à configurer dans **Settings → Secrets and variables → Actions** du dépôt `DavidRocher01/cyber-vault`.

## Prod (deploy.yml)

| Secret | Description | Exemple |
|--------|-------------|---------|
| `AWS_DEPLOY_ROLE_ARN` | ARN du rôle IAM OIDC pour le déploiement | `arn:aws:iam::328646895533:role/github-deploy` |
| `AWS_SM_ARN` | ARN complet du secret Secrets Manager prod | `arn:aws:secretsmanager:eu-west-3:328646895533:secret:cybervault/prod-Uqdfdg` |
| `ECS_CLUSTER` | Nom du cluster ECS | `cybervault-prod` |
| `ECS_SERVICE` | Nom du service ECS backend | `cybervault-backend` |
| `S3_BUCKET_NAME` | Bucket S3 du frontend | `cyberscanapp-frontend` |
| `CLOUDFRONT_DISTRIBUTION_ID` | ID de la distribution CloudFront | `E1ABCDEF2GHIJK` |
| `STRIPE_PUBLISHABLE_KEY` | Clé publique Stripe (live) | `pk_live_...` |

## Staging Oracle (deploy-staging.yml)

| Secret | Description |
|--------|-------------|
| `ORACLE_STAGING_HOST` | IP publique de l'instance Oracle ARM64 |
| `ORACLE_STAGING_USER` | Utilisateur SSH (ex: `cyberscan`) |
| `ORACLE_STAGING_SSH_KEY` | Clé privée SSH (PEM, pas de passphrase) |
| `STAGING_BASIC_AUTH` | `user:password` pour le smoke test HTTP |

## Contenu du secret Secrets Manager (`cybervault/prod`)

Le secret AWS Secrets Manager doit contenir ces clés JSON :

```json
{
  "SECRET_KEY": "64+ chars random string",
  "DATABASE_URL": "postgresql+asyncpg://user:pass@host:5432/db",
  "STRIPE_SECRET_KEY": "sk_live_...",
  "STRIPE_WEBHOOK_SECRET": "whsec_...",
  "SMTP_PASSWORD": "...",
  "ADMIN_API_KEY": "...",
  "RESEND_API_KEY": "re_...",
  "SENTRY_DSN": "https://...@sentry.io/..."
}
```

## Rotation recommandée

- `SECRET_KEY` : tous les 90 jours
- `STRIPE_*` : à la demande (incident ou départ employé)
- Clés SSH Oracle : tous les 180 jours
