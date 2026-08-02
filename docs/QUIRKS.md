# Bizarreries connues du codebase Rocher Cybersécurité

Ce document recense les patterns surprenants ou non-évidents du code.
À lire avant de toucher les modules concernés.

---

## Backend

### Le moteur phishing est du code maison

Une intégration GoPhish a été abandonnée mi-2026. Le moteur actuel est interne :
`phishing_service.py` pour la logique, et le package `phishing_templates/`
(`engine.py`, `emails.py`, `landings.py`) pour les gabarits.

Les colonnes `gophish_*` de `phishing_campaigns` ont été retirées des modèles.

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
Garde ajoutée : si `FRONTEND_URL` contient `rochercybersecurite.com`, le démarrage crashe.
Ne jamais déployer avec `APP_ENV=development` en prod.

### Les tarifs ont trois points d'entrée, une seule vérité

`app/core/pricing.py` fait foi. Trois mécanismes y lisent la même grille, et
aucun ne porte de copie :

- `main.py::_seed_plans()` — insère les plans **absents** au démarrage, ne
  touche jamais une ligne existante ;
- `seed_plans.py` — script de rattrapage qui, lui, **réaligne** les plans
  existants sur la grille ;
- la migration `a5875bea88a0` — pose les `stripe_price_id` sur les bases en
  service.

Pour changer un tarif, suivre la procédure de `docs/RELEASE_RUNBOOK.md` :
modifier la grille, créer les prix chez Stripe, écrire une migration.
`test_pricing_source_unique.py` échoue tant que la migration manque.

### Aucun service n'est exclu de la mesure de couverture

Cinq l'étaient jusqu'au 2026-07-30, sur la présomption qu'ils n'étaient pas
testés. Mesure faite, quatre l'étaient déjà — ils étaient invisibles, pas à
découvert. Le cinquième, `newsletter_email`, était le seul vrai angle mort, et
c'est justement l'exclusion qui l'empêchait de se voir. `.coveragerc` documente
chaque exclusion restante et sa raison ; il n'en reste que des non-applicatives
(migrations, configuration de connexion).

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


## CVE pip-audit (CI) — historique (résolu 2026-06-28)

`pip-audit` (`.github/workflows/ci.yml`) tourne désormais **sans aucun `--ignore-vuln`** — objectif zéro CVE atteint. Les 9 CVE auparavant ignorées ont été corrigées :

- **starlette** (`PYSEC-2026-161`, `CVE-2025-62727`, `PYSEC-2026-248`, `PYSEC-2026-249`, `CVE-2026-48817`, `CVE-2026-48818`, `GHSA-f96h-pmfr-66vw`, `GHSA-2c2j-9gv5-cj73`) — **corrigé** par le bump `fastapi 0.115.14 → 0.138.1` + `starlette → 1.3.1`.
- **pyasn1** (`GHSA-jr27-m4p2-rc6r`) — **corrigé** par la migration `python-jose → PyJWT 2.13.0` (la chaîne pyasn1 vulnérable disparaît).
- **python-multipart** — corrigé par le bump `0.0.27 → 0.0.31`.

## Gestion des CVE — politique

**Règle : on ne masque jamais une CVE en silence.** On corrige (bump vers la version patchée). Si aucun correctif n'existe, on ignore **temporairement, daté, avec lien advisory + ticket de suivi** — jamais un `--ignore-vuln` nu.

**Garde-fous en place :**

- **Backend** : `pip-audit` per-push **sans aucun `--ignore-vuln`** → toute CVE casse le build.
- **Frontend** : `npm audit --audit-level=high --omit=dev` per-push → toute CVE high/critical en dépendance **prod** casse le build.
- **Dependabot** : PRs de bump auto pour `pip` (/backend), `npm` (/frontend), `github-actions` + security updates activés.
- **Audit hebdo** (`security-weekly.yml`) : digest pip-audit + bandit + npm audit (toutes sévérités, dev inclus).

**CVE npm dev-only connues (hors gate prod, non livrées au client) :**

- `http-proxy-middleware` (via `@angular-devkit/build-angular`) — `GHSA-64mm-vxmg-q3vj` (host-header routing bypass). Outil de **build/dev local uniquement**, non exposé en prod. Le correctif force un downgrade cassant de `@angular-devkit/build-angular` → laissé jusqu'à un devkit patché compatible, suivi via le digest hebdo.
