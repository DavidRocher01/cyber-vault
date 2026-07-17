#!/usr/bin/env bash
# Alerting proactif prod — alarmes CloudWatch sur l'ALB, notifiees par email.
#
# Le compte a DEJA un topic SNS `cybervault-prod-alertes` (email confirme) et 5
# alarmes preexistantes : backend-5xx (target 5xx), backend-DOWN (healthy host),
# ecs-cpu-eleve, rds-cpu-eleve, rds-stockage-bas. Ce script AJOUTE seulement ce
# qui manquait, sur le MEME topic :
#   - 5xx generes par l'ALB (backend injoignable, distinct des 5xx applicatifs)
#   - latence backend p95
#
# Pas d'IaC (Terraform/CDK) : ce script est la source de verite. Idempotent
# (put-metric-alarm ecrase par nom).
#
#   bash infra/alerting/setup.sh
set -euo pipefail

REGION="eu-west-3"
TOPIC="arn:aws:sns:eu-west-3:328646895533:cybervault-prod-alertes"  # existant, email confirme
LB_DIM="app/cybervault-alb/08207555147b2190"
TG_DIM="targetgroup/cybervault-backend-tg/023275b247bac920"

echo ">> Alarme : 5xx generes par l'ALB (cible injoignable / 502-503-504)"
aws cloudwatch put-metric-alarm --region "$REGION" \
  --alarm-name "cybervault-alb-5xx-elb" \
  --alarm-description "ALB renvoie des 5xx (cible injoignable). Backend probablement KO." \
  --namespace AWS/ApplicationELB --metric-name HTTPCode_ELB_5XX_Count \
  --dimensions "Name=LoadBalancer,Value=$LB_DIM" \
  --statistic Sum --period 300 --evaluation-periods 1 --threshold 5 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --treat-missing-data notBreaching \
  --alarm-actions "$TOPIC" --ok-actions "$TOPIC"

echo ">> Alarme : latence backend p95 > 3s"
aws cloudwatch put-metric-alarm --region "$REGION" \
  --alarm-name "cybervault-alb-latency-p95" \
  --alarm-description "Latence backend p95 > 3s sur 2 periodes de 5 min." \
  --namespace AWS/ApplicationELB --metric-name TargetResponseTime \
  --dimensions "Name=LoadBalancer,Value=$LB_DIM" "Name=TargetGroup,Value=$TG_DIM" \
  --extended-statistic p95 --period 300 --evaluation-periods 2 --threshold 3 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching \
  --alarm-actions "$TOPIC" --ok-actions "$TOPIC"

echo ""
echo "OK. 7 alarmes au total (5 preexistantes + ces 2) sur $TOPIC."
echo "Aucun abonnement a confirmer : le topic a deja un email confirme."
