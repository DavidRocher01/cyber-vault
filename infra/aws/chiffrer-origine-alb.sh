#!/usr/bin/env bash
#
# Chiffre le trafic entre CloudFront et l'ALB.
#
# POURQUOI. CloudFront va chercher l'API en clair : l'origine est declaree
# `http-only`. Le trafic reste dans le reseau AWS, mais l'ecouteur 443 de l'ALB
# existe deja avec un certificat ACM valide — il ne manque qu'une regle de
# groupe de securite. Autant fermer.
#
# L'ORDRE EST IMPERATIF. Basculer CloudFront avant d'avoir ouvert le port 443
# coupe l'API. Chaque etape verifie la precedente, et chacune est rejouable :
# une etape deja faite est constatee, pas refaite.
#
# Usage :  bash infra/aws/chiffrer-origine-alb.sh
#
# ---------------------------------------------------------------------------
# CE QUI A DEJA ETE FAIT, ET CE QUE CA A APPRIS
#
# 2026-08-16 — la regle de priorite 1 exigeant l'en-tete `X-Origin-Verify` a ete
# repliquee sur l'ecouteur 443, a l'identique de celle du port 80. Sans elle, la
# bascule aurait SUPPRIME cette protection : le 443 renvoyait tout au backend
# sans rien verifier.
#
# 2026-08-17 — etape 1 appliquee : l'action par defaut du 443 est passee de
# `forward` a un 403. Elle est donc acquise, independamment de la suite.
#
# 2026-08-17 — DEUX PIEGES RENCONTRES, gardes ici pour qu'ils ne reviennent pas.
#
#   1. Le test prealable de ce script cherchait `Rules[?Priority==`1`]`. Il
#      renvoyait TOUJOURS zero : `Priority` est la CHAINE "1", et le litteral
#      JMESPath entre accents graves un NOMBRE. Le script refusait de demarrer
#      alors que la regle etait bien la. Il cherche desormais l'en-tete lui-meme,
#      qui est ce qui protege — un numero de priorite, ca se renumerote.
#
#   2. `RulesPerSecurityGroupLimitExceeded` sur un groupe qui ne contenait que
#      DEUX regles. Une liste de prefixes geree ne compte pas pour 1 : elle
#      compte pour sa taille maximale. `com.amazonaws.global.cloudfront.
#      origin-facing` pese 55 (46 adresses au 2026-08-17, plafond 55) sur un
#      quota de 60 par groupe. Une seule regle « depuis CloudFront » tient donc
#      par groupe ; le 80 et le 443 en demanderaient 111.
#      D'ou `sg-032a3ebe1d53d63a8`, cree le 2026-08-17 pour porter le seul 443.
#      Il est TEMPORAIRE : quand la regle du port 80 sera retiree, sa place se
#      libere, le 443 rejoint le groupe principal et ce groupe-ci disparait.
# ---------------------------------------------------------------------------

set -euo pipefail

DISTRIBUTION="E3DFNMKIHVBDO1"
GROUPE_ALB="sg-040da241f674d9b8c"        # porte le 80 depuis CloudFront
GROUPE_HTTPS="sg-032a3ebe1d53d63a8"      # porte le 443 depuis CloudFront
TRAVAIL="$(mktemp -d)"

echo "== 0. Verifications prealables =="
ARN=$(aws elbv2 describe-load-balancers --names cybervault-alb \
  --query 'LoadBalancers[0].LoadBalancerArn' --output text)
L443=$(aws elbv2 describe-listeners --load-balancer-arn "$ARN" \
  --query "Listeners[?Port==\`443\`].ListenerArn" --output text)

# La regle d'en-tete DOIT exister sur le 443 avant d'ouvrir le port. On cherche
# l'en-tete, pas la priorite : cf. piege 1 en tete de fichier.
REGLES=$(aws elbv2 describe-rules --listener-arn "$L443" \
  --query "length(Rules[?Conditions[?HttpHeaderConfig.HttpHeaderName=='X-Origin-Verify']])" \
  --output text)
if [ "$REGLES" != "1" ]; then
  echo "ARRET : la regle X-Origin-Verify manque sur l'ecouteur 443." >&2
  echo "Ouvrir le port sans elle exposerait le backend sans verification." >&2
  exit 1
fi
echo "   regle d'en-tete presente sur le 443 : ok"

# Le groupe dedie doit exister et porter le 443. Sinon, rien a attacher.
PORTE=$(aws ec2 describe-security-group-rules \
  --filters "Name=group-id,Values=$GROUPE_HTTPS" \
  --query "length(SecurityGroupRules[?FromPort==\`443\` && PrefixListId!=null])" \
  --output text)
if [ "$PORTE" != "1" ]; then
  echo "ARRET : $GROUPE_HTTPS ne porte pas la regle 443 depuis CloudFront." >&2
  exit 1
fi
echo "   groupe $GROUPE_HTTPS porte le 443 : ok"

echo "== 1. Fermer la porte par defaut du 443 =="
# Sans cela, une requete qui atteint le 443 sans l'en-tete est transmise au
# backend — exactement ce que le port 80 refuse.
DEFAUT=$(aws elbv2 describe-listeners --load-balancer-arn "$ARN" \
  --query "Listeners[?Port==\`443\`].DefaultActions[0].Type" --output text)
if [ "$DEFAUT" = "fixed-response" ]; then
  echo "   deja ferme (403) — rien a faire"
else
  aws elbv2 modify-listener --listener-arn "$L443" \
    --default-actions 'Type=fixed-response,FixedResponseConfig={MessageBody="Direct origin access denied",StatusCode=403,ContentType=text/plain}' \
    --query 'Listeners[0].DefaultActions[0].Type' --output text
fi

echo "== 2. Attacher le groupe HTTPS a l'ALB =="
# `set-security-groups` REMPLACE la liste : les deux groupes doivent y figurer.
# Le 80 reste ouvert — c'est le chemin de retour arriere.
ACTUELS=$(aws elbv2 describe-load-balancers --names cybervault-alb \
  --query 'LoadBalancers[0].SecurityGroups' --output text)
case "$ACTUELS" in
  *"$GROUPE_HTTPS"*)
    echo "   deja attache — rien a faire" ;;
  *)
    aws elbv2 set-security-groups --load-balancer-arn "$ARN" \
      --security-groups "$GROUPE_ALB" "$GROUPE_HTTPS" \
      --query 'SecurityGroupIds' --output text ;;
esac

echo "== 3. Basculer l'origine CloudFront en https-only =="
POLITIQUE=$(aws cloudfront get-distribution-config --id "$DISTRIBUTION" \
  --query "DistributionConfig.Origins.Items[?contains(Id,'alb')].CustomOriginConfig.OriginProtocolPolicy" \
  --output text)
if [ "$POLITIQUE" = "https-only" ]; then
  echo "   deja en https-only — rien a faire"
else
  aws cloudfront get-distribution-config --id "$DISTRIBUTION" > "$TRAVAIL/dist.json"
  ETAG=$(python -c "import json;print(json.load(open(r'$TRAVAIL/dist.json'))['ETag'])")

  python - "$TRAVAIL" <<'PY'
import json, sys, pathlib
t = pathlib.Path(sys.argv[1])
d = json.loads((t / "dist.json").read_text(encoding="utf-8"))
cfg = d["DistributionConfig"]
touchees = 0
for o in cfg["Origins"]["Items"]:
    custom = o.get("CustomOriginConfig")
    if custom and "alb" in o["Id"]:
        custom["OriginProtocolPolicy"] = "https-only"
        touchees += 1
if touchees != 1:
    raise SystemExit(f"ARRET : {touchees} origine(s) ALB trouvee(s), 1 attendue")
(t / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
print("   origine ALB basculee en https-only")
PY

  aws cloudfront update-distribution --id "$DISTRIBUTION" \
    --distribution-config "file://$TRAVAIL/config.json" --if-match "$ETAG" \
    --query 'Distribution.Status' --output text
fi

echo
echo "== 4. Verifier (le deploiement CloudFront prend quelques minutes) =="
echo "   aws cloudfront get-distribution --id $DISTRIBUTION --query 'Distribution.Status' --output text"
echo "   curl -s -o /dev/null -w '%{http_code}\\n' https://rochercybersecurite.com/api/v1/plans   # doit repondre 200"
echo
echo "En cas de probleme : rebasculer l'origine en 'http-only' par la meme"
echo "methode. Le port 80 reste ouvert et sa regle intacte — le chemin d'avant"
echo "fonctionne toujours. Ne fermer le 80 qu'apres plusieurs jours en 443 ;"
echo "ce jour-la, deplacer le 443 dans $GROUPE_ALB et supprimer $GROUPE_HTTPS."
