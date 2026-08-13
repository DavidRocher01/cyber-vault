# Configuration AWS — ce qui a été durci, et pourquoi

Comme `infra/iam/`, ces fichiers **décrivent** le réel sans l'appliquer. Ils
existent pour être relus et comparés.

## Réseau

**L'ALB n'accepte que CloudFront.** Son groupe de sécurité n'autorise le port 80
que depuis la liste de préfixes gérée `pl-75b1541c` (adresses CloudFront). Il
n'est pas joignable depuis Internet — vérifié.

**La base a son propre groupe** (`cybervault-rds`, `sg-0885f71624e47b738`) depuis
le 2026-08-11. Elle portait auparavant le groupe `default` du VPC, dont une
règle autorise **tous protocoles depuis lui-même** : toute ressource créée sans
groupe explicite — comportement par défaut d'AWS — obtenait un accès réseau
illimité à la production. Le nouveau groupe n'autorise que 5432 depuis les
tâches ECS.

Vérifié après bascule : `database: ok` et lecture réelle des plans.

**`DeletionProtection` est activée** depuis le 2026-08-13. Elle ne l'était pas :
une seule commande `delete-db-instance` — accidentelle, ou lancée avec des
identifiants compromis — détruisait la production. Sept jours de sauvegardes
permettent de restaurer, mais mieux vaut ne pas avoir à le faire.

## Seau du frontend

`cyberscanapp-frontend` était **lisible publiquement** (`Allow * s3:GetObject`)
et répondait en direct hors CloudFront. Deux conséquences : les en-têtes de
sécurité — CSP, HSTS, `X-Frame-Options` — sont posés par CloudFront et non par
S3, donc une page chargée depuis l'URL S3 n'en avait aucun ; et le site formait
une copie indexable sur un second nom d'hôte.

L'accès passe désormais par une **Origin Access Control** (`E1P0TQ4A6T9KDH`) :
CloudFront signe ses requêtes, la politique du seau n'autorise que cette
distribution, et le blocage d'accès public est actif.

**Découvert au passage :** l'origine était déclarée en origine *personnalisée*
avec `OriginProtocolPolicy: http-only` — CloudFront allait chercher le frontend
**en clair**. La conversion en origine S3 corrige ce point par la même
opération.

Ordre suivi, et il compte : accorder à CloudFront **avant** de retirer le
public. L'inverse coupe le site.

## Vérifier

```bash
aws s3api get-bucket-policy --bucket cyberscanapp-frontend --query Policy --output text
aws rds describe-db-instances --db-instance-identifier cybervault-prod \
  --query 'DBInstances[0].VpcSecurityGroups[]'
curl -s -o /dev/null -w "%{http_code}\n" https://cyberscanapp-frontend.s3.eu-west-3.amazonaws.com/index.html  # doit repondre 403
```
