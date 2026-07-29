# S7 — Registre d'acceptation du risque (dette connue différée)

Lot S7 de la remédiation de l'audit `docs/SECURITY_AUDIT_2026-07-27.md`
(finding **#17 — INFO**). Ce lot ne comporte **aucune modification de code** :
il formalise l'**acceptation du risque** pour des points confirmés par l'audit
mais soit déjà différés par décision produit, soit relevant d'une limitation
standard non-autonome. Chaque item note ses atténuants réels et le **déclencheur
de ré-évaluation**.

> Décision cadre : ces points ont été actés « à laisser tomber pour l'instant »
> (décision utilisateur 2026-07-22). Ils sont **ré-évalués** au passage **B2C**
> ou à la signature des **premiers contrats clients** (montée d'exposition +
> exigences contractuelles/assurance cyber).

---

## R1 — Phishing : mandat non prouvé au lancement (ex-S-6, DIFFÉRÉ acté)

- **Localisation** : `backend/app/api/v1/endpoints/phishing.py:509` (gate lancement).
- **Constat** : le seul verrou au lancement d'une campagne est la case CGU
  auto-déclarée (`campaign.cgu_accepted`). Le champ `domain_verified` existe, est
  calculé (`is_domain_verified`) et exposé, mais **n'est jamais lu comme garde**
  de lancement : rien ne prouve techniquement que l'opérateur est mandaté sur le
  domaine ciblé.
- **Atténuants réels** :
  - `from_email` **fixe** (domaine de l'éditeur/sending_domain contrôlé), pas
    d'usurpation arbitraire d'expéditeur ;
  - templates de landing/mail **rendus côté serveur** (pas d'injection libre) ;
  - `record_submit` **ne capture aucune donnée saisie** (pas de collecte de
    credentials) ;
  - gating par plan (Pro+) et rattachement consultant→client.
- **Décision** : **risque accepté / différé**. Ne PAS re-remonter comme finding
  neuf (cf. `project_security_deferred_actions`).
- **Reprise si besoin** : gate de propriété **DNS TXT réutilisable** (jeton à
  publier dans la zone du domaine ciblé), partagé avec R2.

## R2 — Dark Web : lookup de fuites sur emails de tiers (LOW, ouvert)

- **Localisation** : `backend/app/services/darkweb_dossier/ingestion.py:59`
  (`check_email_breaches`).
- **Constat** : l'ingestion interroge HIBP/LeakCheck sur des adresses e-mail de
  **tiers** (salariés des clients) fournies par upload CSV, sans preuve que le
  client B2B est responsable de traitement de ces adresses.
- **Atténuants réels** :
  - fonctionnalité **authentifiée** et **payante** (pas de surface anonyme) ;
  - requêtes en **lecture seule** vers des services publics de breach-check
    (aucune action offensive) ;
  - finalité métier légitime (le client évalue l'exposition de son propre
    périmètre) ; CSV borné (S4) et neutralisé à l'export (S4).
- **Décision** : **risque accepté** (item offensif déjà listé, resté ouvert par
  choix produit).
- **Reprise si besoin** : même gate **DNS TXT** de propriété de domaine que R1
  (ne traiter que les adresses d'un domaine dont la propriété est prouvée).

## R3 — TOTP : rejeu possible dans la fenêtre (~90 s)

- **Localisation** : `backend/app/api/v1/endpoints/auth.py:150`
  (`totp.verify(..., valid_window=1)`).
- **Constat** : un code TOTP reste valide sur sa fenêtre glissante (~90 s avec
  `valid_window=1`) ; aucun anti-rejeu strict (le même code peut être présenté
  deux fois dans la fenêtre).
- **Atténuants réels** :
  - attaque **non-autonome** : le mot de passe (1er facteur) est requis en
    amont ;
  - **lockout** comptant aussi les échecs TOTP + rate-limit `5/min` ;
  - fenêtre courte, pas de valeur pour un rejeu hors-ligne différé.
- **Décision** : **risque standard accepté** (limitation inhérente à TOTP).
- **Reprise si besoin** : persister `last_totp_step` par utilisateur pour un
  usage **strictement unique** du couple (step, user).

## R4 — admin-auth sans garde `isPlatformBrowser` — **RÉSOLU par S6**

- **Constat initial** (audit) : `admin-auth.service` accédait à `sessionStorage`
  dans son constructeur sans garde `isPlatformBrowser` (robustesse SSR).
- **Statut** : **corrigé** dans le lot **S6** — la clé admin n'est plus persistée
  du tout (mémoire seule), le constructeur ne touche plus aucune API navigateur →
  SSR-safe par construction. Cet item n'est donc **plus une dette ouverte**.

---

## Tableau de synthèse

| Réf | Point | Sévérité | Décision | Déclencheur de ré-évaluation |
|-----|-------|----------|----------|------------------------------|
| R1 | Phishing mandat non prouvé | INFO (ex-S-6) | Différé acté | Passage B2C / 1ers contrats |
| R2 | Dark Web emails tiers | LOW | Accepté | Passage B2C / 1ers contrats |
| R3 | TOTP rejeu dans la fenêtre | INFO | Accepté (standard) | Exigence conformité/client |
| R4 | admin-auth isPlatformBrowser | INFO | **Résolu (S6)** | — |
