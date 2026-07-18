# Refonte du parcours Phishing — conception

> Statut : **spec validée sur les grandes décisions, plan par lots à exécuter.**
> Date : 2026-07-18. Ne pas commencer un lot sans que le précédent soit vert.

## Décisions cadrées

| Sujet | Décision |
|---|---|
| **Opérateurs** | **Les deux** : consultant RSSI (campagne rattachée à un client) **et** entreprise en direct (self-service) |
| **Périmètre** | Templates email+landing · gestion des cibles · envoi programmé/cadencé · **training-on-fail** |
| **Look-alike** | **À finir, à deux niveaux** : sous-domaine maîtrisé par défaut (gratuit) + domaine acheté par client (premium) |
| **Accès** | **Gaté par plan/tier** pour l'entreprise directe ; le consultant y accède via sa prestation |

## Point de départ (audit 2026-07-18)

**On garde (le cœur, solide + testé) :** moteur de tracking maison (pixel/clic/landing/submit, idempotent, TTL, rate-limité), 13 scénarios email + landings + contexte dynamique, envoi par batch (verrou, planif, round-robin) via scheduler, rapport PDF ReportLab, modèle campagne/cibles + CRUD + import CSV + UI (liste/wizard/édition/détail).

**À rebrancher / finir :** look-alike (back complet, aucune UI), vérif domaine DNS-TXT (aucune UI), annulation de campagne (statut `cancelled` jamais utilisé).

**À réparer / retirer :** training-on-fail non câblé (webhook awareness `/internal/phishing-click` sans appelant), PDF UI cassé (`window.open` → 401), aucun gating rôle/plan, dérive enum de statut, statut `reported` mort, `PHISHING_FROM_NAME` inutilisé, `.env.example` avec base URL qui casse le tracking, pas de SSRF guard sur `lookalike_domain`.

---

## Architecture cible

### 1. Modèle à deux opérateurs
- `phishing_campaigns` : + `rssi_client_id` (nullable, FK → `rssi_clients`, `ON DELETE CASCADE`).
  - **Entreprise directe** : `rssi_client_id = NULL`, cibles = ses employés, espace `/phishing`.
  - **Consultant** : `rssi_client_id = X`, campagne dans un onglet « Phishing » de la fiche client RSSI, scopée par `consultant_user_id`.
- Service unifié ; les endpoints branchent selon la présence de `rssi_client_id`.
- Accès :
  - Entreprise : `get_current_user` + **`require_phishing_access`** (nouvelle dépendance, gate plan/tier).
  - Consultant : `get_rssi_consultant` + ownership du client (`_get_client_or_404`).

### 2. Gestion des cibles (non destructive)
- Import CSV **merge/dédup** (aujourd'hui un ré-upload efface tout), ajout/suppression unitaire, listes réutilisables par entreprise/client.

### 3. Envoi programmé + cadence + annulation
- Garder le batch/planif. **Câbler `cancelled`** (bouton annuler). Cadence par campagne (aujourd'hui `PHISHING_BATCH_SIZE` global).

### 4. Training-on-fail (intégration phare)
- Sur `record_click` (et/ou `record_submit`, configurable par campagne), **inscrire la cible dans un module de remédiation awareness**.
- Appel **direct au service awareness** (pas le webhook HTTP mort). Idempotent (pas de ré-enrôlement).
- Organisation awareness requise : client RSSI → son `awareness_organization_id` ; entreprise directe → créer/rattacher une org. Le magic-link awareness *est* le mail « vous avez échoué, voici votre formation ».
- Toggle par campagne : `training_on_fail` (bool) + déclencheur (`click` | `submit`).

### 5. Look-alike à deux niveaux
- `phishing_campaigns` : + `sending_mode` (`subdomain` | `lookalike`).
- **Défaut — sous-domaine maîtrisé** : envoi depuis un sous-domaine de notre infra déjà vérifié chez Resend (délivrabilité OK). Câbler le `_sim_subdomain` existant dans l'UI.
- **Premium — domaine acheté par client** : UI de suggestion (`generate_lookalikes`) → flux vérif **DNS-TXT** dans l'UI (`requestDomainVerify`/`checkDomainVerify`) → vérif domaine chez Resend → **case de mandat client** (traçée) → gaté premium.
- Fix : la landing doit poster sur le **même host** que celui qui la sert (aujourd'hui toujours `PHISHING_BASE_URL`).

### 6. Fondations / réparations
- Unifier le statut sur `CampaignStatus` (enum) ; retirer `reported`/`PHISHING_FROM_NAME` morts ; fixer `.env.example` (base URL avec `/api/v1`) ; **SSRF guard** sur `lookalike_domain`.
- PDF UI : fetch-blob-avec-header (ou URL signée courte) au lieu de `window.open`.

---

## Risques à porter explicitement

- **Délivrabilité look-alike** : domaine neuf = 0 réputation → spam. SPF/DKIM/DMARC + vérif Resend + warm-up, par domaine. (Le niveau « sous-domaine maîtrisé » évite ce risque au quotidien.)
- **Légal/consentement** : enregistrer un typosquat du domaine d'un client pour piéger ses employés = test autorisé **uniquement avec mandat écrit**. Case de consentement + traçabilité obligatoires dans le parcours premium.
- **Envoi de vrais mails en recette** : la recette post-prod ne doit **jamais** envoyer de phishing réel — prévoir un mode simulation / cibles canari.

---

## Plan par lots (chacun sur `develop`, testé, déployable seul)

- **Lot 0 — Fondations & nettoyage. ✅ FAIT (`877b11c`).** Enum de statut unifié, PDF UI réparé (blob+Bearer), code mort retiré (`reported`, `PHISHING_FROM_NAME`), `.env.example` corrigé, validation de domaine (anti-SSRF/injection, sans résolution réseau) sur `domain`+`lookalike_domain`.
- **Lot 1 — Modèle deux opérateurs + gating. ✅ FAIT.** `rssi_client_id` (nullable FK, migration `97647476457e`), filtre de liste (`?rssi_client_id=` vs entreprise-only), onglet « Phishing » dans la fiche client RSSI (liste + « Nouvelle campagne » → config). Ownership = `user_id` (le consultant crée sous son compte) ; `rssi_client_id` = attribution. **Gating par plan AU LANCEMENT** (freemium : création/config d'un brouillon libres ; entreprise directe → tier ≥ 3 Pro pour lancer l'envoi ; consultant → via sa prestation, pas de gate tier). À la création, seul le contexte consultant est validé (is_rssi_consultant + ownership du client, 404 sinon).
- **Lot 2 — Cibles non destructives.** Merge/dédup CSV, ajout/suppression unitaire, listes réutilisables.
- **Lot 3 — Planif + annulation + cadence. ✅ FAIT.** Endpoint `POST /campaigns/{id}/cancel` (statut `cancelled` câblé, autorisé depuis draft/pending_verification/ready/scheduled/sending ; le batch ne traite que scheduled/active/sending → plus d'envoi) + bouton « Annuler » (page détail). Cadence par campagne : `batch_size` nullable (migration `a08c087165b4`, repli sur `PHISHING_BATCH_SIZE`) utilisé par le batch + input dans l'édition.
- **Lot 4 — Training-on-fail. ✅ FAIT.** `training_on_fail` + `training_trigger` (click|submit) sur la campagne (migration `d04c845d0a5a`) ; `record_click`/`record_submit` → `_enroll_target_in_remediation` (best-effort, ne casse jamais le tracking) : résout l'org du client RSSI → learner EXISTANT (par email) → programme "remediation" (ou 1er actif en repli) → `enroll_learner` (idempotent). Case à cocher dans l'édition de campagne. **Périmètre** : mode consultant (client avec awareness activée) + learner déjà inscrit. **Follow-up** : auto-création du learner (= email de formation), org pour l'entreprise directe, et un vrai contenu de programme de remédiation dédié (aujourd'hui repli sur le programme actif existant).
- **Lot 5 — Look-alike à deux niveaux.** `sending_mode`, UI sous-domaine vs domaine acheté, flux vérif DNS-TXT + Resend, mandat, gating premium, fix landing cross-host.
- **Lot 6 — Tests & recette.** E2E des deux parcours, ajout à la recette post-prod en **mode simulation** (aucun mail réel).

Ordre conseillé : **0 → 1 → 4 → 3 → 2 → 5 → 6** (le training-on-fail tôt car c'est la valeur différenciante ; le look-alike en dernier car c'est le plus lourd en ops).
