#!/usr/bin/env bash
#
# Chiffre le trafic entre CloudFront et l'ALB.
#
# POURQUOI. CloudFront allait chercher l'API en clair : l'origine etait declaree
# `http-only`. Le trafic reste dans le reseau AWS, mais l'ecouteur 443 de l'ALB
# existait deja avec un certificat ACM valide — il ne manquait qu'une regle de
# groupe de securite. Autant fermer.
#
# CE QUI A DEJA ETE FAIT (le 2026-08-16) : la regle de priorite 1 exigeant
# l'en-tete `X-Origin-Verify` a ete repliquee sur l'ecouteur 443, a l'identique
# de celle du port 80. Sans elle, la bascule aurait SUPPRIME cette protection :
# le 443 renvoyait tout au backend sans rien verifier.
#
# L'ORDRE EST IMPERATIF. Basculer CloudFront avant d'avoir ouvert le port 443
# coupe l'API. Chaque etape verifie la precedente.
#
# Usage :  bash infra/aws/chiffrer-origine-alb.sh

set -euo pipefail

DISTRIBUTION="E3DFNMKIHVBDO1"
GROUPE_ALB="sg-040da241f674d9b8c"
PREFIXE_CLOUDFRONT="pl-75b1541c"
TRAVAIL="$(mktemp -d)"

echo "== 0. Verifications prealables =="
ARN=$(aws elbv2 describe-load-balancers --names cybervault-alb \
  --query 'LoadBalancers[0].LoadBalancerArn' --output text)
L443=$(aws elbv2 describe-listeners --load-balancer-arn "$ARN" \
  --query "Listeners[?Port==\`443\`].ListenerArn" --output text)

# La regle d'en-tete DOIT exister sur le 443 avant d'ouvrir le port.
REGLES=$(aws elbv2 describe-rules --listener-arn "$L443" \
  --query 'length(Rules[?Priority==`1`])' --output text)
if [ "$REGLES" != "1" ]; then
  echo "ARRET : la regle X-Origin-Verify manque sur l'ecouteur 443." >&2
  echo "Ouvrir le port sans elle exposerait le backend sans verification." >&2
  exit 1
fi
echo "   regle d'en-tete presente sur le 443 : ok"

echo "== 1. Fermer la porte par defaut du 443 =="
# Sans cela, une requete qui atteint le 443 sans l'en-tete est transmise au
# backend — exactement ce que le port 80 refuse.
aws elbv2 modify-listener --listener-arn "$L443" \
  --default-actions 'Type=fixed-response,FixedResponseConfig={MessageBody="Direct origin access denied",StatusCode=403,ContentType=text/plain}' \
  --query 'Listeners[0].DefaultActions[0].Type' --output text

echo "== 2. Ouvrir le 443 depuis CloudFront uniquement =="
# La liste de prefixes gerée `pl-75b1541c` couvre les adresses CloudFront. Le
# port reste ferme a Internet.
aws ec2 authorize-security-group-ingress --group-id "$GROUPE_ALB" \
  --ip-permissions "IpProtocol=tcp,FromPort=443,ToPort=443,PrefixListIds=[{PrefixListId=$PREFIXE_CLOUDFRONT,Description=HTTPS depuis CloudFront}]" \
  --query 'SecurityGroupRules[0].SecurityGroupRuleId' --output text

echo "== 3. Basculer l'origine CloudFront en https-only =="
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
print(f"   origine ALB basculee en https-only")
PY

aws cloudfront update-distribution --id "$DISTRIBUTION" \
  --distribution-config "file://$TRAVAIL/config.json" --if-match "$ETAG" \
  --query 'Distribution.Status' --output text

echo "== 4. Verifier (le deploiement CloudFront prend quelques minutes) =="
echo "   aws cloudfront get-distribution --id $DISTRIBUTION --query 'Distribution.Status' --output text"
echo "   curl -s -o /dev/null -w '%{http_code}\\n' https://rochercybersecurite.com/api/v1/plans   # doit repondre 200"
echo
echo "En cas de probleme : rebasculer l'origine en 'http-only' par la meme"
echo "methode. Le port 80 reste ouvert et sa regle intacte — le chemin d'avant"
echo "fonctionne toujours. Ne fermer le 80 qu'apres plusieurs jours en 443."
