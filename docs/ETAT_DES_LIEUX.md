# État des lieux — Cyber-Vault (au 2026-07-29)

Snapshot de reprise : où en est le projet, quoi est en prod / sur `develop` /
à faire. Utile notamment pour reprendre depuis un **autre poste** (le contexte de
travail détaillé n'est pas dans git). Mettre à jour ce fichier au fil de l'eau.

> Rappel workflow : travailler sur `develop`, **jamais** committer sur `master` ;
> merge prod uniquement sur **confirmation explicite**. Voir `CLAUDE.md`,
> `docs/DEV_SETUP.md`.

---

## 1. Chantier en cours — Remédiation audit sécurité 2026-07-27

Audit `docs/SECURITY_AUDIT_2026-07-27.md` (17 findings : 0 HIGH, 6 MEDIUM,
7 LOW, 4 INFO). Remédiation en **7 lots S1→S7, livrés dans l'ordre**.

**Statut : les 7 lots sont TERMINÉS sur `develop`, CI verte — PAS ENCORE EN PROD.**
En attente de **ta décision de merge** `develop→master`.

| Lot | Objet | Commit | État |
|-----|-------|--------|------|
| S1 | Durcissement surface publique non-auth (mailbombing unlock, recon anonyme, escape HTML) | `f50c10a` | ✅ CI verte |
| S2 | Rate-limiting (code no-op activable : Redis, X-Origin-Verify, TRUSTED_PROXY_COUNT) | `75cb704` | ✅ CI verte |
| S3 | Intégrité monétisation (quota URL monotone, gate plan `current_period_end`, plafond scan/IP) + migration `d3b47ded55b3` | `f779491` | ✅ CI verte |
| S4 | Injection/robustesse entrées Dark Web (`_csv_safe`, `_parse_emails_csv`, lecture CSV bornée 413) | `f7d3454` | ✅ CI verte |
| S5 | RGPD (export Art.20 complet, purge/rétention 90j public_scans+darkweb, scrubbing PII Sentry) | `bd534ce` | ✅ CI verte |
| S6 | Auth admin front (clé `X-Admin-Key` en mémoire seule, SSR-safe) | `0d76aeb` | ✅ CI verte |
| S7 | Registre d'acceptation du risque (doc) | `ec06e70` | 📄 docs-only |

**Merge prod** = déclenche `deploy.yml` (build ECR + task def + **migration
`d3b47ded55b3`** `url_scan_usages` + update ECS + front S3/CloudFront) puis la
recette post-prod auto (rollback ECS si KO). Tête Alembic **unique**, migration
rétro-compatible (compatible rollback CODE-only). Quand prêt : demander le merge,
la surveillance du run + checks prod suivent.

---

## 2. Actions INFRA en attente (utilisateur, hors code)

N'empêchent PAS le merge (les fixes code correspondants sont des no-op activables).

- **S2** → `docs/S2_INFRA_CHECKLIST.md` : (A) provisionner **ElastiCache Redis** +
  injecter `REDIS_URL` (~12-15 $/mois) ; (B) **verrouiller l'ALB derrière
  CloudFront** (header X-Origin-Verify + règle listener 403) + `ORIGIN_VERIFY_SECRET`.
  ⚠️ ne pas ajouter ces clés à `$secret_names` de `deploy.yml` avant de les créer
  dans Secrets Manager (sinon la task ECS ne démarre pas).
- **S6** → `docs/S6_INFRA_CHECKLIST.md` : **rotation `ADMIN_API_KEY`**
  (`openssl rand -hex 32` → Secrets Manager `cybervault/prod` → force-new-deployment).

---

## 3. Actions BUSINESS / LÉGALES en attente

- **Assurance RC Pro cyber** — à souscrire **avant les 1ers contrats clients** ;
  vérifier que le **pentest/scan intrusif est couvert**.
- **Médiateur de la consommation (B2C)** — décision à trancher : adhérer
  (~120-200 €/an) **si B2C**, ou passer **B2B-only**. Seul placeholder restant du
  pack légal.
- **Email de contact (changement de domaine)** — ImprovMX créé ; **config MX +
  Secrets Manager à finaliser**. Nettoyage dev : remplacer le SMTP Gmail
  `activatecyberscan` par **Resend** dans le `.env` local (prod déjà OK).
- **INPI** — dépôt marque « Rocher Cybersécurité » **n°5272918** (classes 9+42) ;
  **surveiller les mails BOPI / opposition**.

---

## 4. Récemment livré EN PROD (contexte)

- **Refonte tarifaire complète** (grille 0/49/149/390, facturation annuelle,
  gate email scan gratuit, CGV, TVA franchise en base) — migration `256304ec94d2`,
  Stripe LIVE backfillé. Piège tracé : backfill Stripe **juste après** le deploy.
- **Resserrage freemium** (plafond scan URL 5/mois au Gratuit, verrou export
  NIS2/ISO).
- **Rebranding « Rocher Cybersécurité »** (branded house ; domaines
  rochercybersecurite.com/.fr + 301 depuis cyberscanapp.com). « Rocsûr »
  **abandonné** (ne pas reproposer).
- **Scan gratuit — gate email (LOT 1)** en prod ; reste **lot 2** = Turnstile +
  cache domaine.
- **Audit hebdo CI** réparé (security-weekly) ; secret `RESEND_API_KEY` rafraîchi.
- Modules livrés : Dark Web Dossier, RSSI externalisé, refonte Phishing,
  observabilité/alerting CloudWatch, recette post-prod, admin plan-override.

---

## 5. Décisions & différés ACTÉS (ne pas reproposer spontanément)

- **Sécurité différée** (décision 2026-07-22, cf. `docs/S7_RISK_ACCEPTANCE.md`) :
  CSP + Trusted Types CloudFront (SPA), rotation clés `.env` S-3, Vault AAD,
  RGPD S-8 effacement, IP-pinning S-5, consentement phishing S-6, Dark Web emails
  tiers, TOTP replay.
- **Oracle Staging** — abandonné (quota A1=0, pas de PAYG).
- **Analytics maison** — design validé mais **pas développé** ; prérequis = créer
  un **vrai rôle admin** (aucune UI admin réelle aujourd'hui, juste la clé
  `X-Admin-Key`).

---

## 6. En cours / backlog non-bloquant

- **Sensibilisation NIS2** (e-learning Art.21) — module en cours (attestations
  PDF+QR, gamification, multi-tenancy).
- **Observabilité** — reste Redis multi-instance (limiter+scheduler) + métriques
  de latence (lié à l'action infra S2).
- Dette technique — la majorité des gros refactos restants sont des **décisions**
  différées, pas de la dette bloquante.

---

## 7. Où retrouver le contexte dans le repo

- `CLAUDE.md` — règles projet (branches, archi couches, sécurité, Alembic, tests).
- `docs/DEV_SETUP.md` — installer l'env sur un nouveau poste.
- `docs/SECURITY_AUDIT_2026-07-27.md` — l'audit en cours de remédiation.
- `docs/S2_INFRA_CHECKLIST.md` / `docs/S6_INFRA_CHECKLIST.md` — actions infra.
- `docs/S7_RISK_ACCEPTANCE.md` — risques acceptés/différés.
- `docs/GITHUB_SECRETS.md` — secrets CI/CD.

> ⚠️ Ce fichier est un instantané au **2026-07-29**. Les dates/statuts « en prod »
> ou « sur develop » peuvent avoir évolué — vérifier `git log`, `git branch`, et
> l'état réel avant d'agir.
