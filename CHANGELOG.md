# Changelog

Toutes les modifications notables de ce projet sont documentées dans ce fichier.

Format basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/),
versionnage conforme à [Semantic Versioning](https://semver.org/lang/fr/).

---

## [0.6.0] — 2025-04-13

### Ajouté
- **Infrastructure AWS production** : ALB (Application Load Balancer) devant ECS Fargate, groupe cible avec health-check `/health`, règle HTTPS avec redirection HTTP→HTTPS 301
- **DNS & TLS** : certificat ACM pour `api.cyberscanapp.com` avec validation DNS automatique via Route 53, comportement CloudFront `/api/*` → ALB
- **Sécurité réseau** : groupe de sécurité ECS restreint au seul ALB (port 8000 non exposé au public internet)
- **CI/CD secrets** : injection de `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `SMTP_USER`, `SMTP_PASSWORD` dans la task definition ECS via `jq` (merge sans écrasement des autres variables)
- **Suite de tests — Backend** : 20 tests de non-régression couvrant AUTH/NIS2/SCAN/URLSCAN/USER/API ; 25 tests de validation des entrées (champs manquants, URLs invalides, statuts NIS2 inconnus, pagination négative) ; 15 tests d'intégration NIS2
- **Suite de tests — Frontend** : 7 tests Vitest pour `pollWithBackoff` (backoff exponentiel, plafond `maxMs`, `takeWhile` inclusif) ; 18 tests pour `CyberscanService` couvrant NIS2, téléchargements blob et comportement du cache `shareReplay` ; 3 gardes de régression sur les données statiques de `LandingComponent`
- **Protection des branches** : règles GitHub — PR obligatoire + status checks CI avant merge sur `master`

### Modifié
- CI (`ci.yml`) : `pull_request` déclenché sur `main`, `master` et `develop`

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

## [0.3.0] — 2025-03-28

### Ajouté
- **Plateforme SaaS CyberScan** : abonnements Stripe avec plans Starter (29 €/mois) et Pro (49 €/mois), tableau comparatif des plans
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

[0.6.0]: https://github.com/DavidRocher01/cyber-vault/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/DavidRocher01/cyber-vault/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/DavidRocher01/cyber-vault/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/DavidRocher01/cyber-vault/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/DavidRocher01/cyber-vault/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/DavidRocher01/cyber-vault/releases/tag/v0.1.0
