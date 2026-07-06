# Dossier de sécurité — Cyber-Vault / Rocher Cybersécurité

> Synthèse des mesures de sécurité de la plateforme, destinée aux audits, à la due diligence
> client et à la souscription d'assurance (RC Pro / cyber). Rédigé à partir du code et de
> l'infrastructure réels. Dernière mise à jour : 2026-07.

## 1. Posture générale

Cyber-Vault est une plateforme SaaS de cybersécurité B2B/B2C. La sécurité est traitée comme
une exigence produit, pas une option : chiffrement zero-knowledge du coffre, authentification
forte, isolation multi-tenant vérifiée, 0 CVE tolérée en CI, et une suite de tests d'invariants
de sécurité exécutée à chaque commit.

| Domaine | État |
|---|---|
| Authentification | bcrypt · JWT · 2FA TOTP · verrou anti-bruteforce | ✅ |
| Isolation multi-tenant (IDOR) | audit complet ~150 routes — **aucun trou** | ✅ |
| Injection (SQL / SSRF) | ORM exclusif · anti-SSRF durci | ✅ |
| Chiffrement | vault zero-knowledge AES-GCM · TOTP chiffré · TLS | ✅ |
| Gestion des secrets | AWS Secrets Manager · IAM moindre privilège | ✅ |
| Dépendances | 0 CVE (pip-audit + npm audit) · Dependabot | ✅ |
| Supervision | Sentry · 5 alarmes CloudWatch · logs latence | ✅ |
| Durcissement en cours | CSP vitrine · SPF `-all` | 🟠 en cours |

## 2. Modèle de menace (synthèse)

- **Actifs protégés** : mots de passe des coffres (données les plus sensibles), identifiants et
  sessions, données clients (sites, scans, dossiers dark web), moyens de paiement (délégués à
  Stripe — aucune donnée carte stockée), livrables et données RSSI.
- **Attaquants considérés** : utilisateur authentifié malveillant (tentative d'accès inter-comptes),
  attaquant externe non authentifié (endpoints publics, formulaires, webhooks), bruteforce d'identifiants.
- **Surfaces d'entrée** : API publique, formulaires (contact, scan public), URL fournies par
  l'utilisateur (scanner, phishing), webhooks Stripe, uploads de fichiers (livrables RSSI, CSV).

## 3. Contrôles de sécurité

### 3.1 Authentification
- Mots de passe hachés **bcrypt** (jamais stockés en clair) ; opération déportée en threadpool.
- **JWT** signés (PyJWT) : access token en `sessionStorage`, refresh token en **cookie httpOnly**
  (hors de portée du JavaScript → réduit le vol par XSS).
- **2FA TOTP** (RFC 6238) ; le secret TOTP est **chiffré au repos** (Fernet).
- **Verrou anti-bruteforce en base** : compteur `failed_login_attempts` + `locked_until`
  (les échecs 2FA comptent aussi) — protection globale, indépendante des instances.
- Tokens de réinitialisation de mot de passe à usage unique et à durée limitée.

### 3.2 Autorisation & isolation multi-tenant
- Contrôle d'accès centralisé via des dépendances/ helpers réutilisés partout :
  `get_current_user`, `get_rssi_consultant`, `get_current_learner`, `get_user_resource`,
  `_get_client_or_404`, `_get_org_or_404`…
- **Audit IDOR complet** (~40 fichiers d'endpoints, 150+ routes) : aucune ressource privée n'est
  accessible par `{id}` sans filtre sur le propriétaire ; aucune fuite de liste inter-comptes.
- Les ressources partagées par token (devis, acceptation de collaboration, scan public,
  vérification de certificat) utilisent des tokens cryptographiques non énumérables
  (`secrets.token_urlsafe`), pas des identifiants séquentiels.

### 3.3 Injection & requêtes sortantes
- **SQL** : ORM SQLAlchemy exclusivement, aucune concaténation de chaînes SQL.
- **SSRF** : toute URL fournie par l'utilisateur passe par `assert_no_ssrf()`, qui bloque
  localhost, plages privées, link-local **169.254.169.254 (métadonnées cloud)**, `0.0.0.0`, `::`,
  IPv4-mapped, et les schémas non-http — y compris via résolution DNS (anti-rebinding).
- **Validation** : schémas Pydantic avec `extra='forbid'` sur les entrées publiques.

### 3.4 Chiffrement
- **Coffre zero-knowledge** : les champs sensibles (titre, identifiant, URL, notes, mot de passe)
  sont chiffrés **côté client** en AES-GCM 256, avec une clé dérivée (PBKDF2) du mot de passe
  maître et d'un sel propre à l'utilisateur. **Le backend ne stocke que des blobs opaques et ne
  peut pas déchiffrer** — même en cas de compromission de la base.
- Secret TOTP chiffré au repos (Fernet). TLS de bout en bout (terminé par CloudFront).

### 3.5 Gestion des secrets & infrastructure
- Aucun secret dans le code : **AWS Secrets Manager** (clé JWT, DB, clés Stripe, etc.).
- Conteneur backend avec **rôle IAM au moindre privilège** (accès S3 restreint au préfixe des
  livrables uniquement).
- **RDS PostgreSQL chiffrée**, sauvegardes automatiques 7 jours. **Bucket S3 privé + chiffré**,
  tout accès public bloqué, téléchargements par URL présignée à durée limitée.
- **En-têtes de sécurité** (CloudFront + backend) : HSTS, X-Frame-Options DENY, X-Content-Type-Options
  nosniff, Referrer-Policy, Permissions-Policy, COOP/CORP. **CORS** restreint aux origines autorisées.

### 3.6 Paiement
- Paiement délégué à **Stripe** (aucune donnée de carte ne transite ni n'est stockée côté serveur).
- Webhooks **à signature vérifiée** et **idempotents** (table `ProcessedStripeEvent`).

### 3.7 Abus & limitation de débit
- **slowapi** : login limité (10/min), scan public (3/h), etc. — combiné au verrou de compte
  (défense en profondeur).

### 3.8 Dépendances & chaîne d'approvisionnement
- **0 CVE tolérée** : `pip-audit` (backend) et `npm audit` (frontend) bloquent la CI ; **Dependabot** actif.

### 3.9 Supervision & réponse
- **Sentry** (erreurs + tracing). **5 alarmes CloudWatch** (santé backend, 5xx, RDS, CPU) → SNS email.
- Journalisation structurée de la latence par requête (percentiles par endpoint).
- Déploiement immuable avec **rollback** connu ; migrations testées up + down en CI.

## 4. Protection des données (RGPD)
- Minimisation des données ; chiffrement au repos (RDS, S3) et en transit (TLS).
- **Anonymisation** des apprenants (`anonymized_at`) pour le module de sensibilisation.
- Aucun secret / mot de passe / token / PII dans les logs (règle appliquée).
- Hébergement **UE** (AWS eu-west-3, Paris).

## 5. Assurance qualité sécurité (preuves)
- **~460 tests** exécutés à chaque commit, dont des **invariants de sécurité** : confusion de
  type de token JWT / algo `none`, blocage SSRF (metadata cloud, rebinding), 2FA (secret chiffré,
  anti-rejeu), chiffrement zero-knowledge du coffre, isolation multi-tenant.
- Gates de couverture verrouillés (ne peuvent que monter), gate 0-CVE, revue de code.
- Audits menés : IDOR (RAS), audit BDD, durcissement SSRF, en-têtes, DMARC.

## 6. Points en cours (transparence)
- **CSP** de la vitrine : en cours de durcissement (déploiement prudent en Report-Only d'abord,
  pour ne pas casser le rendu).
- **SPF `-all`** : durcissement prévu après une période de monitoring DMARC.
- **Redis multi-instance** (rate-limit + scheduler partagés) : prévu avant montée en charge
  horizontale ; sans objet à l'échelle actuelle (une instance).

---

*Document dérivé du code et de l'infrastructure réels. Complément technique : [ARCHITECTURE.md](ARCHITECTURE.md).*
