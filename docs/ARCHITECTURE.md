# Architecture technique — Cyber-Vault / Rocher Cybersécurité

> Documentation technique : architecture système (AWS), architecture applicative (couches),
> modèle de données (UML / entité-relation) et diagrammes de séquence des flux clés.
> Diagrammes en [Mermaid](https://mermaid.js.org) (rendu natif sur GitHub).

## Stack

| Couche | Technologies |
|---|---|
| **Frontend** | Angular 20 (standalone, signals), SSR/prerendering statique, Vitest, Playwright |
| **Backend** | FastAPI 0.138 · Starlette 1.3 · SQLAlchemy 2.0 async · Pydantic · PostgreSQL 17 |
| **Sécurité** | JWT (PyJWT) · 2FA TOTP (chiffré Fernet) · vault AES-GCM 256 zero-knowledge (clé PBKDF2) · anti-SSRF · slowapi · bcrypt |
| **Infra** | AWS ECS Fargate (1 vCPU / 2 Go) · RDS PostgreSQL (t4g.micro) · S3 · CloudFront · Route 53 · Secrets Manager · CloudWatch/SNS — région eu-west-3 |
| **CI/CD** | GitHub Actions → ECR → ECS ; gates couverture + 0 CVE (pip-audit / npm audit) |
| **Externes** | Stripe · Resend · Have I Been Pwned / LeakCheck · Sentry |

Volume : ~88 000 lignes de code hors tests (backend ~34k · frontend ~47k · scanner ~7k).

---

## 1. Architecture système (déploiement AWS)

Frontend statique servi par CloudFront/S3 ; API dynamique routée vers ECS Fargate derrière un ALB.
Le conteneur backend s'authentifie à AWS via un **rôle de tâche IAM** (`cybervault-ecs-task-role`).

```mermaid
flowchart TB
    U["👤 Utilisateur<br/>(navigateur)"]

    subgraph edge["Edge / CDN"]
      R53["Route 53<br/>rochercybersecurite.com"]
      CF["CloudFront E3DFNMKIHVBDO1<br/>TLS · cache · en-têtes sécurité"]
    end

    S3F["S3<br/>Frontend Angular<br/>(prerendered)"]

    subgraph vpc["VPC — eu-west-3 (Paris)"]
      ALB["ALB<br/>cybervault-alb"]
      subgraph ecs["ECS Fargate — cluster cybervault-prod"]
        API["Backend FastAPI · uvicorn<br/>1 vCPU / 2 Go · taskRole IAM"]
      end
      RDS[("RDS PostgreSQL 17<br/>t4g.micro · chiffré · backups 7j")]
    end

    SM["Secrets Manager<br/>SECRET_KEY · DATABASE_URL · Stripe…"]
    S3R["S3 livrables RSSI<br/>(privé · chiffré AES256)"]

    subgraph ext["Services externes"]
      STRIPE["Stripe<br/>paiement + webhook"]
      RESEND["Resend<br/>email transactionnel"]
      HIBP["HIBP / LeakCheck<br/>dark web"]
      SENTRY["Sentry<br/>erreurs"]
    end

    subgraph obs["Observabilité"]
      CW["CloudWatch<br/>5 alarmes"]
      SNS["SNS → email"]
    end

    subgraph cicd["CI/CD"]
      GH["GitHub Actions"]
      ECR["ECR<br/>image Docker"]
    end

    U --> R53 --> CF
    CF -->|"/*"| S3F
    CF -->|"/api/*"| ALB --> API
    API --> RDS
    API -->|secrets| SM
    API -->|presigned URL| S3R
    API --> STRIPE
    STRIPE -.->|webhook signé| API
    API --> RESEND
    API --> HIBP
    API --> SENTRY
    API --> CW --> SNS -.->|alerte| U
    GH --> ECR --> API
    GH -->|sync + invalidation| S3F
```

**Points clés :** TLS terminé par CloudFront ; en-têtes de sécurité posés au CDN (HSTS, X-Frame-Options, nosniff…) ; RDS chiffrée + backups 7 jours ; secrets jamais en clair (Secrets Manager) ; déploiement immuable via image ECR + `alembic upgrade head` avant bascule + `wait services-stable` (anti-rollback silencieux).

---

## 2. Architecture applicative (couches)

Séparation stricte des responsabilités côté backend ; chiffrement du coffre effectué **côté client**.

```mermaid
flowchart TB
    subgraph FE["Frontend — Angular 20 (standalone · signals · SSR prerender)"]
      direction TB
      FEfeat["features/ — modules fonctionnels<br/>vault · cyberscan · awareness · rssi · auth"]
      FEcore["core/ — guards (auth · crypto · rssi) · interceptor JWT · services globaux"]
      FEshared["shared/ — composants · pipes · directives"]
      VS["🔐 VaultStore<br/>chiffrement AES-GCM côté client"]
    end

    subgraph BE["Backend — FastAPI (couches strictes)"]
      direction TB
      EP["api/v1/endpoints/ — routing + validation Pydantic<br/>(jamais d'accès DB direct)"]
      SVC["services/ — logique métier<br/>(ne connaît pas le HTTP)"]
      MOD["models/ — SQLAlchemy ORM"]
      CORE["core/ — config · sécurité (JWT · SSRF · rate-limit) · db"]
    end

    DB[("PostgreSQL")]

    FEfeat --> FEcore --> FEshared
    VS -.-> FEfeat
    FE -->|"HTTPS JSON · Bearer JWT"| EP
    EP --> SVC --> MOD --> DB
    EP -.->|Depends| CORE
    SVC -.-> CORE
```

**Règles :** les endpoints délèguent toujours aux services (aucun accès DB direct) ; les services ignorent les schémas HTTP ; l'authentification passe par `Depends(get_current_user)` ; toute URL fournie par l'utilisateur passe par `assert_no_ssrf()`.

**Modules fonctionnels :** Scanner vulnérabilités · Dark Web · Phishing (simulation) · RSSI externalisé · Sensibilisation NIS2 (e-learning) · Code Scan · Conformité ISO 27001 / NIS2 · Vault zero-knowledge.

---

## 3. Modèle de données

51 entités réparties en domaines fonctionnels. Vue d'ensemble puis détail des deux plus structurants.

### 3.1 Carte des domaines

```mermaid
flowchart LR
  User["👤 Auth / User"]
  Bill["💳 Billing<br/>Plan · Subscription · Invoice · Quote"]
  Scan["🛡️ Scan sécurité<br/>Site · Scan · UrlScan · CodeScan"]
  Vault["🔐 Vault<br/>VaultItem (zero-knowledge)"]
  Aware["🎓 Awareness / e-learning<br/>Org · Learner · Program · Module · Enrollment · Certificate · Badge"]
  RSSI["🧑‍💼 RSSI externalisé<br/>Client · Action · Visite · Livrable"]
  Dark["🕵️ Dark Web<br/>Dossier · Target · BreachCatalog"]
  Phish["🎣 Phishing<br/>Campaign · Target"]
  Comp["📋 Conformité<br/>ISO 27001 · NIS2"]
  Mkt["📣 Marketing<br/>Newsletter · Blog · Contact · Booking"]

  User --> Bill
  User --> Scan
  User --> Vault
  User --> Aware
  User --> RSSI
  User --> Dark
  User --> Phish
  User --> Comp
  User --> Mkt
  Scan -.->|"Site.rssi_client_id"| RSSI
```

### 3.2 Cœur — Utilisateur, facturation, scan, vault

```mermaid
erDiagram
  USER ||--o{ REFRESH_TOKEN : "a"
  USER ||--o{ PASSWORD_RESET_TOKEN : "a"
  USER ||--o{ SUBSCRIPTION : "souscrit"
  PLAN ||--o{ SUBSCRIPTION : "propose"
  USER ||--o{ SITE : "possède"
  SITE ||--o{ SCAN : "génère"
  USER ||--o{ VAULT_ITEM : "possède"
  USER ||--o{ NOTIFICATION : "reçoit"
  USER ||--o{ INVOICE : "facturé"
  USER ||--o{ QUOTE : "devis"
  RSSI_CLIENT ||--o{ SITE : "supervise"

  USER {
    int id PK
    string email UK
    string hashed_password
    bytes crypto_salt
    string totp_secret "chiffré Fernet"
    bool totp_enabled
    int failed_login_attempts
    datetime locked_until
    bool is_rssi_consultant
  }
  SUBSCRIPTION {
    int id PK
    int user_id FK
    int plan_id FK
    string stripe_subscription_id
    string status
    int extra_sites
  }
  PLAN {
    int id PK
    string name UK
    int price_eur "centimes"
    int max_sites
    int scan_interval_days
  }
  SITE {
    int id PK
    int user_id FK
    int rssi_client_id FK "nullable"
    string url
    bool is_active
  }
  SCAN {
    int id PK
    int site_id FK
    string status
    string overall_status "OK/WARNING/CRITICAL"
    text results_json
  }
  VAULT_ITEM {
    int id PK
    int owner_id FK
    bytes password_encrypted "AES-GCM (opaque)"
    bytes title_encrypted
    bytes notes_encrypted
  }
```

### 3.3 Awareness / e-learning (domaine le plus riche)

Contient l'unique relation **N-N** (Learner ↔ Badge via l'objet d'association `AwarenessLearnerBadge`)
et une relation **1-1** (Enrollment ↔ Certificate).

```mermaid
erDiagram
  AWARENESS_ORGANIZATION ||--o{ AWARENESS_LEARNER : "regroupe"
  AWARENESS_ORGANIZATION ||--o{ AWARENESS_ENROLLMENT : "porte"
  AWARENESS_PROGRAM ||--o{ AWARENESS_MODULE : "contient"
  AWARENESS_PROGRAM ||--o{ AWARENESS_ENROLLMENT : "cible"
  AWARENESS_LEARNER ||--o{ AWARENESS_ENROLLMENT : "inscrit"
  AWARENESS_ENROLLMENT ||--o{ AWARENESS_PROGRESS : "suit"
  AWARENESS_MODULE ||--o{ AWARENESS_PROGRESS : "mesuré par"
  AWARENESS_LEARNER ||--o{ AWARENESS_QUIZ_ATTEMPT : "tente"
  AWARENESS_MODULE ||--o{ AWARENESS_QUIZ_ATTEMPT : "évalué par"
  AWARENESS_ENROLLMENT ||--|| AWARENESS_CERTIFICATE : "délivre (1-1)"
  AWARENESS_LEARNER ||--o{ AWARENESS_LEARNER_BADGE : "gagne"
  AWARENESS_BADGE ||--o{ AWARENESS_LEARNER_BADGE : "attribué à"

  AWARENESS_LEARNER {
    int id PK
    int organization_id FK
    string email
    datetime anonymized_at "RGPD"
  }
  AWARENESS_ENROLLMENT {
    int id PK
    int learner_id FK
    int program_id FK
    int organization_id FK
    float completion_pct
    int xp_earned
  }
  AWARENESS_CERTIFICATE {
    int id PK
    int enrollment_id FK "UK (1-1)"
    string public_id UK
    string signature_hash
    string pdf_s3_key
  }
  AWARENESS_LEARNER_BADGE {
    int learner_id FK
    int badge_id FK
    datetime earned_at
  }
```

> **11 énumérations** (`enums.py`) : ScanStatus, SubscriptionStatus, EnrollmentStatus, ProgressStatus,
> DossierStatus, ComplianceStatus, QuoteStatus, InvoiceStatus, CampaignStatus, FindingStatusEnum, CollabStatus.

---

## 4. Diagrammes de séquence (flux clés)

### 4.1 Authentification (login + 2FA + JWT)

```mermaid
sequenceDiagram
  actor U as Utilisateur
  participant FE as Frontend
  participant API as FastAPI /auth
  participant DB as PostgreSQL

  U->>FE: email + mot de passe
  FE->>API: POST /auth/login
  API->>DB: SELECT user
  Note over API: contrôle locked_until / tentatives
  API->>API: verify_password (bcrypt, threadpool)
  alt mauvais mot de passe
    API->>DB: failed_login_attempts++ (lockout si seuil)
    API-->>FE: 401
  else 2FA activée
    API-->>FE: {requires_2fa: true}
    U->>FE: code TOTP
    FE->>API: POST /auth/login (+ totp)
    API->>API: vérifie TOTP (secret déchiffré Fernet)
  end
  API->>API: create_access_token (JWT) + refresh
  API->>DB: stocke RefreshToken
  API-->>FE: access_token (JSON) + refresh (cookie httpOnly)
```

### 4.2 Vault zero-knowledge (chiffrement côté client)

```mermaid
sequenceDiagram
  actor U as Utilisateur
  participant FE as VaultStore (navigateur)
  participant API as FastAPI /vault
  participant DB as PostgreSQL

  Note over FE: clé dérivée (PBKDF2) du mot de passe maître + crypto_salt<br/>(jamais transmise au serveur)
  U->>FE: saisir un item (mdp, notes…)
  FE->>FE: chiffre AES-GCM (title, username, url, notes, password)
  FE->>API: POST /vault (blobs chiffrés)
  API->>DB: stocke des blobs OPAQUES
  Note over API,DB: le backend ne peut PAS déchiffrer
  U->>FE: ouvrir le coffre
  FE->>API: GET /vault
  API->>DB: SELECT WHERE owner_id (indexé)
  API-->>FE: blobs chiffrés
  FE->>FE: déchiffre localement avec la clé
```

### 4.3 Abonnement Stripe (checkout + webhook)

```mermaid
sequenceDiagram
  actor U as Utilisateur
  participant FE as Frontend
  participant API as FastAPI
  participant ST as Stripe
  participant DB as PostgreSQL

  U->>FE: choisir un plan
  FE->>API: POST /subscriptions/checkout/{plan}
  API->>ST: crée Checkout Session
  ST-->>FE: URL de paiement hébergée
  U->>ST: paie (page Stripe)
  ST-->>API: webhook checkout.session.completed (signé)
  API->>API: vérifie signature + idempotence (ProcessedStripeEvent)
  API->>DB: Subscription → active (plan, période, ids Stripe)
  ST-->>FE: redirection succès
```

### 4.4 Scan de sécurité (déclenchement + anti-SSRF)

```mermaid
sequenceDiagram
  actor U as Utilisateur
  participant API as FastAPI /scans
  participant DB as PostgreSQL
  participant SC as Scanner (cyber-scanner)

  U->>API: POST /scans/trigger/{site}
  API->>API: assert_no_ssrf(site.url)
  API->>DB: contrôle quota (plan) + verrou anti-course
  API->>DB: crée Scan (pending)
  API-->>U: 202 Accepted
  API->>SC: run_scan (tâche de fond)
  SC->>SC: modules — SSL · en-têtes · DNS · IP/DNSBL · WAF · CMS…
  SC->>DB: Scan → done (overall_status, results_json, PDF)
```

---

*Diagrammes générés depuis le code source (modèles, endpoints, services).
Régénérer les images PNG/SVG : `bash docs/render-diagrams.sh` (nécessite `@mermaid-js/mermaid-cli`).
Voir aussi [DEPLOY.md](DEPLOY.md) et [SCALING.md](SCALING.md).*
