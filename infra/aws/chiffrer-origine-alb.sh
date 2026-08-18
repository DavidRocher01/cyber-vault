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
#
#   3. LE PIEGE QUI AURAIT COUPE LE SITE. En `https-only`, CloudFront valide le
#      certificat de l'origine contre le NOM D'ORIGINE qu'il a en configuration.
#      Le certificat de l'ecouteur 443 couvre `api.cyberscanapp.com` et rien
#      d'autre ; l'origine etait declaree sous
#      `cybervault-alb-1319154203.eu-west-3.elb.amazonaws.com`. Basculer sans
#      renommer = 502 sur tout le site. Et aucune AC publique ne delivre de
#      certificat pour un nom `amazonaws.com` : renommer l'origine est la SEULE
#      voie. `api.cyberscanapp.com` est deja un alias Route53 vers ce meme ALB.
#      L'etape 3 fait donc les deux d'un coup — renommer et chiffrer.
#      Le renommage ne touche pas l'`Id` de l'origine, auquel se rattachent les
#      comportements de cache : ils suivent sans modification.
# ---------------------------------------------------------------------------

set -euo pipefail

DISTRIBUTION="E3DFNMKIHVBDO1"
GROUPE_ALB="sg-040da241f674d9b8c"        # porte le 80 depuis CloudFront
GROUPE_HTTPS="sg-032a3ebe1d53d63a8"      # porte le 443 depuis CloudFront
ORIGINE_HTTPS="api.cyberscanapp.com"     # cf. piege 3 : le certificat du 443
TRAVAIL="$(mktemp -d)"
# Sous Git Bash, `mktemp` renvoie un chemin POSIX (/tmp/...) que le python et
# l'aws de Windows lisent comme C:\tmp\... — donc pas du tout. Les redirections
# du shell utilisent $TRAVAIL ; tout ce qui est PASSE a un binaire Windows
# utilise $TRAVAIL_NATIF. `cygpath -m` donne la forme C:/... , acceptee aussi
# bien par python que par le prefixe file:// de l'AWS CLI.
if command -v cygpath >/dev/null 2>&1; then
  TRAVAIL_NATIF="$(cygpath -m "$TRAVAIL")"
else
  TRAVAIL_NATIF="$TRAVAIL"
fi

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
# Le NOM de l'origine change aussi, et ce n'est pas cosmetique : cf. piege 3.
aws cloudfront get-distribution-config --id "$DISTRIBUTION" > "$TRAVAIL/dist.json"
ETAG=$(python -c "import json;print(json.load(open(r'$TRAVAIL_NATIF/dist.json'))['ETag'])")

set +e
python - "$TRAVAIL_NATIF" "$ORIGINE_HTTPS" <<'PY'
import json, sys, pathlib
t, nom = pathlib.Path(sys.argv[1]), sys.argv[2]
d = json.loads((t / "dist.json").read_text(encoding="utf-8"))
cfg = d["DistributionConfig"]

# On vise l'unique origine personnalisee : le seau S3 n'en a pas. Viser par
# `"alb" in Id` marchait tant que l'Id contenait le nom d'hote de l'ALB — ce
# qui n'est vrai que par accident, et l'Id ne change pas quand le nom change.
personnalisees = [o for o in cfg["Origins"]["Items"] if o.get("CustomOriginConfig")]
if len(personnalisees) != 1:
    raise SystemExit(f"ARRET : {len(personnalisees)} origine(s) personnalisee(s), 1 attendue")

o = personnalisees[0]
custom = o["CustomOriginConfig"]
avant = (o["DomainName"], custom["OriginProtocolPolicy"],
         tuple(custom.get("OriginSslProtocols", {}).get("Items", [])))

o["DomainName"] = nom
custom["OriginProtocolPolicy"] = "https-only"
# L'ecouteur applique ELBSecurityPolicy-TLS13-1-2-Res-PQ-2025-09 : offrir SSLv3
# ou TLSv1 ne sert qu'a se les faire refuser. On n'offre que ce qui aboutit.
custom["OriginSslProtocols"] = {"Quantity": 1, "Items": ["TLSv1.2"]}

apres = (o["DomainName"], custom["OriginProtocolPolicy"],
         tuple(custom["OriginSslProtocols"]["Items"]))
if avant == apres:
    print("   deja conforme — rien a faire")
    sys.exit(3)

print(f"   nom       : {avant[0]}")
print(f"           -> {apres[0]}")
print(f"   protocole : {avant[1]} -> {apres[1]}")
print(f"   TLS       : {list(avant[2])} -> {list(apres[2])}")
(t / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
PY
CODE=$?
set -e

if [ "$CODE" -eq 0 ]; then
  aws cloudfront update-distribution --id "$DISTRIBUTION" \
    --distribution-config "file://$TRAVAIL_NATIF/config.json" --if-match "$ETAG" \
    --query 'Distribution.Status' --output text
elif [ "$CODE" -ne 3 ]; then
  exit "$CODE"
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
