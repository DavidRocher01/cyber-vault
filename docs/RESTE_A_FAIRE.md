# Reste à faire — Cyber-Vault

> Audit du 2026-06-07. Ce document corrige un audit multi-agents initial qui
> comportait beaucoup de **faux positifs** : la plupart des points « bloquants »
> étaient en réalité déjà traités. Statut vérifié manuellement ci-dessous.

---

## ✅ Déjà fait / non-problèmes (vérifié — ne pas re-traiter)

- **Vault zero-knowledge** : le client n'envoie que les blobs `*_encrypted`, le
  backend ne stocke plus de clair (title nullable + migration `0fda8d4857ac`),
  test sentinel garde-fou. Migration legacy efface le clair existant au 1er login.
- **Refresh token** : déjà en cookie httpOnly (rotation + révocation), pas en JSON.
- **Rate-limit** : login (10/min) + register (5/min) déjà en place ; forgot/reset
  ajoutés (5/min). NB : le loopback est bypassé par design (cf. `core/limiter.py`).
- **Intercepteur HTTP retry** : déjà GET-only (pas de retry sur POST/PATCH).
- **SSR / prerendering** : fonctionne (le build frontend en CI le prouve). Les 3
  « crashs SSR » signalés étaient des handlers déclenchés uniquement côté
  navigateur. `clipboard.service` durci par cohérence.
- **CI déjà mature** : ruff + mypy + bandit + pip-audit + alembic check + pytest
  `--cov-fail-under=81` (backend) ; ESLint + Vitest + build AOT (frontend) ; E2E
  Playwright. Lint ET typecheck frontend SONT présents (via ESLint + build).
- **Colonnes mortes `gophish_*`** : déjà supprimées des modèles.
- **Outils sécu** (bandit/semgrep/checkov) : déjà hors de `requirements.prod.txt`.
- **Deps prod manquantes** (email-validator, httpx, dnspython, boto3) : ajoutées.
- **Divergence FastAPI dev/prod** : alignée (dev 0.111→0.115.14 = prod).
- **`extra='forbid'`** : ajouté aux schémas d'entrée publics (auth, contact,
  newsletter subscribe, public-scan, api-waitlist).
- **Webhook `/internal/phishing-click`** : protégé par `require_admin`.

---

## 🟠 Reste réel — bounded (faisable en code, à planifier)

### Backend
- **`extra='forbid'` sur les schémas d'entrée authentifiés** (vault, rssi,
  darkweb, awareness, 2FA, notif prefs) — étendre la règle au-delà du public.
  *Risque : vérifier chaque payload frontend avant, pour éviter les 422.*
- **`except Exception` silencieux (~20 fichiers)** : remplacer par exceptions
  ciblées + `logger.exception()` + capture Sentry sur les chemins critiques
  (upload S3 certificats, envoi emails batch phishing, scheduler).
- **TTL des tokens newsletter** : `confirmation_token`/`unsubscribe_token` sans
  expiration → ajouter `token_created_at` + check TTL (faible sévérité, opt-in).
- **Timeout DNS** sur la vérification de domaine phishing (`socket.getaddrinfo`).
- **Couverture réelle** : plusieurs gros services exclus du calcul via
  `.coveragerc` (`phishing_service`, `phishing_templates`, `scan_service`,
  `public_scan_service`) → écrire des tests puis les réintégrer au coverage.
- **Incohérence doc** : CLAUDE.md mentionne 84 % de couverture, le seuil réel
  est 81 % (`pytest.ini`). Aligner l'un sur l'autre.

### Frontend
- **Accessibilité (a11y)** : quasi aucun `aria-*`/`role`/`alt` dans `features/`.
  Chantier transverse (WCAG) — à faire page par page.
- **`app-nav-buttons` manquant** sur certaines pages publiques (nis2, iso27001,
  ressources, bonnes-pratiques…) — règle projet non respectée partout.
- **Tests unitaires manquants** : ~17 composants `cyberscan` sans `.spec.ts`
  (dont `admin-shell`, `newsletter-admin`).
- **2 tests E2E skippés** (PDF phishing, upgrade pricing) — à activer quand les
  features sous-jacentes sont stables.

### Dette / refacto (gros, à cadrer — ne pas faire à l'aveugle)
- Monolithes : `phishing_templates.py` (~950 l), `scheduler.py`, composants
  `dashboard`/`client-detail`/`awareness-module`.
- 6 services PDF quasi-dupliqués → extraire un `BasePdfBuilder`.
- Imports lazy ↔ cycles (darkweb↔email, scan↔email, rssi↔rssi_pdf) → module
  `notifications/` événementiel.
- `cyber-scanner` chargé via `sys.path.insert` → packager proprement.

---

## 🔴 Nécessite TON intervention (hors code / décisions)

### Infra / Ops (accès AWS/Oracle requis)
- **Staging Oracle** : provisionner l'instance (scripts `staging/` prêts), DNS
  `staging.rochercybersecurite.com`, hash bcrypt Caddy, secrets staging.
- **Secrets à configurer** : `S3_BUCKET_NAME` + `AWS_REGION` (livrables RSSI),
  domaine email ImprovMX (MX + Secrets Manager), vérifier OIDC GitHub→AWS.
- **Sécurité ops à vérifier/activer** : WAF CloudFront, chiffrement RDS at-rest,
  redirection HTTP→HTTPS ALB, rétention backups ≥ 30 j, rotation secrets.
- **Observabilité** : alertes CloudWatch (CPU/mém/connexions), règles
  d'escalade Sentry, (option) table `audit_logs`.
- **Déploiement** : health-check post-deploy (`ecs wait services-stable`),
  script de rollback, SBOM (utile NIS2).

### Décisions produit (à valider par l'usage client réel)
- Module **awareness/sensibilisation NIS2** : central ou optionnel ?
- **cyber-scanner** : intégré au produit ou vendu standalone ?
- Migration legacy vault : surveiller le volume de PATCH au 1er login en prod.

---

## Recommandation d'ordre
1. ✅ Quick wins sécu backend — **fait** (forbid public, rate-limit, webhook, deps).
2. ✅ Étendre `extra='forbid'` aux schémas authentifiés cœur + `except`→Sentry — **fait**.
3. ✅ a11y (noms accessibles) + tests des composants à logique — **fait** ; `app-nav-buttons` = non-problème.
4. Infra/secrets/staging (toi) au moment de viser la prod.
5. Refactos de dette quand un module est confirmé « gardé ».

---

## Mise à jour 2026-06-07 (passe d'exécution)

**Fait :**

- `extra='forbid'` étendu aux schémas authentifiés cœur (vault, 2FA, notif,
  url/site/code scan) — payloads frontend vérifiés un par un.
- Échecs critiques certificat (PDF + S3) → `logger.exception` (capturés Sentry).
- a11y : 17 vrais bloqueurs WCAG corrigés (noms accessibles `aria-label` sur les
  boutons icône-seule : toggles mot de passe, copier, statuts iso27001/nis2).
- Tests unitaires des composants à logique (contact, newsletter-unsubscribe,
  quote-action, collab-accept) — 24 tests.

**Constats (faux positifs ou déjà fait) :**

- `app-nav-buttons` : les pages sans en sont volontairement dépourvues (auth,
  admin, landing, vault, modales). Rien à corriger.
- **BasePdfBuilder déjà existant** : `pdf_brand.py` (header/footer, styles) +
  `pdf_covers.py` sont la base partagée, utilisée par les rapports de conformité.
  Migrer invoice/quote (docs financiers, layout dédié) serait inapproprié + risqué
  (PDF clients, pas de validation visuelle) → à ne PAS faire à l'aveugle.

**Reste, NON fait volontairement (risque/valeur) :**

- `forbid` sur schémas admin/awareness/blog/booking : nécessite mapping
  endpoint↔payload soigneux (ex: `/modules/{id}/complete` envoie `{answer}` ≠
  `CompleteModuleIn{quiz_score}`) — diff_one_by_one avant.
- a11y « polish » : `aria-hidden` sur les icônes décoratives (~55 fichiers) +
  audit lecteur d'écran. Non bloquant WCAG (les éléments ont un nom).
- Tests des flux complexes (onboarding, auth-modal) + pages statiques (faible valeur).
- Refactos lourds (découpe monolithes, casse des cycles via module `notifications/`)
  : code critique sans filet E2E complet → session dédiée avec régression.
- TTL token newsletter : migration pour token opt-in non sensible (valeur faible).

**#3 infra/produit — nécessite ton intervention** (inchangé) : staging Oracle,
secrets AWS (S3/region, email ImprovMX), WAF/RDS/backups, décisions produit.
