# Recette post-mise-en-production

Une **recette** fonctionnelle joue de vrais parcours contre la **prod** après
chaque déploiement — pas de simples `curl` de liveness. Si elle échoue, le
backend est **rollback automatiquement** vers la révision précédente.

## Ce qu'elle couvre

Deux couches complémentaires, toutes deux contre le site déployé :

### 1. Socle API — `backend/recette/` (pytest + httpx, boîte noire)

| Fichier | Vérifie |
|---|---|
| `test_01_infra.py` | `GET /api/v1/health` : app vivante, DB joignable, **révision Alembic appliquée** présente (le migrate step a bien tourné) |
| `test_02_auth.py` | login, `/users/me`, refresh (cookie httpOnly), logout+révocation, et **bad creds → 401** (jamais 500 = régression PyJWT) |
| `test_03_read_paths.py` | chemins publics : `/plans`, `/blog/articles` |
| `test_04_vault_cycle.py` | cycle d'écriture **create → list → get → delete → absent** sur le coffre |
| `test_05_scan_cycle.py` | lance un url-scan sur notre propre domaine, vérifie que le **worker asynchrone vit** (le scan quitte `pending`), puis nettoie |

### 2. Parcours UI — `frontend/e2e/recette/` (Playwright, navigateur réel)

Détecte ce que l'API ne voit pas (bundle JS cassé, routing SPA HS, mauvaise base
URL d'API côté front) : la vitrine se charge et Angular rend, puis **connexion
canari via l'UI** → espace authentifié.

Config dédiée `frontend/playwright.recette.config.ts` (pas de `webServer`, pointe
`RECETTE_BASE_URL`). La suite E2E locale l'ignore (`testIgnore: **/recette/**`).

## Compte canari

Un compte **dédié** `recette@rochercybersecurite.com` (jamais un vrai compte
client). Business tier, expiration ~2126 (pas de plan-gating). Les identifiants
vivent dans **AWS Secrets Manager** (`cybervault/recette-canary`) et en **GitHub
secrets** (`RECETTE_EMAIL`, `RECETTE_PASSWORD`, `RECETTE_BASE_URL`).

> La recette **fait table rase** du coffre et des url-scans du canari au début et
> à la fin de chaque passage (`_wipe_canary`) : aucun résidu ne s'accumule, même
> si un run précédent a crashé. Ne jamais mettre de vraie donnée sur ce compte.

Recréer / réinitialiser le mot de passe du canari :

```bash
# via une task ECS one-off qui lance scripts/create_admin.py (idempotent)
# le mot de passe transite par une variable, jamais en clair dans un log
```

## Déclenchement & rollback (`.github/workflows/deploy.yml`)

Job `recette`, `needs: [deploy-backend, deploy-frontend]` → tourne une fois le
service ECS **stable sur la nouvelle révision**. En cas d'échec :

```
recette KO  ->  aws ecs update-service --task-definition <prev_task_def>
            ->  wait services-stable  ->  run rouge + alerte
```

`prev_task_def` est la révision **en service avant** ce déploiement, exposée en
output du job `deploy-backend`.

### ⚠️ Contrainte : migrations rétro-compatibles

Le rollback ne concerne **que le backend (task def ECS)**. Il ne **rejoue pas les
migrations à l'envers** (aucun `downgrade` n'est exécuté en prod). Donc :

- **L'image précédente doit pouvoir tourner contre le schéma déjà migré.**
  Suivre le patron *expand / contract* : ajouter (colonne nullable, nouvel index)
  dans un déploiement, puis retirer/durcir dans un **déploiement ultérieur**,
  jamais un changement destructif-immédiat qui casserait l'ancienne image.
- Le **frontend** (S3/CloudFront) n'est **pas** rollback automatiquement (le sync
  a déjà remplacé les assets). En cas d'échec purement front : corriger et
  redéployer.

## Lancer en local

```bash
make recette                      # API + UI contre la prod (creds depuis Secrets Manager)
RECETTE_BASE_URL=http://localhost:8000 make recette   # contre une instance locale
```

Ou directement :

```bash
cd backend && RECETTE_EMAIL=... RECETTE_PASSWORD=... \
  python -m pytest recette/ -c recette/pytest.ini -v
```

Sans `RECETTE_EMAIL`/`RECETTE_PASSWORD`, les tests d'écriture sont **skip** (un run
lecture-seule reste possible).

## Ajouter un test

- **API** : nouveau `backend/recette/test_*.py`. Utiliser la fixture `canary`
  (client httpx authentifié) et **toujours nettoyer** ce qu'on crée (`finally` +
  le wipe de session en filet de sécurité). Décorer les tests d'écriture avec
  `@requires_canary`.
- **UI** : ajouter au `frontend/e2e/recette/`. Rester **robuste** (un échec =
  rollback) : vérifier que ça rend / que l'auth aboutit, pas des détails fragiles.
