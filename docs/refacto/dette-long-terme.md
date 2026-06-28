# Dette technique CyberScan — refacto long terme

> **Pour qui** : toi, dans 3-6 mois, quand tu auras des clients réels et que tu reprendras le code.
> **Pour quoi** : tout ce qui n'a pas été fait avant le gel parce que **non visible commercialement**.
> **À conserver dans** `docs/refacto/dette-long-terme.md` du repo.
> **À relire** au retour de prospection, avant de reprendre le code.

---

## Avant-propos : pourquoi ce document existe

Avant la prospection, tu as gelé le site après l'audit `audit-final-pre-gel.md`. Tu as corrigé :
- les bugs visibles côté client (prix, Stripe, mentions légales)
- les risques de production (CVE, monitoring, sauvegardes)
- la documentation et les tests des parcours critiques

**Tout le reste**, c'est-à-dire **la dette structurelle**, a été repoussée à plus tard. Ce document liste ce "plus tard".

**Règle d'or pour la suite** : ne pas traiter cette dette tant que tu n'as pas validé que ton modèle économique marche. Refactor un produit qui ne se vend pas = perte de temps pure. Refactor un produit qui marche = investissement.

**Critère pour lancer ce refacto long terme** : tu as au moins **10 clients payants** et tu vois **clairement** quels modules ils utilisent vs lesquels sont morts. Avant ça, tu sais pas où couper.

---

## Sommaire

1. [Décisions stratégiques à prendre avant de refactorer](#decisions)
2. [Niveau A — Réduction du périmètre](#niveau-a)
3. [Niveau B — Architecture transactionnelle](#niveau-b)
4. [Niveau C — Découpage des monolithes](#niveau-c)
5. [Niveau D — Sécurité du vault (zero-knowledge)](#niveau-d)
6. [Niveau E — Frontend : memory leaks, bundle, SSR](#niveau-e)
7. [Niveau F — Infrastructure et exploitation](#niveau-f)
8. [Niveau G — Qualité de code et CI](#niveau-g)
9. [Niveau H — Modèles God-objects](#niveau-h)
10. [Niveau I — Tests](#niveau-i)
11. [Planning sur 9-12 mois](#planning)
12. [Métriques de progression](#metriques)

---

<a name="decisions"></a>
## 1. Décisions stratégiques à prendre avant de refactorer

Avant de commencer le refacto long terme, tu **dois trancher** sur 3 questions. Ne pas refactorer sans réponse claire à chacune.

### Décision 1 — Quels modules tu gardes vraiment ?

À ton retour, regarde les **vrais usages** dans tes données (Plausible + logs + DB) :

```sql
-- Modules utilisés (proxy : tables remplies)
SELECT 'scans', COUNT(*) FROM scans WHERE finished_at > now() - interval '90 days'
UNION ALL SELECT 'rssi_clients', COUNT(*) FROM rssi_clients WHERE created_at > now() - interval '90 days'
UNION ALL SELECT 'phishing_campaigns', COUNT(*) FROM phishing_campaigns WHERE created_at > now() - interval '90 days'
UNION ALL SELECT 'awareness_enrollments', COUNT(*) FROM awareness_enrollments WHERE created_at > now() - interval '90 days'
UNION ALL SELECT 'darkweb_dossiers', COUNT(*) FROM darkweb_dossiers WHERE created_at > now() - interval '90 days'
UNION ALL SELECT 'vault_items', COUNT(*) FROM vault_items
UNION ALL SELECT 'iso27001_assessments', COUNT(*) FROM iso27001_assessments
UNION ALL SELECT 'nis2_assessments', COUNT(*) FROM nis2_assessments
UNION ALL SELECT 'code_scans', COUNT(*) FROM code_scans WHERE created_at > now() - interval '90 days'
UNION ALL SELECT 'pca_documents', COUNT(*) FROM pca_documents 2>/dev/null
ORDER BY 2 DESC;
```

Les modules à **0 utilisation sur 90 jours** = candidats à supprimer.

**Tu as actuellement 10+ modules. Une PME solo ne peut maintenir que 3-4 produits.** Décision honnête à prendre.

### Décision 2 — Cyber-Vault : on garde ou on tue ?

Le vault occupe 3% du code mais maintient la promesse "zero-knowledge" dans le README. Aujourd'hui :
- title/username/url/notes en clair en DB
- email utilisé comme salt PBKDF2
- Tokens en localStorage (attaquable XSS)

Trois options :

**A. Tu garde et tu finis le zero-knowledge** (gros chantier, ~2 semaines)
- Migration colonnes en clair → chiffrées
- Vrai salt cryptographique
- Tests sentinels
- Migration des données existantes (script TS côté client à la première connexion)

**B. Tu garde mais tu retires la promesse "zero-knowledge"**
- Renommage README et marketing
- "Stockage chiffré des mots de passe" plutôt que "zero-knowledge"
- Pas de refacto à faire
- Honnêteté vis-à-vis des prospects

**C. Tu tues le module vault**
- Supprime les routes `/vault/*`, la table `vault_items`, le composant frontend
- Migration de suppression
- Ne maintiens plus de promesse irréaliste pour un dev solo
- Tu te concentres sur les modules qui se vendent réellement

**Recommandation honnête** : option **C** si tu n'as aucun client qui utilise le vault après 3 mois de prospection. Option **B** sinon. Option A uniquement si un gros client paie pour ça.

### Décision 3 — Le `cyber-scanner/` standalone : intégration ou suppression ?

Le module `cyber-scanner/` (11 000 lignes Python) est physiquement séparé du backend, importé via `sys.path.insert(0, ...)`. Deux usages possibles :
- En script CLI standalone
- Réutilisé par le backend via cet hack

Options :

**A. Le rendre vraiment indépendant** (CLI commercial séparé)
- Packager comme un vrai package pip
- Le vendre comme un produit séparé ("CyberScan CLI" — outil ligne de commande pour pentesters)
- Supprimer la dépendance backend → réécrire les services scan

**B. L'intégrer proprement au backend**
- Déplacer le code dans `backend/app/scanner/`
- Supprimer la manipulation `sys.path`
- Simplifier le déploiement Docker

**C. Statu quo** = laisser comme aujourd'hui

Recommandation : **B** sauf si un client achète le CLI standalone (option A).

---

<a name="niveau-a"></a>
## 2. Niveau A — Réduction du périmètre (priorité maximale)

**Le plus gros gain de qualité possible** : supprimer du code mort.

### A1 — Supprimer les modules à 0 client (4-8h selon ampleur)

Une fois la décision 1 prise, supprimer agressivement :

```
Pour chaque module à supprimer :
1. Désactiver les routes frontend (cyberscan.routes.ts)
2. Désactiver les endpoints backend (api/v1/router.py)
3. Migration Alembic : drop des tables associées
4. Suppression des modèles SQLAlchemy
5. Suppression des services
6. Suppression des composants Angular
7. Suppression des tests
8. Nettoyage navbar / liens / sitemap
```

**Estimation par module supprimé** : 4-8h.

**Candidats probables** vu ton ICP (PME/agences via CCI) :
- Awareness NIS2 (10 modèles + 17 modules e-learning) si non vendu après 3 mois
- API REST si non vendu
- Vault si non utilisé
- PCA si non utilisé

### A2 — Supprimer le code mort identifié (2h)

Dette technique repérée mais jamais nettoyée :

**Colonnes mortes `gophish_*` dans phishing_campaigns**

```python
# 4 colonnes jamais utilisées que par leur déclaration
gophish_campaign_id: Mapped[int | None]
gophish_group_id: Mapped[int | None]
gophish_template_id: Mapped[int | None]
gophish_page_id: Mapped[int | None]
```

Migration de suppression :

```python
def upgrade():
    op.drop_column('phishing_campaigns', 'gophish_campaign_id')
    op.drop_column('phishing_campaigns', 'gophish_group_id')
    op.drop_column('phishing_campaigns', 'gophish_template_id')
    op.drop_column('phishing_campaigns', 'gophish_page_id')
```

**Migration fantôme `5e6403bce97c_add_vault_items.py`**

`upgrade=pass, downgrade=pass`. Pollution du DAG Alembic. À retirer.

**Dépendances frontend dead-weight**

```bash
cd frontend
npm uninstall animate.css aos material-icons @types/aos
```

0 occurrence dans le code source, 200-400 Ko économisés sur le bundle.

### A3 — Nettoyer le scope du repo (1h)

8 fichiers `.txt` à la racine avec encoding cassé. À déplacer dans `docs/notes/` ou supprimer.

Le repo doit être propre pour qu'un futur freelance (ou toi-même) puisse s'y retrouver.

---

<a name="niveau-b"></a>
## 3. Niveau B — Architecture transactionnelle (12h)

### B1 — Fix du double-commit dans `get_db()` (6h)

Bug architectural identifié dans plusieurs audits précédents, jamais corrigé :

```python
# core/database.py
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()  # ← commit auto en fin de requête
        except Exception:
            await session.rollback()
            raise
```

**Mais 18+ endpoints font aussi `await db.commit()` manuellement** → double-commit sur toutes les mutations. Inconsistance flush vs commit (25 vs 64+ aujourd'hui).

**Fix** : retirer le commit automatique de `get_db()` et obliger chaque endpoint à commit explicitement.

```python
# core/database.py (corrigé)
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        # pas de commit auto
```

Puis migration des endpoints : remplacer `flush` par `commit` partout où il y a mutation. 1 PR par module.

### B2 — Pool de connections DB configuré (1h)

```python
# core/database.py
engine = create_async_engine(settings.DATABASE_URL, echo=settings.APP_ENV == "development")
```

Pas de pool size configuré → défaut 5 connexions + 10 overflow. Sur RDS t4g.micro, c'est trop bas dès qu'il y a du trafic.

```python
engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=AsyncAdaptedQueuePool,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
    echo_pool=False,
)
```

### B3 — Casser les imports circulaires (5h)

**56 imports lazy** (`from app.X import Y` dans des fonctions) pour contourner des cycles d'imports. Commentaire littéral dans le code : `"to avoid circular"`.

Liste des cycles identifiés (audit précédent) :
- `darkweb_dossier_service.py ↔ email_service.py`
- `scan_service.py ↔ email_service.py`
- `rssi.py ↔ rssi_report_pdf.py`
- `nis2.py ↔ brand_profile`

**Solution architecturale** : créer `app/notifications/` qui centralise les envois externes (email, sms, webhook). Les services métier émettent des events, le module notifications les consomme.

```
app/
  services/         # logique métier pure
    scan_service.py
    darkweb_service.py
  notifications/    # orchestration externe
    email.py
    dispatch.py     # event bus : scan.completed → email
```

---

<a name="niveau-c"></a>
## 4. Niveau C — Découpage des monolithes (20h)

### C1 — Backend : fichiers > 800 lignes (12h)

Liste actuelle :

| Fichier | Lignes | Action |
|---|---|---|
| `services/code_scan_service.py` | **1185** | 5 fichiers : `runner`, `parser`, `reporter`, `remediation`, `cli` |
| `api/v1/endpoints/awareness.py` | **1028** | 6 fichiers : `programs`, `enrollments`, `learners`, `progress`, `quizzes`, `badges` |
| `services/phishing_templates.py` | 953 | Garder mais sortir les scenarios dans des JSON séparés |
| `services/email_service.py` | 876 | 1 fichier par type d'email (welcome, reset, scan_report, invoice, etc.) |
| `services/darkweb_dossier_service.py` | 826 | 3 fichiers : `ingestion`, `enrichment`, `reporting` |
| `services/pdf_brand.py` | 805 | Factoriser en `BasePdfBuilder` réutilisable |
| `api/v1/endpoints/rssi.py` (vu précédemment) | ~1200 | Sous-package `rssi/` avec 5 modules |

**Méthode** : 1 PR par fichier découpé. Tests verts à chaque étape.

### C2 — Frontend : composants > 500 lignes TS ou 800 lignes HTML (8h)

| Composant | LOC TS | LOC HTML | Découpage |
|---|---|---|---|
| `dashboard.component` | 744 | **1575** | Sidebar + SitesGrid + RecentScans + Stats + AlertsBanner |
| `landing.component` | ~600 | **1336** | Hero + FeaturesGrid + Pricing + Testimonials + FAQ + CTA |
| `client-detail.component` | **925** | 1193 | Header + InfoPanel + ActionsTable + DeliverablesList + ActivityFeed |
| `awareness-module.component` | 722 | ~ | Header + ContentViewer + QuizPanel + Progress + Navigation |
| `awareness-org-detail.component` | 690 | ~ | LearnersList + ProgramsList + ProgressDashboard + Settings |
| `vault-dashboard.component` | 571 | 664 | VaultList + VaultItemForm + Search + MasterPasswordPrompt |
| `profile.component` | ~ | 944 | TabsContainer + sous-composants par tab |

**Pattern d'extraction** :

```typescript
// Avant : dashboard.component.ts (744 lignes)
@Component({...})
export class DashboardComponent {
  // 50 propriétés
  // 30 méthodes
  // 1 template HTML de 1575 lignes
}

// Après : dashboard.component.ts (150 lignes)
@Component({
  imports: [SidebarComponent, SitesGridComponent, RecentScansComponent, StatsComponent],
  template: `
    <app-sidebar [activeRoute]="route()" />
    <app-sites-grid [sites]="sites()" (siteClick)="onSiteClick($event)" />
    <app-recent-scans [scans]="recentScans()" />
    <app-stats [data]="statsData()" />
  `,
})
export class DashboardComponent {
  // juste l'orchestration : signals, computed, peu de méthodes
}
```

Bénéfice : chaque sous-composant testable indépendamment + lazy loading possible + réutilisation.

---

<a name="niveau-d"></a>
## 5. Niveau D — Sécurité du vault (conditionnel) (15h)

**À ne faire QUE si tu as gardé le vault avec la promesse zero-knowledge** (décision 2 = A).

Sinon, sauter cette section.

### D1 — Vrai salt cryptographique (4h)

Aujourd'hui : email utilisé comme salt PBKDF2. Mieux que rien mais pas un vrai salt.

```python
# Migration : ajouter colonne crypto_salt à users
def upgrade():
    op.add_column('users', sa.Column('crypto_salt', sa.LargeBinary, nullable=True))

    connection = op.get_bind()
    users = connection.execute(sa.text("SELECT id FROM users WHERE crypto_salt IS NULL")).fetchall()
    for user in users:
        salt = secrets.token_bytes(32)
        connection.execute(
            sa.text("UPDATE users SET crypto_salt = :salt WHERE id = :id"),
            {"salt": salt, "id": user.id}
        )

    op.alter_column('users', 'crypto_salt', nullable=False)
```

Backend retourne le salt au login. Frontend l'utilise dans `crypto.service.ts`.

### D2 — Chiffrer tous les champs sensibles du vault (8h)

Aujourd'hui en clair en DB : `title`, `username`, `url`, `notes`. Un dump révèle quels services chaque user utilise.

```python
# Migration : renommer en _plain_legacy et ajouter colonnes _encrypted
def upgrade():
    op.alter_column('vault_items', 'title', new_column_name='title_plain_legacy')
    op.alter_column('vault_items', 'username', new_column_name='username_plain_legacy')
    op.alter_column('vault_items', 'url', new_column_name='url_plain_legacy')
    op.alter_column('vault_items', 'notes', new_column_name='notes_plain_legacy')

    op.add_column('vault_items', sa.Column('title_encrypted', sa.Text))
    op.add_column('vault_items', sa.Column('username_encrypted', sa.Text))
    op.add_column('vault_items', sa.Column('url_encrypted', sa.Text))
    op.add_column('vault_items', sa.Column('notes_encrypted', sa.Text))
```

Migration des données existantes : script TS côté client qui s'exécute à la première connexion post-déploiement, déchiffre l'ancien, chiffre le nouveau, marque le user comme migré.

### D3 — Test e2e sentinel (3h)

```typescript
test('aucun champ vault en clair ne traverse l\'API', async ({ page }) => {
  const SENTINEL_TITLE = 'CANARY_TITLE_DO_NOT_LEAK_2026';
  const SENTINEL_PWD = 'CANARY_PWD_DO_NOT_LEAK_2026';
  const SENTINEL_NOTE = 'CANARY_NOTE_DO_NOT_LEAK_2026';

  const requests: string[] = [];
  page.on('request', req => {
    if (req.url().includes('/api/v1/vault')) {
      requests.push(req.postData() || '');
    }
  });

  await createAndLogin(page);
  await page.goto('/vault');
  // ... créer une entrée avec les sentinels

  for (const body of requests) {
    expect(body).not.toContain(SENTINEL_TITLE);
    expect(body).not.toContain(SENTINEL_PWD);
    expect(body).not.toContain(SENTINEL_NOTE);
  }
});
```

Garde-fou contre toute régression future.

### D4 — Tokens : localStorage → httpOnly cookies (4h)

Aujourd'hui XSS = jeton volé. Pour un produit cyber, gênant.

```python
# Backend : login retourne le refresh_token en cookie httpOnly
@router.post("/login")
async def login(response: Response, ...):
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh,
        httponly=True,
        secure=settings.APP_ENV == "production",
        samesite="strict",
        max_age=30 * 24 * 3600,
        path="/api/v1/auth",
    )
    return {"access_token": access_token}  # seulement l'access
```

Frontend : access_token en mémoire JS, refresh_token jamais lu par le JS.

---

<a name="niveau-e"></a>
## 6. Niveau E — Frontend : memory leaks, bundle, SSR (16h)

### E1 — Memory leaks Observable (6h)

**236 `.subscribe()` vs 13 `takeUntilDestroyed`**. Memory leaks probables sur les SPA longue durée.

Migration pattern :

```typescript
// Avant
ngOnInit() {
  this.service.getData().subscribe(data => this.data = data);
}

// Après (Angular 16+)
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

private destroyRef = inject(DestroyRef);

ngOnInit() {
  this.service.getData()
    .pipe(takeUntilDestroyed(this.destroyRef))
    .subscribe(data => this.data = data);
}

// Encore mieux : async pipe dans le template, pas de subscribe manuel
```

À faire **module par module**. Pas en une seule PR géante.

### E2 — Audit imports `CommonModule` inutiles (4h)

Tu utilises massivement `@if`/`@for` (754 occurrences) vs `*ngIf`/`*ngFor` (1 seule). Donc `CommonModule` (100+ imports) est inutile dans la majorité des composants.

Remplacer par imports précis :

```typescript
// Avant
import { CommonModule } from '@angular/common';
@Component({ imports: [CommonModule], ... })

// Après
import { AsyncPipe, DatePipe } from '@angular/common';
@Component({ imports: [AsyncPipe, DatePipe], ... })
```

Gain : tree-shaking optimal, ~50-100 Ko bundle.

### E3 — SSR / prerendering pages statiques (8h)

Aujourd'hui Angular standalone client-side uniquement. Pour un site qui vend du SEO d'audit, c'est ironique.

**Action 1 — Prerendering** des pages statiques :

```bash
ng add @angular/ssr
```

```json
// angular.json
"prerender": {
  "discoverRoutes": true,
  "routes": [
    "/cyberscan",
    "/cyberscan/audit-pme",
    "/cyberscan/scan-gratuit",
    "/cyberscan/bonnes-pratiques",
    "/cyberscan/nis2",
    "/cyberscan/iso27001",
    "/cyberscan/cgu",
    "/cyberscan/politique-confidentialite",
    "/cyberscan/mentions-legales",
    "/cyberscan/blog"
  ]
}
```

**Action 2 — SSR complet** pour le blog (contenu dynamique).

Bénéfice : Google indexe en HTML statique, Lighthouse +30 points, First Contentful Paint divisé par 5.

---

<a name="niveau-f"></a>
## 7. Niveau F — Infrastructure (12h)

### F1 — Scheduler persistant (4h)

APScheduler intra-process : si crash → jobs perdus. Si 2 instances ECS → double exécution.

**Option 1 — Minimal** : APScheduler + Redis jobstore.

```python
from apscheduler.jobstores.redis import RedisJobStore

scheduler = AsyncIOScheduler(
    jobstores={'default': RedisJobStore(host='redis', port=6379, db=1)},
)
```

**Option 2 — Robuste** : passage à **Arq** (compatible asyncio, Redis-backed).

```python
class WorkerSettings:
    functions = [run_scan_task, send_email_task, generate_pdf_task]
    redis_settings = RedisSettings(host="redis")
```

Démarrage : `arq workers.WorkerSettings`. Robuste, idempotent, scalable.

### F2 — Dockerfile multi-stage (4h)

Image actuelle ~1.5-2 Go (inclut nodejs, npm, nmap, trivy, grype, gitleaks, hadolint, etc.).

```dockerfile
# Image 1 : backend-api (~150 Mo)
FROM python:3.12-slim AS builder
WORKDIR /app
COPY backend/requirements.prod.txt .
RUN pip install --user --no-cache-dir -r requirements.prod.txt

FROM python:3.12-slim
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
WORKDIR /app
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini .

RUN useradd -r -u 1001 -s /bin/false appuser
USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Image 2 : `code-scanner-worker` séparée (avec tous les outils), lancée à la demande via Arq, pas dans le runtime API.

### F3 — Migrations Alembic en job ECS séparé (2h)

Aujourd'hui `alembic upgrade head && uvicorn ...` au démarrage du container. Race condition si 2 instances.

Solution : job one-shot ECS dédié, déclenché par la CI **avant** le déploiement.

```yaml
# .github/workflows/deploy.yml
- name: Run migrations
  run: |
    aws ecs run-task --task-definition cyberscan-migrate \
      --launch-type FARGATE \
      --wait-for-stopped

- name: Deploy API
  run: aws ecs update-service --service cyberscan-api ...
```

### F4 — Outils dev hors requirements.prod (2h)

Si pas déjà fait : sortir bandit, semgrep, checkov, detect-secrets de `requirements.prod.txt`. Ces outils ont leurs propres CVE et n'ont rien à faire en runtime.

Créer `requirements-dev.txt` séparé.

---

<a name="niveau-g"></a>
## 8. Niveau G — Qualité de code et CI (8h)

### G1 — Mypy + ruff dans CI (3h)

Aucun type-checking statique actuellement. Le code utilise massivement `Mapped[]`, `int | None`, etc. mais rien ne vérifie.

```toml
# backend/pyproject.toml
[tool.mypy]
python_version = "3.12"
strict = false
warn_redundant_casts = true
warn_unused_ignores = true
disallow_untyped_defs = false  # à durcir progressivement
plugins = ["pydantic.mypy", "sqlalchemy.ext.mypy.plugin"]

[[tool.mypy.overrides]]
module = "tests.*"
ignore_errors = true

[tool.ruff]
line-length = 100
target-version = "py312"
select = ["E", "F", "I", "B", "UP", "ASYNC"]
```

CI :

```yaml
- name: Type check
  run: mypy app
  working-directory: backend

- name: Lint
  run: ruff check app
  working-directory: backend
```

### G2 — Test cohérence prix Stripe ↔ DB ↔ frontend (2h)

Garde-fou contre divergence Stripe ↔ frontend (cf audit pricing T11).

```python
@pytest.mark.skipif(not os.getenv("STRIPE_SECRET_KEY"), reason="No Stripe key")
async def test_plan_prices_match_stripe():
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

    async with AsyncSessionLocal() as db:
        plans = (await db.execute(
            select(Plan).where(Plan.is_active, Plan.stripe_price_id != "")
        )).scalars().all()

    for plan in plans:
        stripe_price = stripe.Price.retrieve(plan.stripe_price_id)
        assert stripe_price.unit_amount == plan.price_eur, (
            f"Plan {plan.name}: DB={plan.price_eur} vs Stripe={stripe_price.unit_amount}"
        )
        assert stripe_price.tax_behavior == "exclusive"
```

À exécuter en CI nightly avec une clé Stripe test.

### G3 — Réduire les `except Exception` (3h)

**61 occurrences** dont plusieurs `except Exception: pass`. Pour un produit cyber, c'est gênant.

Méthode :

```python
# Avant
try:
    do_something()
except Exception:
    pass  # silent swallow

# Après
try:
    do_something()
except SpecificException as exc:  # type concret
    logger.warning("Operation X failed", exc_info=exc)
except Exception as exc:
    # filet de sécurité, mais on remonte à Sentry
    logger.exception("Unexpected error in X")
    sentry_sdk.capture_exception(exc)
```

Pour chaque cas, identifier la vraie exception attendue (TimeoutError, ConnectionError, ValidationError…) plutôt que catch global.

---

<a name="niveau-h"></a>
## 9. Niveau H — Modèles God-objects (10h)

Modèles avec trop de colonnes (= mélangent plusieurs préoccupations) :

| Modèle | Colonnes | Découpage proposé |
|---|---|---|
| `phishing.py` (PhishingCampaign) | **42** | Identity + Stats + Timing + Config |
| `darkweb_dossier.py` | 29 | Dossier + EnrichmentResult + ExportData |
| `awareness_module.py` | 21 | Module + ContentReferences |
| `user.py` | 19 | User + NotificationPreferences |
| `quote.py` | 19 | Quote + ClientInfo |
| `rssi_client.py` | 17 | Client + Configuration |
| `invoice.py` | 16 | Invoice + LineItems (déjà 1:N) |

### H1 — Découpage PhishingCampaign (4h)

42 colonnes, 5 préoccupations distinctes :

```python
class PhishingCampaign(Base):
    """Identity + config"""
    id, user_id, name, status, plan_tier
    domain, lookalike_domain, scenario_keys
    cgu_accepted, created_at, updated_at

class PhishingCampaignStats(Base):
    """Stats agrégées (1:1)"""
    campaign_id (FK)
    targets_count, emails_sent
    opened_count, clicked_count, submitted_count
    last_synced_at

class PhishingCampaignTiming(Base):
    """Cycle de vie (1:1)"""
    campaign_id (FK)
    scheduled_at, started_at, finished_at
```

Bénéfice : updates de stats fréquents ne touchent pas la table principale. Moins de verrous.

### H2 — JSON stocké en TEXT → JSONB (3h)

Plusieurs modèles utilisent `Text` pour stocker du JSON :
- `rssi_client.extra_data`
- `scan.results_json`
- `blog_post.tags`
- `darkweb_dossier.top_sources_json`

PostgreSQL a `JSONB` natif (indexable, queryable, validé). Migration :

```python
from sqlalchemy.dialects.postgresql import JSONB

# Migration
def upgrade():
    op.execute("ALTER TABLE blog_posts ALTER COLUMN tags TYPE JSONB USING tags::JSONB")
    op.create_index('ix_blog_posts_tags', 'blog_posts', ['tags'], postgresql_using='gin')
```

Recherche par tag devient instantanée.

### H3 — Enum pour les status stringly-typed (3h)

96+ occurrences de `"compliant"`, `"partial"`, `"non_compliant"`, etc. en strings dupliquées. À remplacer par Enum :

```python
from enum import StrEnum

class ComplianceStatus(StrEnum):
    COMPLIANT = "compliant"
    PARTIAL = "partial"
    NON_COMPLIANT = "non_compliant"
    NOT_APPLICABLE = "na"

class CampaignStatus(StrEnum):
    DRAFT = "draft"
    PENDING_VERIFICATION = "pending_verification"
    READY = "ready"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
```

Si tu renommes un jour `"non_compliant"` en `"non_conforme"`, 1 changement au lieu de 96.

---

<a name="niveau-i"></a>
## 10. Niveau I — Tests (10h)

### I1 — Testcontainers PostgreSQL (3h)

Aujourd'hui tests sur SQLite, prod sur PostgreSQL. Divergences silencieuses (JSON vs JSONB, locks, dates, contraintes).

```python
# conftest.py
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:17-alpine") as postgres:
        yield postgres

@pytest_asyncio.fixture
async def test_engine(postgres_container):
    url = postgres_container.get_connection_url().replace(
        "postgresql://", "postgresql+asyncpg://"
    )
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()
```

Tests 5-10× plus lents mais ils testent la **vraie DB**.

### I2 — Tests paramétrés sur les edge cases (4h)

Tu as ~7 `@pytest.mark.parametrize` sur 93 fichiers de test. Beaucoup de tests "happy path × 1". Ajouter du paramétrage sur les inputs critiques :

```python
@pytest.mark.parametrize("category,expected", [
    ("invalid_cat", "login"),
    ("", "login"),
    (None, "login"),
    ("LOGIN", "login"),
    ("a" * 100, "login"),
    ("<script>alert(1)</script>", "login"),
])
def test_vault_category_validation(category, expected):
    item = VaultItemCreate(title="Test", password_encrypted="enc", category=category)
    assert item.category == expected
```

### I3 — Tests cycle migration Alembic (2h)

Aucun test ne vérifie qu'un `upgrade head` suivi de `downgrade base` fonctionne. Risque : déploiement qui casse la prod si une migration récente a un downgrade buggué.

```python
# tests/test_migrations_cycle.py
def test_full_upgrade_downgrade_cycle(postgres_container):
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", postgres_container.get_connection_url())

    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")
```

### I4 — Tests E2E supplémentaires (1h)

Compléter la suite E2E avec :
- Test reset password
- Test 2FA setup + login
- Test changement de plan (upgrade Starter → Pro)
- Test export RGPD
- Test rate limiting (429 après N tentatives)

---

<a name="planning"></a>
## 11. Planning sur 9-12 mois

Hypothèse : tu reviens avec ~10 clients après 3-6 mois de prospection. Tu reprends le code 1 jour par semaine, le reste en commercial.

### Phase 1 (mois 1) — Décisions et nettoyage du périmètre

| Sem. | Tâche | Heures |
|---|---|---|
| 1 | Audit usage modules + décisions stratégiques | 4 |
| 2-3 | Niveau A : suppression modules non utilisés | 8 |
| 4 | Niveau A : nettoyage code mort + .txt | 3 |

**Total : ~15h** sur 4 semaines.

### Phase 2 (mois 2-3) — Architecture transactionnelle + sécurité vault

| Sem. | Tâche | Heures |
|---|---|---|
| 5-6 | Niveau B : fix double-commit + pool DB | 7 |
| 7-8 | Niveau B : casser cycles d'imports | 5 |
| 9-10 | Niveau D (si vault gardé) : refacto zero-knowledge | 12 |
| 11-12 | Niveau D : tokens httpOnly + tests sentinel | 7 |

**Total : ~31h** sur 8 semaines.

### Phase 3 (mois 4-5) — Découpage frontend + backend

| Sem. | Tâche | Heures |
|---|---|---|
| 13-15 | Niveau C : découpage 3 fichiers backend monstres | 8 |
| 16-18 | Niveau C : découpage 3 composants frontend monstres | 8 |
| 19-20 | Niveau E : memory leaks Observable | 6 |

**Total : ~22h** sur 8 semaines.

### Phase 4 (mois 6-8) — Infrastructure et CI

| Sem. | Tâche | Heures |
|---|---|---|
| 21-22 | Niveau F : Dockerfile multi-stage | 4 |
| 23-24 | Niveau F : Scheduler Arq + Redis | 4 |
| 25-26 | Niveau G : Mypy + ruff CI | 3 |
| 27-28 | Niveau G : réduction except Exception | 3 |
| 29-30 | Niveau I : testcontainers PostgreSQL | 3 |

**Total : ~17h** sur 10 semaines.

### Phase 5 (mois 9-12) — Modèles + finitions

| Sem. | Tâche | Heures |
|---|---|---|
| 31-34 | Niveau H : découpage God-models | 10 |
| 35-40 | Niveau E : SSR + prerendering | 8 |
| 41-48 | Niveau I : tests paramétrés + E2E supplémentaires | 7 |

**Total : ~25h** sur 18 semaines.

### Grand total

**~110h de refacto** étalées sur 9-12 mois, soit ~3h par semaine en moyenne. **Soutenable** parallèlement à de l'activité commerciale.

---

<a name="metriques"></a>
## 12. Métriques de progression

À mesurer mensuellement pendant la phase de refacto :

| Métrique | Valeur actuelle | Cible 6 mois | Cible 12 mois |
|---|---|---|---|
| Lignes de code total | ~70 000 | < 50 000 | < 40 000 |
| Modules actifs | 10+ | 4-5 | 3-4 |
| Fichiers backend > 500 lignes | 8+ | 3 | 0 |
| Composants frontend > 500 LOC TS | 7 | 3 | 0 |
| `except Exception` | 61 | < 30 | < 15 |
| Imports lazy (cycles) | 56 | < 25 | < 10 |
| `.subscribe()` non gérés | 236-13 = 223 | < 100 | < 30 |
| Migrations Alembic totales | 66 | 66 | < 70 (rythme normal) |
| Couverture frontend | ~25% | 50% | 70% |
| Bundle initial frontend | ~1 Mo | < 600 Ko | < 400 Ko |
| Image Docker backend | 1.5-2 Go | < 500 Mo | < 200 Mo |
| Promesse zero-knowledge respectée | Non | Oui (si gardé) | — |
| Tokens httpOnly cookies | Non | Oui | — |
| Tests sur PostgreSQL | Non | Oui | — |
| Mypy + ruff CI | Non | Oui | — |
| SSR / prerendering | Non | Partial | Complet |

---

## Mot final

Ce document est **un guide, pas une obligation**. Tu n'es pas tenu de tout faire — tu es tenu de **faire des choix conscients**.

Trois pièges à éviter :

1. **Refactor avant validation produit** : si après 6 mois tu n'as pas 5-10 clients réels, **ne refactore rien**. Tu serais en train de polir un produit qui ne se vend pas. Mieux vaut tuer le projet ou pivoter.

2. **Tout faire d'un coup** : le grand refactor "big bang" est l'erreur classique. Une PR par item de cette liste, tests verts à chaque étape, déploiement entre chaque PR.

3. **Ajouter pendant qu'on refactore** : ne pas mélanger dette technique et nouvelles features. Si tu refactores le module Phishing, ne **ne pas** ajouter de nouvelle fonctionnalité Phishing dans la même PR. Pas de dette nouvelle pendant le remboursement de l'ancienne.

Et un conseil stratégique : **utilise ce document comme baromètre**. Si tu rouvres ce fichier dans 3 mois et que rien n'a bougé sur les métriques de la section 12, c'est probablement que ton temps est mieux investi ailleurs (commercial, support, contenu). Et c'est OK.

Le but n'est pas d'avoir un code parfait. Le but est d'avoir un produit **rentable**.

---

*Document à conserver dans `docs/refacto/dette-long-terme.md`.*
*Dernière mise à jour : juin 2026.*
