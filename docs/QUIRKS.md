# Bizarreries connues du codebase CyberScan

Ce document recense les patterns surprenants ou non-évidents du code.
À lire avant de toucher les modules concernés.

---

## Backend

### Colonnes `gophish_*` mortes dans `phishing_campaigns`

Les colonnes `gophish_campaign_id`, `gophish_group_id`, `gophish_template_id`, `gophish_page_id`
sont les vestiges d'une intégration GoPhish abandonnée mi-2026.
Le moteur phishing utilise désormais du code maison (`phishing_service.py` + `phishing_templates.py`).
Ces colonnes sont à supprimer dans un futur refacto (migration Alembic nécessaire).

### `max_sites` utilisé comme quota de scans

Dans `scans.py`, `plan.max_sites` est utilisé comme quota de scans dans une fenêtre temporelle,
pas seulement comme limite du nombre de sites enregistrés. Double sémantique à découpler
(refacto prévu dans le plan pricing).

### `sys.path` manipulé au niveau module

`backend/app/services/scan_service.py` insère `cyber-scanner/` dans `sys.path` au niveau
du module (import-time). Dépendance physique au filesystem relatif.
À packager proprement (editable install ou sous-paquet).

### Auto-import awareness au boot (désactivé)

`main.py` contenait un import automatique du contenu NIS2 YAML à chaque démarrage.
Désactivé mi-2026 (trop lent, fragile en prod si le path change).
Pour synchroniser le contenu : `POST /api/v1/admin/awareness/sync-content` (auth admin requise)
ou `python scripts/import_awareness_content.py`.

### DEV_MODE dans subscriptions.py

Si `APP_ENV=development`, les checkouts Stripe sont simulés sans vrai paiement.
Garde ajoutée : si `FRONTEND_URL` contient `cyberscanapp.com`, le démarrage crashe.
Ne jamais déployer avec `APP_ENV=development` en prod.

### _seed_plans dans main.py ET dans seed_plans.py

Deux sources de vérité pour les plans initiaux :
- `main.py::_seed_plans()` : crée les plans au boot si absents (n'écrase pas les Stripe IDs)
- `backend/seed_plans.py` : script standalone pour réinitialiser les plans complets

Si tu mets à jour les prix, modifier les deux + créer une migration Alembic.

### Migration fantôme `5e6403bce97c_add_vault_items.py`

Cette migration a `upgrade = pass`. Elle existait pour forcer une tête Alembic unique
après une fusion de branches. Inoffensive, ne pas supprimer (casserait la chaîne).

### `phishing_service.py` splitté en deux

Avant mai 2026, `phishing_service.py` contenait ~1 550 lignes (logique + templates HTML).
Splitté en :
- `phishing_service.py` : logique métier (envoi, tracking, campagnes)
- `phishing_templates.py` : templates HTML (950 lignes)

Les deux sont dans l'omit coverage (`.coveragerc`) car non testables unitairement sans fixtures lourdes.

---

## Frontend

### Tokens

L'`access_token` est en `sessionStorage` ; le `refresh_token` est en **cookie
httpOnly** (rotation + révocation en DB) — non accessible au JavaScript.
Migration vers httpOnly réalisée (l'ancienne note « refresh_token en
localStorage » est obsolète).

### Route admin obfusquée

`admin/ba61c5a60113/agenda` — security through obscurity.
Le UUID est visible dans le bundle JS minifié. À remplacer par une vraie
route protégée `admin/bookings` + guard Angular + `require_admin` backend.

### `CommonModule` importé sans usage dans plusieurs composants

La majorité des composants standalone importent `CommonModule` alors qu'ils utilisent
le control flow Angular (`@if`/`@for`). Le tree-shaking nettoie, mais c'est du bruit.
Nettoyage prévu lors d'un refacto frontend.

### Polling phishing page détail

`phishing-campaign-detail.component.ts` poll toutes les 5s pendant qu'une campagne
est active. Le polling s'arrête si le composant est détruit (takeUntilDestroyed).
Pas de WebSocket pour l'instant.

---

## Infrastructure

### Scheduler APScheduler intra-process

Les jobs de monitoring (SSL expiration, at-risk learners, phishing) tournent dans
le même process FastAPI via APScheduler. Si l'instance crashe, les jobs sont perdus
jusqu'au redémarrage. Acceptable avec une seule instance ECS.
Si tu scales > 1 instance : migrer vers Redis jobstore ou Arq.

### Backup DB local Windows inutilisable en prod

`scripts/backup_db.py` contient un chemin `C:\Program Files\PostgreSQL\...`.
En prod ECS Fargate, il n'y a pas de filesystem persistant.
Utiliser les RDS Automated Backups (rétention à configurer) + snapshots manuels.

### Quota GitHub Actions 2000 min/mois

Pipeline CI optimisé en mai 2026 (fusion job coverage + concurrency).
Coût estimé : ~20 min/push. Budget : ~100 pushs/mois avant quota.
Reset le 1er du mois. Surveiller via la routine quotidienne `CI Quota Monitor`.


## CVE ignorées dans pip-audit (CI) — à revoir

`pip-audit` (`.github/workflows/ci.yml`) ignore certaines vulnérabilités sans correctif applicable en l'état :

- **starlette 0.46.2** — `PYSEC-2026-248`, `PYSEC-2026-249`, `CVE-2026-48817`, `CVE-2026-48818`.
  Correctifs disponibles uniquement en **starlette 1.x**, **incompatible avec FastAPI 0.115**
  (qui exige `starlette < 0.47`). À lever lors d'un futur **upgrade FastAPI** (FastAPI ≥ version
  supportant starlette 1.x). Exposition jugée faible (app derrière CloudFront + usage standard).
- python-multipart : **corrigé** par le bump `0.0.27 → 0.0.31` (plus ignoré).
