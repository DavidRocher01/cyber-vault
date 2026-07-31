# S2 — Fiabiliser le rate-limiting : actions INFRA

> **État au 2026-07-31 : action B terminée (B1 + B2).** Seule l'action A
> (ElastiCache) reste, volontairement différée — ce n'est pas un trou tant que
> le service tourne à une tâche et un worker.

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

**Action B (verrou ALB) — ✅ FAITE le 2026-07-31 via B2.** Le trou est ferme.

Etat constate avant correction : le SG `sg-040da241f674d9b8c` de `cybervault-alb`
autorisait `0.0.0.0/0` sur 80 ET 443. Verifie par `curl` : `/api/v1/health`
repondait 200 en direct sur les deux ports, avec `X-Forwarded-For: 9.9.9.9`
accepte. Un attaquant controlait donc sa cle de rate-limit.

Etat final :

| Port | Regle entrante | Pourquoi |
|------|----------------|----------|
| 80 | prefix-list `pl-75b1541c` (`com.amazonaws.global.cloudfront.origin-facing`) | CloudFront attaque l'origine en **http-only:80** — c'est le seul chemin legitime |
| 443 | **aucune** | N'etait utilise que par l'acces direct (`api.cyberscanapp.com`). CloudFront ne s'en sert pas. |

> ⚠️ Si l'origine CloudFront passe un jour en `https-only`, il faudra **rouvrir le
> 443 sur la prefix-list**. Attention : une regle prefix-list consomme autant de
> slots que la liste a d'entrees, pas 1. Poser les deux ports d'un coup depasse la
> limite de 60 regles par SG (`RulesPerSecurityGroupLimitExceeded`) — il faudra
> demander un relevement de quota ou scinder les SG.

**Effets de bord assumes :**
- `api.cyberscanapp.com` (alias DNS vers l'ALB, herite de l'ancienne archi) ne
  repond plus. Il n'etait reference nulle part dans le code : le frontend appelle
  `/api/v1` en relatif, donc via CloudFront.
- `/health/deep` n'est plus joignable du tout depuis Internet (il l'etait
  uniquement en direct sur l'ALB). Passer par `aws ecs execute-command`.
- `RECETTE_BASE_URL` a ete bascule sur `https://rochercybersecurite.com` le
  2026-07-31 **avant** la fermeture, sa valeur precedente etant inconnue. Les 25
  chemins `/api/*` de la recette ont ete verifies un a un a travers CloudFront.

**B1 (header `X-Origin-Verify`) — ✅ FAITE le 2026-07-31 elle aussi.**

Pourquoi elle restait utile malgre B2 : n'importe qui peut creer SA PROPRE
distribution CloudFront pointant sur notre ALB. Ses requetes arriveraient
alors depuis des IP CloudFront legitimes et franchiraient la prefix-list. Seul
un secret partage distingue notre distribution des autres.

Ce qui a ete pose, dans cet ordre (l'ordre importe : exiger l'en-tete avant que
CloudFront ne l'envoie coupe tout le site) :

1. Secret de 64 caracteres hex ajoute comme **10e cle de `cybervault/prod`**,
   les 9 autres preservees. Pas de nouveau secret cree — la facturation
   Secrets Manager est par secret, pas par cle.
2. **CloudFront** : header d'origine `X-Origin-Verify` sur la SEULE origine
   ALB (l'origine S3 n'en a que faire). Attendu `Status: Deployed` avant la
   suite.
3. **ALB, listener :80** (celui que CloudFront utilise — l'origine est en
   http-only) : regle de priorite 1 qui forwarde si l'en-tete vaut le secret,
   puis action par defaut basculee en **fixed-response 403**.
4. `ORIGIN_VERIFY_SECRET` ajoute a `$secret_names` dans `deploy.yml`.

**Preuve que le verrou fonctionne** : avec l'action par defaut a 403, le site
et `/api/v1/health` repondent toujours 200 a travers CloudFront. Seule une
requete portant le bon en-tete est forwardee — c'est donc bien la regle qui
matche, pas le defaut.

> Pour retirer le verrou en urgence : remettre l'action par defaut du listener
> :80 sur `Type=forward,TargetGroupArn=<tg>`. Effet immediat, aucun
> redeploiement.

Le garde applicatif `_get_real_ip` s'active au prochain deploiement, quand la
task ECS recevra `ORIGIN_VERIFY_SECRET` : une requete sans en-tete valide verra
son `X-Forwarded-For` ignore au profit de l'IP TCP.

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

### Ce qui dépend de l'accès direct à l'ALB (vérifié le 2026-07-31, AVANT de poser B2)

Couper l'ALB casse tout ce qui ne passe pas par CloudFront. Inventaire :

- **La recette post-prod ne casse pas.** `backend/recette/conftest.py` prend
  `https://rochercybersecurite.com` par défaut et n'interroge que `/api/v1/health`,
  route servie par CloudFront. ⚠️ Non vérifiable depuis le repo : la valeur réelle
  du secret `RECETTE_BASE_URL`, qui peut surcharger ce défaut. **Le lire avant de
  poser B2** — s'il pointe sur le DNS de l'ALB, la recette échouera à chaque
  déploiement et déclenchera un rollback automatique.
- **Le health check approfondi casse.** `/health/deep` est monté à la racine de
  l'app et CloudFront ne route que `/api/*` : il n'est joignable qu'en direct sur
  l'ALB (cf. [DEPLOY.md](DEPLOY.md)). Après B2, il faudra passer par une task ECS
  (`aws ecs execute-command`). C'est un outil de diagnostic manuel, pas une
  dépendance du pipeline — coût opérationnel acceptable, mais à savoir avant de
  chercher pourquoi la commande du runbook ne répond plus.
- **Le health check de la target group ALB ne casse pas** : il vient de l'intérieur
  du VPC, pas d'Internet.

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
