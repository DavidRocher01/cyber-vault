# Alerting proactif — prod

Alarmes CloudWatch sur l'ALB/ECS/RDS, notifiées par email via le topic SNS
**`cybervault-prod-alertes`** (région eu-west-3, abonnement email **déjà
confirmé**). Pas d'IaC dans ce repo : `infra/alerting/setup.sh` ajoute les
alarmes manquantes (idempotent) et fait foi.

## Alarmes (toutes → `cybervault-prod-alertes`)

| Alarme | Déclenche si | Détecte | Origine |
|---|---|---|---|
| `cybervault-alb-5xx-elb` | `HTTPCode_ELB_5XX_Count` ≥ 5 / 5 min | l'ALB renvoie des 5xx → backend injoignable | ajoutée |
| `cybervault-alb-latency-p95` | `TargetResponseTime` p95 > 3 s, 2× 5 min | latence dégradée | ajoutée |
| `cybervault-backend-5xx` | `HTTPCode_Target_5XX_Count` > 10 / 5 min | l'app répond mais plante | préexistante |
| `cybervault-backend-DOWN` | `HealthyHostCount` < 1 | plus aucune cible saine | préexistante |
| `cybervault-ecs-cpu-eleve` | ECS `CPUUtilization` > 85 % | backend saturé | préexistante |
| `cybervault-rds-cpu-eleve` | RDS `CPUUtilization` > 85 % | DB saturée | préexistante |
| `cybervault-rds-stockage-bas` | RDS `FreeStorageSpace` < 2 Go | disque DB bientôt plein | préexistante |

Les 2 ajoutées ont `treat-missing-data = notBreaching` (pas de faux positif sans
trafic) + action `OK` (notif du retour à la normale).

> **Attention doublons** : `cybervault-backend-5xx` couvre déjà les 5xx
> **applicatifs** (target) et `cybervault-backend-DOWN` le healthy-host. Ne pas
> re-créer d'alarmes sur ces mêmes métriques. Les 2 ajoutées comblent les vrais
> trous : 5xx **niveau ALB** et **latence** (aucune alarme de latence avant).

## Coût

**~0 €/mois** : 7 alarmes ≤ **10 gratuites** (free tier CloudWatch, résolution
standard) ; métriques ALB/ECS/RDS standard ; emails SNS gratuits (< 1 000/mois).

Ajouter un destinataire :
```bash
aws sns subscribe --topic-arn arn:aws:sns:eu-west-3:328646895533:cybervault-prod-alertes \
  --protocol email --notification-endpoint autre@example.com --region eu-west-3
```

## Volontairement écarté : health check externe (Route53)

Un health check Route53 sur `/api/v1/health` détecterait « site public
injoignable » au niveau **DNS/CloudFront** (hors AWS), que les alarmes ALB — qui
tournent *dans* AWS — ne voient pas. Écarté pour rester à **coût nul** (~2–3 $/mois
sinon). Réactivation : health check `HTTPS_STR_MATCH` (`SearchString=ok`) sur
`rochercybersecurite.com/api/v1/health` + alarme `HealthCheckStatus` (métriques
Route53 = `us-east-1`).

## Reste de l'observabilité

- Erreurs applicatives : **Sentry** (`SENTRY_DSN`, échantillon traces 10 %).
- Latence 100 % : loggée en CloudWatch (`RequestTimingMiddleware` → Logs Insights).
- Santé : `GET /api/v1/health` (liveness + DB + révision Alembic).
