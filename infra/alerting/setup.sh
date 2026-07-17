#!/usr/bin/env bash
# Alerting proactif prod — provisionne (idempotent) :
#   - un topic SNS eu-west-3 + abonnement email          (alarmes ALB)
#   - un topic SNS us-east-1 + abonnement email          (Route53, metriques forcees en us-east-1)
#   - alarmes CloudWatch : 5xx ELB, 5xx target, latence p95, healthy host
#   - un health check Route53 externe sur /api/v1/health + alarme "site down"
#
# Pas d'IaC (Terraform/CDK) dans ce repo : ce script EST la source de verite.
# Rejouable sans creer de doublons (create-topic / put-metric-alarm idempotents,
# health check idempotent par caller-reference). Les abonnements email doivent
# etre CONFIRMES via le lien recu par mail.
#
#   ALERT_EMAIL=you@example.com bash infra/alerting/setup.sh
set -euo pipefail

# Git Bash (Windows) convertit sinon "/api/v1/health" en chemin Windows -> le
# create-health-check echoue. Sans effet sur Linux/Mac.
export MSYS_NO_PATHCONV=1

REGION="eu-west-3"
ACCOUNT="328646895533"
EMAIL="${ALERT_EMAIL:-rocherdavid@ymail.com}"
DOMAIN="rochercybersecurite.com"
HEALTH_PATH="/api/v1/health"

LB_DIM="app/cybervault-alb/08207555147b2190"
TG_DIM="targetgroup/cybervault-backend-tg/023275b247bac920"

echo ">> Topic SNS eu-west-3 + abonnement email"
TOPIC=$(aws sns create-topic --name cybervault-alerts --region "$REGION" --query TopicArn --output text)
aws sns subscribe --topic-arn "$TOPIC" --protocol email --notification-endpoint "$EMAIL" --region "$REGION" >/dev/null || true
echo "   $TOPIC"

echo ">> Alarme : 5xx generes par l'ALB (backend injoignable / 502-503-504)"
aws cloudwatch put-metric-alarm --region "$REGION" \
  --alarm-name "cybervault-alb-5xx-elb" \
  --alarm-description "ALB renvoie des 5xx (cible injoignable). Backend probablement KO." \
  --namespace AWS/ApplicationELB --metric-name HTTPCode_ELB_5XX_Count \
  --dimensions "Name=LoadBalancer,Value=$LB_DIM" \
  --statistic Sum --period 300 --evaluation-periods 1 --threshold 5 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --treat-missing-data notBreaching \
  --alarm-actions "$TOPIC" --ok-actions "$TOPIC"

echo ">> Alarme : 5xx applicatifs (l'app repond mais plante)"
aws cloudwatch put-metric-alarm --region "$REGION" \
  --alarm-name "cybervault-alb-5xx-target" \
  --alarm-description "L'app renvoie des 5xx (>=10 / 5 min)." \
  --namespace AWS/ApplicationELB --metric-name HTTPCode_Target_5XX_Count \
  --dimensions "Name=LoadBalancer,Value=$LB_DIM" "Name=TargetGroup,Value=$TG_DIM" \
  --statistic Sum --period 300 --evaluation-periods 1 --threshold 10 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --treat-missing-data notBreaching \
  --alarm-actions "$TOPIC" --ok-actions "$TOPIC"

echo ">> Alarme : latence p95 > 3s"
aws cloudwatch put-metric-alarm --region "$REGION" \
  --alarm-name "cybervault-alb-latency-p95" \
  --alarm-description "Latence backend p95 > 3s sur 2 periodes de 5 min." \
  --namespace AWS/ApplicationELB --metric-name TargetResponseTime \
  --dimensions "Name=LoadBalancer,Value=$LB_DIM" "Name=TargetGroup,Value=$TG_DIM" \
  --extended-statistic p95 --period 300 --evaluation-periods 2 --threshold 3 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching \
  --alarm-actions "$TOPIC" --ok-actions "$TOPIC"

echo ">> Alarme : plus aucune cible saine (backend down, meme sans trafic)"
aws cloudwatch put-metric-alarm --region "$REGION" \
  --alarm-name "cybervault-alb-no-healthy-host" \
  --alarm-description "HealthyHostCount < 1 pendant 3 min : backend down." \
  --namespace AWS/ApplicationELB --metric-name HealthyHostCount \
  --dimensions "Name=LoadBalancer,Value=$LB_DIM" "Name=TargetGroup,Value=$TG_DIM" \
  --statistic Minimum --period 60 --evaluation-periods 3 --threshold 1 \
  --comparison-operator LessThanThreshold \
  --treat-missing-data notBreaching \
  --alarm-actions "$TOPIC" --ok-actions "$TOPIC"

# NB : un health check Route53 externe sur $HEALTH_PATH (detection "site public
# down" au niveau DNS/CloudFront, hors AWS) a ete volontairement ECARTE pour
# rester a cout nul (~2-3 $/mois sinon). Les alarmes ci-dessus couvrent le
# backend (5xx, latence, host sain) et restent dans le free tier (10 alarmes).
# Pour le reactiver un jour : health check HTTPS_STR_MATCH (SearchString=ok) sur
# $DOMAIN$HEALTH_PATH + alarme HealthCheckStatus (metriques Route53 = us-east-1).

echo ""
echo "OK. Confirme l'abonnement email ($EMAIL) via le lien recu."
