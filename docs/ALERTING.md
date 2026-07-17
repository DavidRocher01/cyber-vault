# Alerting proactif — prod

Alarmes CloudWatch sur l'ALB, notifiées par email via SNS. Provisionnées par
`infra/alerting/setup.sh` (pas d'IaC dans ce repo — ce script est la source de
vérité, rejouable sans doublon).

## Alarmes (région eu-west-3, topic SNS `cybervault-alerts`)

| Alarme | Déclenche si | Détecte |
|---|---|---|
| `cybervault-alb-5xx-elb` | `HTTPCode_ELB_5XX_Count` ≥ 5 / 5 min | l'ALB renvoie des 5xx → backend injoignable (502/503/504) |
| `cybervault-alb-5xx-target` | `HTTPCode_Target_5XX_Count` ≥ 10 / 5 min | l'app répond mais plante (5xx applicatifs) |
| `cybervault-alb-latency-p95` | `TargetResponseTime` p95 > 3 s, 2× 5 min | latence dégradée |
| `cybervault-alb-no-healthy-host` | `HealthyHostCount` < 1 pendant 3 min | plus aucune cible saine (backend down, même sans trafic) |

Toutes avec `treat-missing-data = notBreaching` (pas de faux positif quand il n'y
a pas de trafic) et action `OK` (on est notifié aussi du retour à la normale).

## Notification

Topic SNS `cybervault-alerts` → abonnement **email**. ⚠️ L'abonnement doit être
**confirmé** via le lien reçu par mail (sinon aucune notification).

Ajouter un destinataire :
```bash
aws sns subscribe --topic-arn arn:aws:sns:eu-west-3:328646895533:cybervault-alerts \
  --protocol email --notification-endpoint autre@example.com --region eu-west-3
```

## Coût

**~0 €/mois** : les 4 alarmes tiennent dans le free tier CloudWatch (10 alarmes
gratuites), les métriques ALB sont standard (déjà publiées), et les emails SNS
sont gratuits jusqu'à 1 000/mois.

## Volontairement écarté : health check externe (Route53)

Un health check Route53 sur `/api/v1/health` détecterait le cas « site public
injoignable » au niveau **DNS/CloudFront** (hors AWS) — que les alarmes ALB, qui
tournent *dans* AWS, ne voient pas. Il a été retiré pour rester à **coût nul**
(~2–3 $/mois sinon). Pour le réactiver : voir le commentaire en fin de
`infra/alerting/setup.sh` (health check `HTTPS_STR_MATCH`, `SearchString=ok`, +
alarme `HealthCheckStatus` — métriques Route53 forcément en `us-east-1`).

## Ce qui reste (observabilité)

- Erreurs applicatives : **Sentry** (câblé, `SENTRY_DSN`, échantillon traces 10 %).
- Latence 100 % : loggée en CloudWatch (`RequestTimingMiddleware` → Logs Insights).
- Endpoint santé : `GET /api/v1/health` (liveness + DB + révision Alembic).
