# SECURITY.md — Modèle de sécurité Cyber-Vault

## Vue d'ensemble

Cyber-Vault est une plateforme SaaS de cybersécurité. Ce document décrit les menaces identifiées, les mesures de protection en place, et la procédure de signalement des vulnérabilités.

---

## Analyse des menaces (STRIDE)

| Menace | Vecteur | Mesure |
|--------|---------|--------|
| **Spoofing** | Usurpation d'identité utilisateur | JWT signé (HS256) + refresh tokens révocables en DB |
| **Tampering** | Modification des données en transit | TLS 1.2+ obligatoire en prod (HSTS) |
| **Repudiation** | Déni d'action | Logs structurés (Loguru) + Sentry |
| **Information Disclosure** | Fuite de données sensibles | Zero-knowledge vault (chiffrement AES-256-GCM côté client) |
| **Denial of Service** | Épuisement des ressources | Rate limiting SlowAPI multi-niveaux |
| **Elevation of Privilege** | Accès non autorisé aux ressources admin | RBAC + `ADMIN_API_KEY` sur routes admin |

---

## Mesures de sécurité implémentées

### Authentification et sessions

- **JWT** : durée d'accès 30 min, algorithme HS256, clé ≥ 64 caractères
- **Refresh tokens** : durée 30 jours, stockés en DB sous forme HMAC-SHA256, révocables
- **Mots de passe** : bcrypt (coût adaptatif), jamais stockés en clair
- **Verrouillage de compte** : 5 tentatives échouées → verrouillage 15 min
- **Magic links** : expiration 15 min, usage unique

### Autorisation

- **RBAC** : rôles `user` / `admin` — vérifiés sur chaque endpoint sensible
- **Isolation des données** : chaque utilisateur ne peut accéder qu'à ses propres ressources
- **Routes admin** : protégées par `x-admin-key` en plus de l'auth JWT

### Chiffrement des données (Vault zero-knowledge)

- Chiffrement **AES-256-GCM** côté client (Web Crypto API)
- Dérivation de clé **PBKDF2** (100 000 itérations, SHA-256) à partir du mot de passe maître
- Le serveur ne reçoit et ne stocke **jamais** les données en clair ni la clé de déchiffrement
- Le mot de passe maître reste en mémoire côté client uniquement

### Protection des transports

- **TLS 1.2+** en production (HSTS activé, `max-age=31536000; includeSubDomains; preload`)
- Headers de sécurité sur chaque réponse :
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Content-Security-Policy` (strict, `frame-ancestors 'none'`)
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy: geolocation=(), microphone=(), camera=()`
  - `Cross-Origin-Opener-Policy: same-origin`
  - `Cross-Origin-Resource-Policy: same-origin`

### Validation et injection

- **Pydantic strict** (`extra='forbid'`) sur tous les schémas exposés publiquement
- **ORM SQLAlchemy uniquement** — aucune concaténation de chaînes SQL
- **SSRF** : `assert_no_ssrf()` bloque les requêtes vers les IP privées / localhost / APIC AWS IMDS
- **CORS** : liste d'origines autorisées explicite (`ALLOWED_ORIGINS`)

### Rate limiting

- Lecture : 60 req/min par IP
- Écriture : 30 req/min par IP
- Auth : 5 tentatives / 15 min avant verrouillage

### Secrets et configuration

- Tous les secrets dans des variables d'environnement (jamais dans le code)
- Secrets en production : **AWS Secrets Manager** via ECS task definition
- `.env` exclu du dépôt (`.gitignore`)
- Détection de secrets dans les commits : **gitleaks** (pre-commit hook)
- Audit des dépendances : **bandit** (Python) + **npm audit** (frontend)

---

## Sensibilité des données

| Donnée | Sensibilité | Stockage |
|--------|-------------|---------|
| Mots de passe utilisateur | Critique | bcrypt hash uniquement |
| Entrées vault | Critique | Chiffré AES-256-GCM côté client, opaque côté serveur |
| Refresh tokens | Haute | HMAC-SHA256 en DB, jamais en clair |
| Emails | Moyenne | En clair (nécessaire pour auth) |
| Logs applicatifs | Basse | Structurés, sans données sensibles |

---

## Conformité

- **OWASP Top 10** : A01 (RBAC), A02 (crypto), A03 (injection ORM), A05 (headers), A07 (auth), A09 (logs Sentry)
- **RGPD** : données hébergées EU (AWS eu-west-3 Paris), suppression sur demande
- **NIS2** : module d'auto-évaluation intégré à la plateforme

---

## Signalement d'une vulnérabilité

Si vous découvrez une vulnérabilité de sécurité dans Cyber-Vault :

1. **Ne pas créer d'issue GitHub publique**
2. Envoyer un email à : `contact@cyberscanapp.com` avec le sujet `[SECURITY]`
3. Inclure : description, étapes de reproduction, impact estimé, preuve de concept si possible
4. Délai de réponse : **48h** pour un accusé de réception, **7 jours** pour une évaluation initiale

Les vulnérabilités critiques (CVSS ≥ 9.0) sont traitées en priorité avec un correctif sous **24h**.

---

## Historique des audits

| Date | Type | Résultat |
|------|------|----------|
| 2026-04-21 | Audit interne | Rotation secrets, migration ECS Secrets Manager, OIDC GitHub Actions |
