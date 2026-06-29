# Changelog

Toutes les modifications notables de ce projet sont documentées dans ce fichier.

Format basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/),
versionnage conforme à [Semantic Versioning](https://semver.org/lang/fr/).

---

## [0.1.0] — 2025-03-10

### Ajouté
- **Authentification** : inscription/connexion JWT (access token 30 min + refresh token), 2FA TOTP (QR code, validation, désactivation), verrouillage de compte après 5 échecs, logout + invalidation du refresh token
- **Vault de mots de passe** : chiffrement AES-256-GCM côté serveur, CRUD complet, catégories, recherche, export chiffré
- **API REST** : FastAPI + SQLAlchemy async + PostgreSQL, migrations Alembic, validation Pydantic, gestion d'erreurs unifiée
- **Sécurité** : hachage bcrypt, CORS configuré, rate limiting, headers de sécurité, scan statique Bandit en CI
- **Frontend Angular** : thème dark Material + Tailwind CSS, routing protégé par guard, interceptor JWT automatique, gestion des tokens expirés
- **Tests** : Vitest (frontend), pytest + httpx AsyncClient (backend), couverture auth complète
- **Architecture** : monorepo avec `backend/`, `frontend/`, `cyber-scanner/`, `infra/`

---

## [0.2.0] — 2025-03-20

### Ajouté
- **Cyber-Scanner — Tier 1** (6 modules) : headers HTTP, cookies, CORS, email (SPF/DKIM/DMARC), IP réputation, SSL/TLS basique
- **Cyber-Scanner — Tier 2** (5 modules) : DNS avancé, détection CMS, vérification de brèches, détection WAF, scanner de ports
- **Cyber-Scanner — Tier 3** (5 modules) : fingerprint technologique, audit TLS approfondi, détection subdomain takeover, threat intelligence, méthodes HTTP dangereuses
- **Cyber-Scanner — Tier 4** (5 modules) : open redirect, clickjacking, directory listing, robots.txt/sitemap, JWT checker
- **Modules transverses** : détection de secrets exposés, analyse SCA (Software Composition Analysis), scripts de remédiation SSH + FastAPI
- **Rapport PDF** : génération automatique avec résumé exécutif, score global, résultats par module, recommandations
- **326+ tests unitaires** couvrant l'ensemble des modules du scanner

---

## [0.3.0] — 2025-03-28

### Ajouté
- **Plateforme SaaS Rocher Cybersécurité** : abonnements Stripe avec plans Starter (29 €/mois) et Pro (49 €/mois), tableau comparatif des plans
- **Frontend Angular complet** :
  - Landing page avec FAQ, témoignages, compteurs animés, section newsletter, offres d'audit
  - Dashboard avec liste de sites, déclenchement de scan, badges de statut
  - Page détail d'un scan avec résultats par module
  - Page Profil (mise à jour email/mot de passe)
  - Page Onboarding post-inscription
  - Page succès Stripe post-checkout
  - Guard dashboard (redirection si non authentifié)
  - Page 404
  - Pages Ressources et Bonnes Pratiques
- **Fonctionnalités transverses** : polling temps réel des scans en cours, export CSV de l'historique, pagination, skeletons de chargement, dialog Material, thème dark unifié, i18n partiel
- **URL Scanner** : analyse d'URLs suspectes avec verdict (safe/suspicious/malicious), score de menace, type de menace, historique paginé
- **CI/CD** : premier pipeline GitHub Actions (lint, vitest, build Angular, pytest, bandit, pip-audit, alembic, deploy ECS)
- **Infrastructure Docker** : `docker-compose.staging.yml` avec backend + frontend + postgres
- **UX/UI tooling** : GSAP, AOS, animate.css, axe-core, Storybook, Compodoc

### Modifié
- Pricing mis à jour : Starter 29 €, Pro 49 €, Audit Flash 290 €, Audit Standard 890 €

---

## [0.4.0] — 2025-04-05

### Ajouté
- **Analyse de code sécurité** : intégration Bandit + Semgrep + pip-audit dans l'interface, upload ZIP ou URL GitHub/GitLab/Bitbucket, résultats par sévérité (critical/high/medium/low), pagination
- **5 outils d'analyse supplémentaires** : détection patterns dangereux, complexité cyclomatique, dépendances obsolètes, licences, fichiers sensibles exposés
- **RGPD complet** : bannière de consentement cookies, page Politique de confidentialité, export RGPD (JSON chiffré), suppression de compte avec cascade DB
- **Dashboard redesigné** : nouvelle UI Tailwind, modale de sélection de plan, bouton de suppression dans l'historique URL Scanner
- **Persistance de l'historique de navigation** : dernière page visitée mémorisée pour le retour post-login
- **Reset password** : correction timezone + couverture tests complète

### Corrigé
- Export vault : déchiffrement des mots de passe avant téléchargement, attente du chargement avant export
- Toast de login bloqué supprimé, bouton dismiss ajouté sur les erreurs inline
- Forgot-password retournait 500 (désormais 200/422)
- Imports Angular manquants (`CodeScan`, `MatProgressSpinnerModule`)
- URL SSH + HTTPS acceptées pour l'analyse de dépôt
- Normalisation de l'URL au collé (paste) sans attendre le blur
- Erreur URL uniquement si champ dirty + non-vide + invalide

---

## [0.5.0] — 2025-04-08

### Ajouté
- **Module NIS2** : checklist de conformité 34 critères répartis en 10 catégories, scoring (compliant=2pts, partial=1pt, NA exclu), export PDF, isolation stricte par utilisateur
- **Téléchargement PDF pour les scans URL** : endpoint `GET /url-scans/{id}/pdf`, bouton de téléchargement dans l'historique
- **UX/UI** : redirection post-login vers la page demandée, amélioration du flux onboarding, téléchargement PDF en blob (sans onglet parasite), mise à jour du tableau de pricing

### Corrigé
- Requêtes N+1 sur les endpoints scans et sites (eager loading SQLAlchemy)
- Index DB ajoutés sur `user_id`, `site_id`, `status` pour accélérer les requêtes fréquentes
- Polling remplacé par un backoff exponentiel (`pollWithBackoff`) avec cap configurable
- Cache `shareReplay(1)` sur `getPlans()` et `getMySubscription()` pour éviter les appels HTTP répétés
- Prix Audit Standard corrigé à 390 € HT (était 890 €)
- Nombre de modules affiché corrigé à 21 (comptage réel depuis `scan_service`)
- Redirect 2FA vers `/cyberscan` (accueil) et non `/cyberscan/dashboard`
- `STATUS_LIST` déplacé en propriété de composant dans `Nis2Component`
- Compat Angular < 18.1 : `@let` remplacé par appels de méthode directs

---

## [0.6.0] — 2025-04-13

### Ajouté
- **Infrastructure AWS production** : ALB (Application Load Balancer) devant ECS Fargate, groupe cible avec health-check `/health`, règle HTTPS avec redirection HTTP→HTTPS 301
- **DNS & TLS** : certificat ACM pour `api.cyberscanapp.com` avec validation DNS automatique via Route 53, comportement CloudFront `/api/*` → ALB
- **Sécurité réseau** : groupe de sécurité ECS restreint au seul ALB (port 8000 non exposé au public internet)
- **CI/CD secrets** : injection de `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `SMTP_USER`, `SMTP_PASSWORD` dans la task definition ECS via `jq`
- **Suite de tests — Backend** : 20 tests de non-régression couvrant AUTH/NIS2/SCAN/URLSCAN/USER/API ; 25 tests de validation des entrées ; 15 tests d'intégration NIS2
- **Suite de tests — Frontend** : 7 tests Vitest pour `pollWithBackoff` ; 18 tests pour `CyberscanService` ; 3 gardes de régression sur `LandingComponent`
- **Protection des branches** : règles GitHub — PR obligatoire + status checks CI avant merge sur `master`

### Modifié
- CI (`ci.yml`) : `pull_request` déclenché sur `main`, `master` et `develop`

---

## [0.7.0] — 2025-12-01

### Ajouté
- **Module ISO 27001** : auto-évaluation, scoring, export PDF
- **Module PCA** : plan de continuité d'activité, export PDF
- **Phishing simulation** : création de campagnes, templates personnalisables, rapport PDF
- **Public scans** : endpoint sans authentification avec protection SSRF et rate limiting
- **Waitlist API** : inscription avec rôle et entreprise, endpoint `/count`
- **2FA TOTP** : QR code, validation, désactivation
- **Code scans** : intégration GitHub/GitLab/Bitbucket avec token embed, background jobs

### Modifié
- Vault zero-knowledge migré vers chiffrement AES-256-GCM côté client (Web Crypto API)

---

## [0.8.0] — 2026-03-01

### Ajouté
- **Module Dark Web Dossier** : upload CSV, vérification HIBP/LeakCheck, scoring risk+severity, rescan, export CSV, monitoring mensuel, timeline, suite de tests complète
- **Actions sécurité post-audit** : rotation secrets, migration vers ECS Secrets Manager, OIDC GitHub Actions (plus de clés AWS statiques), `ng update` Angular Material

---

## [0.9.0] — 2026-05-01

### Ajouté
- **Module RSSI Externalisé** : gestion complète des missions consultant B2B — CRUD clients, visites, actions correctives, livrables, upload S3, génération PDF, guard `rssiGuard`, toggle admin, profil consultant
- **Staging Oracle Cloud** : `staging/docker-compose.yml` + Caddy reverse proxy + workflow `deploy-staging.yml` (ARM64 via QEMU/Buildx), instance Oracle A1.Flex Always Free
- **Module phishing natif** : remplacement de GoPhish par moteur natif — 13 templates HTML riches, générateur de domaines look-alike, file d'attente non-bloquante, multi-scénarios, envoi planifié, notification email de fin de campagne, rapport PDF enrichi, comparaison inter-campagnes
- **Page vitrine API** : `/cyberscan/api` avec liste d'attente — validation marché Phase 0
- **Devis PDF** : système complet multi-lignes, bon pour accord, CGV, email automatique
- **Add-on sites supplémentaires** : pack Stripe `+5 sites` à 5 €/mois
- **Badges gamification** : 5 badges calculés dynamiquement selon l'activité
- **Calculateur coût d'une cyberattaque** : `/cout-cyberattaque`
- **Email mensuel de synthèse** de sécurité
- **Export NIS2 prêt-à-déposer**
- **Mode audit collaboratif**
- **Rapport PDF marque blanche**
- **Rapport public partageable** : URL shareable + bouton copie
- **Surveillance dark web** : HaveIBeenPwned email breach monitoring
- **CTA Audit Flash** dans les rapports de scan

### Modifié
- Couverture de tests backend portée à 84 %+ (1 645 tests), seuil CI ajusté pour Python 3.12
- `phishing_service.py` 1 550 lignes scindé en `phishing_service.py` (logique métier) + `phishing_templates.py` (templates HTML)

### Corrigé
- Bug `auto-repair` état 2FA incohérent (`enabled=True`, `secret=None`)
- Prix Audit Flash harmonisés à 290 € HT sur toutes les pages

---

## [1.0.0] — 2026-05-29

### Ajouté

#### Module Sensibilisation NIS2 (e-learning B2B — 11 sprints)
- **Data model** : 12 entités SQLAlchemy — `AwarenessOrganization`, `AwarenessLearner`, `AwarenessProgram`, `AwarenessModule`, `AwarenessEnrollment`, `AwarenessProgress`, `AwarenessQuizAttempt`, `AwarenessCertificate`, `AwarenessBadge`, `AwarenessLearnerBadge`
- **Contenu** : 17 modules NIS2 Article 21 complets (markdown + quiz YAML), importeur idempotent `ContentImporter`, validation YAML en CI
- **Organisations et learners** : CRUD multi-tenant, import CSV en masse, quota learners configurable, anonymisation RGPD
- **Authentification learner** : magic-link JWT sans mot de passe, email d'invitation automatique
- **Progression** : state machine `not_started → in_progress → completed`, heartbeat vidéo, calcul `completion_pct`
- **Moteur de quiz** : pool YAML, tirage aléatoire par seed, 3 tentatives max, cooldown configurable, scoring pondéré, validation anti-triche
- **Attestations PDF** : génération automatique à 100 % de complétion, QR code, signature SHA-256, validité 12 mois, page de vérification publique `/verify-certificate`
- **Gamification** : points XP, 20 badges (bronze/silver/gold/platinum), niveaux 1–10, leaderboard par organisation
- **Dashboards multi-rôles** : consultant (KPIs globaux, at-risk, funnel), admin organisation (progression), learner (modules + badges + niveau)
- **Rapport PDF NIS2 Article 21** : export conformité avec taux de complétion, certificats émis, learners à risque
- **Frontend Angular** : portail learner (`/awareness/login`, `/awareness`, `/awareness/module/:id`), admin sensibilisation, détail organisation, page tarifs, guard `awarenessLearnerGuard`
- **Suite de tests** : 1 787 tests backend (92 % couverture), 1 778 tests frontend — 100 % verts

#### Intégration sur la plateforme
- Section dédiée Sensibilisation NIS2 sur la landing (features, CTA, tarifs)
- Bouton « Formation NIS2 » dans la navbar
- Option « Formation NIS2 » dans le formulaire contact

### Modifié
- Angular 19 → 20 (core + CLI + Angular Material + CDK)
- `phishing_service.py` : split logique métier / templates HTML

### Corrigé
- SQLAlchemy lazy load async (`MissingGreenlet`) sur `AwarenessProgramOut.modules`
- N+1 queries sur `list_organizations`, `list_programs_admin` (JOIN + GROUP BY)
- Webhook Stripe : appel bloquant wrappé dans `asyncio.to_thread()`
- 5× `except Exception: pass` remplacés par `logger.warning()`
- `class Config` Pydantic V2 déprécié migré vers `ConfigDict`
- Index DB composite `(organization_id, is_active)` sur `awareness_learners`

### Infrastructure qualité
- `CLAUDE.md`, `SECURITY.md` (modèle STRIDE), `Makefile`, ADRs (`docs/adr/`)
- Pre-commit : ruff, gitleaks, mypy, ESLint/Prettier, conventional commits
- Script qualité PDF : couverture, complexité cyclomatique, audit sécurité, stats Git

---

## [1.1.0] — 2026-06-03

### Ajouté
- **Contenu sensibilisation étendu** : 28 modules NIS2 au total (+ 11 nouveaux : chiffrement, sécurité physique, gestion vulnérabilités, continuité activité, chaîne approvisionnement, déclaration incident NIS2, DORA, CRA, 3 études de cas réels) ; 3 programmes par rôle (direction, technique, onboarding) en plus du programme essentiel (28 modules)
- **Module DORA enrichi** : seuils RTO/RPO réglementaires, registre ICT, superviseurs compétents, alignement ISO 27001, scénario concret ETI
- **Endpoint admin** `POST /admin/awareness/sync-content` : permet de recharger le contenu YAML à chaud sans redéploiement
- **Formation sur `/cyberscan/sensibilisation`** : les 28 modules NIS2 Awareness sont désormais accessibles depuis la page formation employés existante

### Modifié
- **Politique de pricing v2** — nouvelle grille complète :
  - Scanner : Surveillance Starter 14,90 €/mois (1 site, hebdo), Surveillance Pro 49 €/mois (5 sites, 20 scans/mois), Surveillance Business 149 €/mois (15 sites, quotidien)
  - API : Dev 49 €/500 scans, Pro 199 €/5 000 scans, Business 499 €/25 000 scans
  - Formation NIS2 : S 79 €/10 learners, M 199 €/30, L 449 €/75, XL 899 €/200
  - Audits : Flash 390 €, App-Check 990 €, Pentest léger 2 490 €, Audit NIS2/RGPD 1 290 €
  - Add-on +5 sites : 9 €/mois
  - Audit NIS2/RGPD ajouté sur la page `/audit-pme`
  - Plans monitoring (`Vigie`/`Sentinelle`/`Blindage 360`) remplacés par les nouvelles appellations `Surveillance Starter/Pro/Business`
- **CI** : job `coverage` fusionné dans le job `backend` (tests exécutés une seule fois), règle `concurrency` ajoutée (annulation automatique des anciens runs sur la même branche) — gain ~15 min par pipeline

### Corrigé
- **Hang test_training_unit** : `_load_all_modules` appelait `yaml.safe_load()` sur un `MagicMock` (mock AwarenessProgram) — PyYAML tentait de le lire comme un fichier infini, causant un blocage indéfini au 8e test
- Formulaire ajout learner : inputs Tailwind corrigés, bouton désactivé si email vide
- Bouton quiz renommé de « Passer le quiz » en « Passer au quiz »

### Tests
- `awareness_quiz_engine.py` porté à **100 % de couverture** (ajout de 11 tests d'intégration couvrant : `start_quiz` succès/cooldown 429/max tentatives 422/module sans quiz 422/mauvaise inscription 403/module hors programme 404 ; `submit_quiz` réussi/échoué/score partiel/incrément attempt_number/YAML corrompu 422)

---

## [1.2.0] — 2026-06-28

### Ajouté

- **Vault zero-knowledge complet** : les champs `title`, `username`, `url`, `notes` sont chiffrés AES-GCM **côté client** ; le serveur refuse tout champ en clair et ne stocke que des blobs opaques (migrations `crypto_salt`, `title_encrypted`)
- **Pages légales** : CGV + DPA (accord de traitement des données), mise à jour mentions légales/CGU ; SIRET + adresse réels (attestation INPI), téléphone ; prix audit aligné à 390 €
- **OpenAPI** : `summary` + codes d'erreur documentés (auth, contact, blog, admin)
- **Accessibilité** : `aria-label` sur les boutons icône-seule

### Sécurité

- **P0** — confusion de types de JWT corrigée + invalidation des sessions au reset du mot de passe
- **P0-3** — fermeture de la race du quota de scans (verrou `FOR UPDATE`, fin du check-then-act)
- **P1-1** — les échecs TOTP comptent désormais dans le verrouillage de compte
- **P1-2** — chiffrement du `totp_secret` au repos (Fernet)
- **P1-3** — validation de chaque redirection avant de la suivre (anti-SSRF)
- **P1-4** — refus strict de tout champ vault en clair côté serveur
- `extra=forbid` sur les schémas d'entrée authentifiés clés ; remontée Sentry des échecs critiques de certificat

### Performance

- Pagination des endpoints de liste admin
- Appels Stripe déportés en thread (non bloquants)
- Appel HIBP (dark web) non bloquant
- Suppression du N+1 sur le dashboard awareness (GROUP BY)

### Corrigé

- Tâche phishing détachée correctement référencée + exception non exposée
- SSR : `clipboard.service` SSR-safe ; corrections de build (config SSR/AOS/NgClass)
- `requirements.prod.txt` : ajout httpx, dnspython, boto3, email-validator (divergence prod/dev)
- Garde-fou anti-prod sur `reset_test_account_scans` (Alembic)

### Interne

- **Remboursement complet de la dette technique** (22 items) : refacto de services en sous-packages, nettoyage des dépendances mortes, purge des artefacts, `.gitignore`, alignement apscheduler prod/dev
- Correction des 36 tests cassés post-refacto ; specs frontend adaptées au SSR

---

## [2.0.0] — 2026-06-28

> Rebranding complet : **CyberScan → Rocher Cybersécurité** (nom, domaine, URLs).

### Modifié

- **Nom de marque** : « CyberScan » → « Rocher Cybersécurité » partout (interface, emails, PDF, documentation, module scanner)
- **Domaine** : `cyberscanapp.com` → `rochercybersecurite.com`. L'ancien domaine est conservé avec une **redirection 301** permanente (fonction CloudFront)
- **URLs à la racine** : suppression du préfixe de route `/cyberscan` — la landing est sur `/`, les pages sur `/dashboard`, `/blog`, `/contact`, etc.
- **Emails** : envoi depuis `no-reply@rochercybersecurite.com` (Resend, DKIM/SPF vérifiés), réception sur `contact@rochercybersecurite.com` (ImprovMX)
- **Noms de fichiers téléchargés** : `cyberscan_*.pdf/.csv/.json` → `rochercybersecurite_*` ; token de vérification de domaine phishing `_cyberscan-verify` → `_rocher-verify`

### Ajouté

- Infrastructure du nouveau domaine : certificat ACM multi-domaines, alias CloudFront, zones Route 53, hébergement email (Resend + ImprovMX)

### Corrigé

- **Webhook Stripe** : l'URL pointait vers une route inexistante (404 silencieux servi en fallback SPA, événements jamais traités) → corrigée vers `/api/v1/webhooks/stripe`
- **Open redirect** : durcissement de la validation `returnUrl` — rejet des cibles externes (`//evil`, `/\`) et des zones à part (`/auth`, `/vault`, `/awareness`)

### Supprimé

- Configuration Oracle Cloud staging (abandonnée) : dossier `staging/`, workflow `deploy-staging.yml`, `docker-compose.staging.yml`

### CI/CD

- **`deploy.yml`** : les migrations Alembic s'exécutent désormais sur la **nouvelle** image (elles étaient jouées sur l'ancienne → migrations jamais appliquées en prod)
- `python-multipart` bumpé en 0.0.31 (CVE-2026-53538/53539/53540) ; CVE starlette sans correctif compatible ignorées et documentées
- Ajout d'un `.gitleaks.toml` (allowlist des faux tokens de fixtures de test)

---

## [Unreleased]

---

[2.0.0]: https://github.com/DavidRocher01/cyber-vault/compare/v1.2.0...v2.0.0
[1.2.0]: https://github.com/DavidRocher01/cyber-vault/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/DavidRocher01/cyber-vault/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/DavidRocher01/cyber-vault/compare/v0.9.0...v1.0.0
[0.9.0]: https://github.com/DavidRocher01/cyber-vault/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/DavidRocher01/cyber-vault/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/DavidRocher01/cyber-vault/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/DavidRocher01/cyber-vault/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/DavidRocher01/cyber-vault/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/DavidRocher01/cyber-vault/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/DavidRocher01/cyber-vault/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/DavidRocher01/cyber-vault/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/DavidRocher01/cyber-vault/releases/tag/v0.1.0
