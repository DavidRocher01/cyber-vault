# Runbook de release — Bascule Zero-Knowledge + JSONB + reprice (juin 2026)

> Runbook **spécifique** à la mise en prod du gros lot `develop → master`
> (73 commits, 6 nouvelles migrations). Pour les commandes AWS génériques
> (snapshot, rollback ECS/RDS), voir [`DEPLOY.md`](DEPLOY.md). Pour la réponse
> à incident, voir [`RUNBOOK_INCIDENT.md`](RUNBOOK_INCIDENT.md).

## TL;DR — pourquoi ce déploiement est sensible

| Sujet | Risque | Statut / décision |
|-------|--------|-------------------|
| Bascule zero-knowledge (sel + colonnes chiffrées) | Coffres existants illisibles | ✅ **Sans objet** — pas de données vault réelles en prod (comptes de test only) |
| `reprice_plans_v2` efface `stripe_price_id` | Checkout cassé (400 propre) | ⚠️ **Bloquant** — créer les 3 prix Stripe + backfill avant de rouvrir le checkout |
| `JSON → JSONB` (ALTER TYPE) | Lock `ACCESS EXCLUSIVE`, réécriture table `scans` | 🟡 **Fenêtre de maintenance** + snapshot |
| Migration TOTP chiffré (`b7f3e1a9c2d4`) | Rotation `SECRET_KEY` casse la 2FA | 🟡 Ne **pas** rotater `SECRET_KEY` pendant ce déploiement |
| Double exécution migrations | Race si ≥2 tâches ECS | ✅ Corrigé : migration via tâche one-shot uniquement (cf. plus bas) |

## Les 6 nouvelles migrations (ordre d'application)

`alembic upgrade head` les applique dans cet ordre :

1. `6f5b7d420f72` — **reprice_plans_v2** : change les prix (14,90 / 49 / 149 €) et **vide `stripe_price_id`**. ⚠️ Voir § Stripe. <!-- prix-historique : grille de juin 2026, remplacée depuis -->
2. `b8c4d2e9f1a3` — **json → jsonb** : `ALTER COLUMN TYPE` sur `blog_posts.tags`, `scans.results_json`, `darkweb_dossiers.top_sources_json`, `rssi_clients.extra_data` + index GIN sur tags. 🟡 Lock + réécriture (cf. § Fenêtre).
3. `d7e2f3a4b5c6` — **crypto_salt** : ajoute la colonne, backfille un sel aléatoire par user, passe `NOT NULL`.
4. `e9f1a2b3c4d5` — **vault_encrypted_fields** : ajoute `title/username/url/notes_encrypted` (nullable, additif).
5. `0fda8d4857ac` — **title nullable** (zero-knowledge).
6. `b7f3e1a9c2d4` — **widen totp_secret** 64→255 (opération métadonnée, instantanée).

> Toutes additives/transformantes — **aucune perte de colonne**. La seule lourde
> en I/O est la (2). Vérifier **une seule tête** avant de partir :
> `alembic heads` doit retourner exactement 1 révision.

---

## Pré-requis (J-1)

- [x] **Prix Stripe** — plus rien à créer : les six prix LIVE existent
      (49 / 149 / 390 € par mois, 490 / 1 490 / 3 900 € par an), et les sept
      générations précédentes ont été archivées le 2026-08-02. Leurs
      identifiants sont versionnés dans `backend/app/core/pricing.py`, qui fait
      désormais foi — le seed les pose sur une base neuve, la migration
      `a5875bea88a0` sur une base existante.
  - Vérifié le 2026-08-02 : les sessions de paiement créées par la production
    depuis le 26 juillet portent bien les prix de juillet. L'affichage et le
    débit correspondent.

### Si un tarif change

1. Modifier `GRILLE` dans `backend/app/core/pricing.py`.
2. Créer les nouveaux prix chez Stripe (un montant est **immuable** : on ne
   modifie pas un prix, on en crée un autre), reporter les `price_...`.
3. Ajouter les anciens montants à `LIBELLES_RETIRES` — `check_prix_retires.py`
   fera alors échouer la CI tant qu'ils traînent dans une page publique.
4. Écrire une migration de données qui pose les nouveaux identifiants.
   `test_pricing_source_unique.py` échoue tant qu'elle manque.
5. Corriger les articles de blog concernés : ils vivent en base, aucun contrôle
   ne les voit (modèle : `f7fb572e4e16_blog_tarifs_grille_juillet_2026.py`).
6. Archiver les anciens prix chez Stripe. Si l'un est le prix par défaut de son
   produit, repointer d'abord ce défaut — Stripe refuse sinon.
7. Lancer `python scripts/verifier_prix_stripe.py` : il confronte les montants
   réellement servis par `/api/v1/plans` en production aux prix Stripe désignés
   par les `stripe_price_id`. Il lit la clé dans Secrets Manager lui-même.
   Le même contrôle tourne à chaque déploiement (travail « Coherence des prix
   Stripe »), mais le lancer ici évite de découvrir l'écart après coup.
   Il a remplacé `tests/test_stripe_price_coherence.py`, qui était
   `skipif(not STRIPE_SECRET_KEY)` — donc ignoré depuis toujours — et qui lisait
   la base de TEST plutôt que la production.

> Le filet en production : `stripe_service.verifier_prix` interroge Stripe avant
> chaque ouverture de session et **refuse de facturer** si le montant,
> l'intervalle, la devise, l'état d'archivage ou le `tax_behavior` ne
> correspondent pas. Une erreur de configuration devient une 503 visible, jamais
> un prélèvement au mauvais montant.
- [ ] **Vérifier AWS Secrets Manager** (`cybervault/prod`) contient bien :
  `SECRET_KEY`, `DATABASE_URL`, `STRIPE_SECRET_KEY` (sk_live), `STRIPE_WEBHOOK_SECRET` (whsec), `RESEND_API_KEY`, `SENTRY_DSN`, `SMTP_PASSWORD`.
- [ ] **Vérifier GitHub Secrets** : `AWS_DEPLOY_ROLE_ARN`, `AWS_SM_ARN`, `ECS_CLUSTER`, `ECS_SERVICE`, `S3_BUCKET_NAME`, `CLOUDFRONT_DISTRIBUTION_ID`, `STRIPE_PUBLISHABLE_KEY` (pk_live).
- [ ] **`TRUSTED_PROXY_COUNT=2`** dans l'environnement ECS (CloudFront + ALB = 2 hops ; défaut=1 → IP client faussée pour le rate-limit). Variable non-secrète, à mettre dans la task definition.
- [ ] **CI verte** sur `develop` (Backend/Frontend/E2E/Rapport).
- [ ] **NE PAS rotater `SECRET_KEY`** (clé de chiffrement TOTP en dérive — cf. `DEPLOY.md` § b7f3e1a9c2d4).
- [ ] Préparer le **bandeau de maintenance** (cf. § Maintenance) et l'horaire (heure creuse).

---

## Jour J — séquence de déploiement

### 1. Annonce & gel
- [ ] Activer le **bandeau de maintenance** (éditer `maintenance.json` dans S3 — voir § Maintenance, pas de rebuild).
- [ ] Annoncer la fenêtre (~30 min).

### 2. Sauvegarde

> ⚠️ **Exemption en cours (décision 2026-07-29)** : le snapshot est sauté tant
> qu'il n'y a **aucun client réel** en base — rien d'irremplaçable à perdre.
> **Dès le premier client signé, il redevient obligatoire.** Cf.
> [`DEPLOY.md`](DEPLOY.md) § Snapshot manuel pré-déploiement.

- [ ] **Snapshot RDS** (obligatoire avant migrations) :
  ```bash
  aws rds create-db-snapshot \
    --db-snapshot-identifier cyberscan-pre-zk-$(date +%Y%m%d-%H%M) \
    --db-instance-identifier cybervault-prod
  # attendre "available"
  aws rds wait db-snapshot-completed --db-snapshot-identifier <id-ci-dessus>
  ```

### 3. Merge & build
- [ ] Merger `develop → master` (déclenche `deploy.yml`).
- [ ] `deploy.yml` enchaîne : build image → push ECR → **tâche one-shot `alembic upgrade head`** → update service → build/sync front S3 + invalidation CloudFront.
- [ ] **Surveiller la tâche de migration** (la (2) JSONB peut durer selon le volume de `scans`) :
  ```bash
  aws ecs wait tasks-stopped --cluster cybervault-prod --tasks <task-arn>
  # exit code 0 attendu ; sinon → § Rollback
  ```

### 4. Stripe (post-migration, AVANT de rouvrir le checkout)
- [ ] **Backfiller les `stripe_price_id`** avec les nouveaux prix LIVE, via le script
  idempotent (hors chaîne Alembic — cf. dette #2), lancé en `aws ecs execute-command` :
  ```bash
  python scripts/set_stripe_price_ids.py \
    --starter  price_LIVE_starter \
    --pro      price_LIVE_pro \
    --business price_LIVE_business
  ```
  (Idempotent : relançable sans risque ; ne touche que les plans fournis.)
- [ ] **Vérifier le webhook Stripe** : endpoint `https://rochercybersecurite.com/api/v1/webhooks/stripe`, `STRIPE_WEBHOOK_SECRET` à jour côté Secrets Manager ET côté dashboard Stripe.

### 5. Vérifications post-déploiement
- [ ] Health : `curl https://rochercybersecurite.com/api/v1/health` → 200
- [ ] Révision Alembic : le même appel renvoie `db_revision` — vérifier qu'il vaut
      la tête attendue (plus fiable et plus rapide qu'un `alembic current` via exec ECS)
- [ ] Health profond : **non joignable publiquement** (monté sur `/health/deep` à la
      racine, et CloudFront ne route que `/api/*`) — cf. [`DEPLOY.md`](DEPLOY.md)
      § Vérification post-déploiement
- [ ] **Parcours nominal** : inscription → login → 2FA setup/verify → création entrée vault (chiffrée) → relecture → déconnexion.
- [ ] **Checkout** : tester un abonnement (sandbox carte test si dispo) → redirection Stripe OK.
- [ ] Front : page d'accueil + `/docs` (Swagger) chargent ; pas d'erreur console.
- [ ] Logs : `aws logs tail /ecs/cyberscan-backend --since 5m` — pas d'exception au boot.

### 6. Clôture
- [ ] **Désactiver le bandeau de maintenance** (`maintenance.json` → `active:false`).
- [ ] Annoncer la fin.
- [ ] Garder le snapshot RDS **7 jours minimum**.

---

## Rollback

> Décider vite : **avant** ou **après** que des écritures aient eu lieu sur le nouveau schéma.

### Si la migration échoue (tâche one-shot exit ≠ 0)
- Le service ECS tourne **encore sur l'ancienne image** (update-service ne s'est pas fait). Pas de downtime applicatif.
- Diagnostiquer les logs de la tâche, corriger la migration, re-push.

### Si le nouveau code est déployé mais KO
1. **Code** : revenir à la task definition précédente (cf. `DEPLOY.md` § Rollback ECS).
2. **DB** : la plupart des migrations sont additives (rollback code = sûr). ⚠️ **Exceptions** :
   - `b8c4d2e9f1a3` (JSONB) : `downgrade` re-convertit en TEXT (réécriture inverse, lock) — possible mais coûteux.
   - `b7f3e1a9c2d4` (totp) : **ne PAS `downgrade`** si des graines TOTP chiffrées (~140 car) existent déjà (rétrécir la colonne les tronquerait). L'ancien code lit le clair en fallback → redéployer l'ancien code suffit.
   - `6f5b7d420f72` (reprice) : `downgrade` restaure les anciens prix + anciens `stripe_price_id`.
3. **Dernier recours** : restaurer le snapshot RDS (cf. `DEPLOY.md` § Rollback DB, ~15-30 min).

---

## Maintenance (bandeau + page)

- **Bandeau d'annonce** (app debout) : composant `MaintenanceBannerComponent`
  (`frontend/src/app/shared/maintenance-banner/`), branché dans le shell `AppComponent`,
  piloté **au runtime** par `frontend/src/assets/maintenance.json` (servi en S3 sous
  `assets/maintenance.json`). Pour l'activer/désactiver **sans rebuild**, éditer le JSON
  dans le bucket S3 puis invalider sur CloudFront :
  ```bash
  aws s3 cp maintenance.json s3://<bucket>/assets/maintenance.json --cache-control "no-cache"
  aws cloudfront create-invalidation --distribution-id <id> --paths "/assets/maintenance.json"
  ```
  Schéma : `{ "active": true, "level": "warning|critical|info", "message": "...", "until": "2026-06-XXTXX:XXZ" }`.
  (Dismissible côté user ; un nouveau `message` ré-affiche le bandeau.)
- **Page de coupure** (app indisponible) : `frontend/src/assets/maintenance.html` autonome
  (sans JS ni back-end), servie sous `assets/maintenance.html` — à brancher en custom error
  page CloudFront pendant la coupure réelle si besoin.

---

## Notes mécaniques

- **Migrations = tâche one-shot uniquement.** Le `CMD` du conteneur ne lance plus `alembic upgrade head` au démarrage (évite la race si ECS scale >1 tâche). La migration est jouée par la tâche dédiée de `deploy.yml` (prod).
- **Cible = AWS uniquement** (ECS Fargate cluster `cybervault-prod` + RDS + S3/CloudFront, `eu-west-3`). Le `render.yaml` et le staging Oracle ont été **supprimés** (juin 2026) — pas de staging actif.
