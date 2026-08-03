# État des lieux — Cyber-Vault

Ce fichier ne contient **que ce que git ne sait pas dire** : des décisions, leurs
raisons, et ce qui attend quelqu'un plutôt que du code. Utile pour reprendre le
projet depuis un autre poste, ou après une interruption.

L'historique des livraisons n'est pas ici — il est dans
`git log master --merges`, qui est toujours à jour, alors qu'une liste
« récemment livré » ne l'est jamais.

> **Comment le tenir.** Ce document est permanent : il n'a pas de date globale,
> chaque fait porte la sienne. Une ligne sans date est suspecte. Quand un point
> est réglé, on le supprime — la trace reste dans git ; on ne le déplace pas dans
> une rubrique « fait », qui grossit jusqu'à ce que plus personne ne lise le
> reste.
>
> La version précédente était datée « au 2026-07-29 » et annonçait comme trou
> ouvert un ALB fermé depuis. Un état des lieux qui se périme en silence est pire
> qu'une absence d'état des lieux.

> Rappel workflow : travailler sur `develop`, **jamais** committer sur `master` ;
> merge prod uniquement sur **confirmation explicite**. Voir `CLAUDE.md`,
> `docs/DEV_SETUP.md`.

---

## 1. En attente de quelqu'un — infra

- **ElastiCache Redis / Valkey — différé, assumé** (décision 2026-07-30).
  `REDIS_URL` est absente de Secrets Manager, vérifié le 2026-08-02. Le service
  tourne en `desiredCount: 1` et `--workers 1` : un seul processus, donc les
  compteurs `memory://` du rate-limiting sont de fait globaux. **Ce n'est pas une
  faille active**, c'est un prérequis pour scaler à plus d'une tâche — et pour
  les métriques de latence multi-instance. Coût estimé ~10,51 $/mois.
  Checklist : `docs/S2_INFRA_CHECKLIST.md`.

- **Créer le premier compte admin en production.** Le rôle `users.is_admin`
  existe depuis le 2026-08-02 (migration `4b6fae2210d3`), mais **aucun compte
  n'est promu** : la colonne arrive à `false` pour tout le monde, délibérément.
  Tant que le compte n'existe pas, `X-Admin-Key` reste le seul accès — les deux
  voies coexistent exprès, couper avant rendrait le back-office inaccessible.
  Séquence complète, dont le retrait de la clé ensuite :
  `docs/S6_INFRA_CHECKLIST.md` §0. La rotation de clé qui figurait ici est
  remplacée par cette bascule : faire tourner un secret partagé ne lui donne ni
  identité, ni révocation, ni 2FA.

> ⚠️ Ne jamais ajouter une clé à `$secret_names` de `deploy.yml` avant de l'avoir
> créée dans Secrets Manager : la tâche ECS ne démarrerait pas.

---

## 2. En attente de quelqu'un — business et légal

- **Facturation électronique — échéance réglementaire au 1er septembre 2026.**
  Toutes les entreprises assujetties doivent être en capacité de **recevoir** des
  factures électroniques via une **Plateforme Agréée** (PA). Le PPF a été
  abandonné comme plateforme d'échange en octobre 2024 : passer par une PA est
  donc obligatoire, il n'y a pas d'option « portail public gratuit ».
  À faire : choisir une PA et s'y raccorder. Aucune ligne de code n'en dépend
  aujourd'hui — c'est une démarche, pas un chantier technique.

- **Assurance RC Pro cyber** — à souscrire **avant les premiers contrats
  clients** ; vérifier explicitement que le **pentest / scan intrusif est
  couvert**.

- **Médiateur de la consommation** — à trancher : adhérer (~120-200 €/an) **si
  B2C**, ou assumer un positionnement **B2B-only**. Seul placeholder restant du
  pack légal.

- **E-mail de contact (changement de domaine)** — ImprovMX créé ; **config MX +
  Secrets Manager à finaliser**. Côté poste de dev : remplacer le SMTP Gmail
  `activatecyberscan` par Resend dans le `.env` local (la production est déjà
  sur Resend).

- **INPI** — marque « Rocher Cybersécurité » déposée sous le **n°5272918**
  (classes 9 + 42). Surveiller les mails BOPI et les oppositions.

---

## 3. Déclenché par un événement — rien à faire avant

- **Passage à la TVA** → le détail est dans
  [`RESTE_A_FAIRE.md`](RESTE_A_FAIRE.md). En un mot : **les montants ne changent
  pas**, seul le libellé « HT » devra être repris. Ne pas basculer les prix
  Stripe en `exclusive`.

- **Premier client payant** → snapshot RDS avant toute migration lourde, et
  régénération des PDF déjà stockés. Les deux sont sans objet tant qu'il n'y a
  aucune donnée client réelle.

- **Ouverture du scan gratuit à du vrai trafic** → écrire le webhook de rebonds
  Resend avant, sous peine de dégrader la réputation d'envoi sans le voir.

---

## 4. Décisions actées — ne pas reproposer spontanément

- **Sécurité différée** (2026-07-22, registre `docs/S7_RISK_ACCEPTANCE.md`) :
  CSP + Trusted Types CloudFront, rotation clés `.env` S-3, Vault AAD, RGPD S-8
  effacement, IP-pinning S-5, consentement phishing S-6, e-mails tiers Dark Web,
  replay TOTP.
- **Référencement** — repoussé à après l'amélioration du site. Les constats sont
  déjà mesurés, ne pas les refaire.
- **Oracle Staging** — abandonné (quota A1 = 0, pas de PAYG).
- **« Rocsûr »** — nom abandonné au profit de « Rocher Cybersécurité ».
- **Mesure d'audience et de conversion** — conception écrite et **entièrement
  tranchée** le 2026-08-02 : [`ANALYTICS.md`](ANALYTICS.md). Pas développée.
  La ligne précédente disait « design validé » sans que ce design n'existe nulle
  part ; c'est réparé.
  Retenu : attribution au moment de la conversion, **sans identifiant
  persistant** (principe RGPD, cf. §4), solution **maison sans coût récurrent**,
  rétention 13 mois. La recommandation Plausible/Matomo du kit marketing est
  caduque.
  Prérequis inchangé avant de développer la restitution : un vrai rôle admin —
  la clé `X-Admin-Key` n'est pas une base acceptable pour exposer des données de
  conversion.
- **`tax_behavior=inclusive` chez Stripe** — délibéré, cf. §3.
- **Dépôt de documents par les clients** — conception écrite le 2026-08-03 dans
  [`DEPOT_DOCUMENTS.md`](DEPOT_DOCUMENTS.md), **pas développée**. Trois points à
  trancher y figurent, dont un bloquant : sans analyse antivirus, le dépôt ne
  doit pas être ouvert aux clients.

---

## 5. Backlog non bloquant

- **Montées de dépendances** — état réel au 2026-08-02 : ESLint 10 ✅,
  Stripe 15.4.0 ✅ (Dependabot `0497ffa`), Angular **arrêté à 21.2.19** car
  bloqué en amont par `@ngrx/component-store` et `lucide-angular`, **Tailwind 4**
  restant et sans filet de validation visuelle. Détail et prérequis :
  `docs/MONTEES_DEPENDANCES.md`.
  Le SDK Stripe a bougé, **pas la version d'API serveur** : elle reste épinglée
  à `2024-06-20`. La monter est une décision distincte, encore à prendre.
- **Sensibilisation NIS2** — construite et promue offre de pointe n°2
  (2026-07-30) : 28 modules, 4 parcours, 198 tests. Reste que **les quotas ne
  sont pas appliqués par le code** : bloquant pour un passage en self-service,
  sans effet tant que la vente se fait sur devis.
- **Scan gratuit** — le gate e-mail (lot 1) est en production ; reste le lot 2 :
  Turnstile + cache domaine.
- **Observabilité** — métriques de latence multi-instance, liées à Redis (§1).
- **Dette technique** — l'essentiel des gros refactos restants sont des
  **décisions différées**, pas de la dette bloquante.

---

## 6. Où retrouver le reste

| Fichier | Contenu |
|---------|---------|
| `CLAUDE.md` | Règles projet : branches, architecture en couches, sécurité, Alembic, tests |
| `docs/SALES-BRIEF.md` | Offres et tarifs — source de vérité commerciale |
| `docs/RESTE_A_FAIRE.md` | Dette et chantiers ouverts, dont le passage à la TVA |
| `docs/ANALYTICS.md` | Mesure d'audience et de conversion — conception |
| `docs/DEPOT_DOCUMENTS.md` | Dépôt de documents par les clients — conception |
| `docs/MONTEES_DEPENDANCES.md` | Montées de versions et leurs blocages amont |
| `docs/DEV_SETUP.md` | Installer l'environnement sur un nouveau poste |
| `docs/SECURITY_AUDIT_2026-07-27.md` | L'audit dont S1→S7 est la remédiation |
| `docs/S2_INFRA_CHECKLIST.md`, `docs/S6_INFRA_CHECKLIST.md` | Les deux actions infra du §1 |
| `docs/S7_RISK_ACCEPTANCE.md` | Risques acceptés et différés |
| `docs/RELEASE_RUNBOOK.md` | Mise en production, dont la procédure de changement de grille tarifaire |
| `docs/GITHUB_SECRETS.md` | Secrets CI/CD |
| `git log master --merges` | Ce qui est parti en production, et quand |
