# S2 — Fiabiliser le rate-limiting : actions INFRA restantes (à faire côté AWS)

Le lot **S2** de l'audit `SECURITY_AUDIT_2026-07-27.md` est en partie **bloqué par de
l'infra AWS** non gérée dans ce repo. Le code a été préparé pour être **activable sans
redéploiement applicatif** : les deux durcissements sont des **no-op tant que le secret /
l'URL correspondant n'est pas injecté** en prod. Cette checklist liste ce qu'il reste à
provisionner côté AWS pour les activer.

État du code (déjà livré, EN ATTENTE d'infra) :

| Finding | Code livré | S'active quand… |
|---------|-----------|-----------------|
| #5 Compteurs slowapi en mémoire, non partagés entre tâches ECS | `Limiter(storage_uri=settings.REDIS_URL or "memory://")` + champ `REDIS_URL` | `REDIS_URL` pointe vers un Redis/ElastiCache joignable |
| #4 Spoof X-Forwarded-For via accès direct à l'ALB | Garde `X-Origin-Verify` dans `_get_real_ip` + champ `ORIGIN_VERIFY_SECRET` | `ORIGIN_VERIFY_SECRET` est posé ET CloudFront injecte le header |
| #10 `TRUSTED_PROXY_COUNT` non versionné | **Versionné `=2` dans `deploy.yml`** (`$env_overrides`) | ✅ fait, aucune action infra |

> ⚠️ Tant que ces deux actions ne sont pas faites, la seule barrière des endpoints
> publics non-auth reste : (a) multipliable par le nombre de tâches ECS (compteurs
> in-memory), et (b) spoofable **si l'ALB est joignable en direct**. Le finding #4
> retombe à LOW dès que l'ALB est verrouillé derrière CloudFront (action B ci-dessous).

---

## ⚠️ Statut réel des deux actions (vérifié le 2026-07-30)

**Action A (Redis) — DIFFÉRÉE, ce n'est pas un trou aujourd'hui.** Le conteneur
tourne en `--workers 1` et le service ECS en `desiredCount: 1` : un seul
processus détient les compteurs, ils sont donc **de fait globaux**. Le finding #5
ne se matérialise qu'à partir de **2 tâches** (ou pendant les quelques secondes
d'un déploiement). C'est un prérequis pour scaler, pas une faille active.

> Coûts relevés via l'API AWS Pricing (EU Paris, `cache.t4g.micro`, aucun free
> tier sur ce compte) : **Redis 13,14 $/mois**, **Valkey 10,51 $/mois**. Prendre
> **Valkey** le jour où on provisionne : `limits` 5.8.0 supporte nativement les
> schémas `valkey://` / `valkeys://`, donc **zéro ligne de code à changer**.
>
> Alternative écartée : écrire un backend de stockage PostgreSQL pour `limits`
> (non supporté nativement). Ça mettrait une écriture par requête sur la base,
> sur les endpoints publics justement visés par un afflux — la protection
> deviendrait un amplificateur.

**Action B (verrou ALB) — À FAIRE, trou ouvert et correction gratuite.** L'ALB
`cybervault-alb` est `internet-facing` et répond en direct : `/health` renvoie
200 en HTTP comme en HTTPS, CloudFront contourné. Un attaquant peut donc forger
`X-Forwarded-For` et **changer sa clé de rate-limit à volonté**, ce qui annule la
protection par IP des endpoints publics non authentifiés. C'est l'action qui a le
meilleur rapport valeur/coût du lot : **0 €**.

---

## Action A — Compteurs de rate-limit partagés (ElastiCache) → active #5

Rend les limites (`public-scans 3/h`, `contact 3/h`, `url-scans 10/min`, `unlock 5/h`,
login) **globales à toutes les tâches ECS** au lieu d'être comptées par tâche.

1. **Provisionner ElastiCache Redis** (même VPC/subnets privés que ECS + RDS) :
   - Type minimal : `cache.t4g.micro` (coût récurrent ~12-15 $/mois, à assumer).
   - Chiffrement in-transit + at-rest activés.
   - Security group : autoriser le port 6379 **uniquement** depuis le SG des tâches ECS.
2. **Stocker l'URL dans Secrets Manager** (secret `cybervault/prod`) :
   - Clé `REDIS_URL` = `rediss://<endpoint>:6379/0` (noter `rediss://` = TLS).
3. **Injecter le secret dans la task def** : ajouter `"REDIS_URL"` à la liste
   `$secret_names` de [.github/workflows/deploy.yml](../.github/workflows/deploy.yml)
   (bloc jq du job deploy), puis redéployer. Le code bascule automatiquement de
   `memory://` vers Redis au démarrage.
4. **Vérifier** : après rollout, un même endpoint limité doit renvoyer 429 après le
   quota **quel que soit le nombre de tâches** (tester en scalant à 2 tâches).

> Bonus : APScheduler (scheduler) utilise déjà `os.getenv("REDIS_URL")` comme jobstore
> — poser `REDIS_URL` réglera aussi la duplication des jobs planifiés en multi-instance
> (cf. mémoire `project_optim_technique`).

---

## Action B — Verrouiller l'ALB derrière CloudFront (X-Origin-Verify) → active #4

Empêche un attaquant d'atteindre l'ALB en direct pour forger `X-Forwarded-For` et
contrôler la clé de rate-limit. Deux couches (poser au moins UNE, idéalement les deux) :

### B1. Header secret X-Origin-Verify (couche applicative, déjà codée)
1. Générer un secret aléatoire long (ex. `openssl rand -hex 32`).
2. **CloudFront** : ajouter un *Origin custom header* `X-Origin-Verify: <secret>` sur
   l'origine ALB (Origins → Edit → Add header).
3. **ALB** : créer une règle de listener HTTPS qui **rejette (403)** toute requête dont
   le header `X-Origin-Verify` ≠ `<secret>` (condition « HTTP header » sur la règle).
4. **Secrets Manager** : ajouter `ORIGIN_VERIFY_SECRET=<secret>` au secret
   `cybervault/prod`, puis l'ajouter à `$secret_names` dans `deploy.yml` et redéployer.
   → Le garde applicatif `_get_real_ip` cesse alors de faire confiance au XFF des
   requêtes sans header valide (défense en profondeur si la règle ALB est contournée).

### B2. Security group / prefix-list (couche réseau, recommandée en plus)
- Restreindre le SG de l'ALB en entrée (443) à la **managed prefix-list**
  `com.amazonaws.global.cloudfront.origin-facing` au lieu de `0.0.0.0/0`.
- Bénéfice : l'ALB n'est plus joignable que depuis les IP CloudFront, l'accès direct
  est coupé au niveau réseau (le plus robuste).

### Vérification #4
- `curl -H "X-Forwarded-For: 9.9.9.9" https://<ALB-DNS-direct>/api/v1/plans` → doit
  échouer (403 via B1, ou timeout/refus via B2), et NON servir la réponse.
- Le trafic normal via `https://rochercybersecurite.com/` reste 200.

---

## Rappels
- Ces deux actions touchent la **prod** : les faire hors pic, et vérifier le health
  check ECS + un `curl` racine après chaque changement.
- Ne **pas** ajouter `REDIS_URL` / `ORIGIN_VERIFY_SECRET` à `$secret_names` **avant**
  de les avoir créés dans Secrets Manager : une clé référencée mais absente fait
  échouer le démarrage de la task ECS.
