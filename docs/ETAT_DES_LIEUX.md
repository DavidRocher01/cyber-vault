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

- **Vérifier la purge des orphelins vers le 12 août 2026.** Deux objets S3
  déposés le 2026-08-05 sont devenus orphelins (leurs livrables ont été
  supprimés). La purge nocturne doit les effacer sept jours après leur dépôt,
  objet S3 compris. C'est le seul maillon du chantier qui n'aura pas été observé
  en conditions réelles.
  Bucket : `cybervault-rssi-deliverables-prod`. Ne pas supprimer l'objet
  `malware-protection-resource-validation-object`, écrit par GuardDuty.

- **Rotation de secrets — différée le 2026-08-04, connue.** Une capture d'écran
  de la console Secrets Manager a exposé des valeurs de production. Entièrement
  lisibles : `RESEND_API_KEY`, `SMTP_PASSWORD`, `STRIPE_WEBHOOK_SECRET`.
  Partiellement : `STRIPE_SECRET_KEY` (`sk_live_`), `SECRET_KEY`,
  `DATABASE_URL`, `ORIGIN_VERIFY_SECRET`.
  La plus sensible est la clé Resend : elle permet d'envoyer des courriels
  signés DKIM depuis les domaines vérifiés.
  ⚠️ **`SECRET_KEY` ne se fait pas tourner à la légère** : elle chiffre aussi
  les graines TOTP, sa rotation casse la 2FA de tous les comptes. Chantier
  séparé, avec re-chiffrement. Cf. `docs/RUNBOOK_INCIDENT.md`.

- **Supprimer les clés de `cybervault-deploy`** — **désactivées le 2026-08-05**,
  pas encore supprimées. Laisser passer quelques jours, vérifier qu'aucun
  déploiement ne casse, puis `delete-access-key`. Réactivation d'une commande en
  cas de besoin : `update-access-key --status Active`.
  Ce que c'était : deux clés d'accès **statiques et actives** sur un utilisateur
  portant `PowerUserAccess` — tout sauf IAM et Organizations. L'une n'avait
  **jamais** servi, l'autre pas depuis le **22 avril 2026**. La CI ayant basculé
  sur un rôle assumé par OIDC, plus rien ne les utilisait. Une clé statique ne
  demande ni MFA, ni session, ni présence.
  Retirer aussi `AWSAppRunnerFullAccess` — App Runner n'est pas utilisé — et se
  demander si cet utilisateur a encore une raison d'exister.

- **Utilisateur IAM nominatif pour l'usage interactif — souhaitable, pas
  urgent.** Les appels se font sous le compte racine, ce qu'AWS déconseille.
  Mais le risque réel est faible, vérifié le 2026-08-05 : **aucune clé d'accès
  racine n'existe** et **la MFA racine est active** ; la session est temporaire
  et expire.
  La version précédente de cette entrée présentait le point comme un constat
  d'audit sérieux, sur la seule foi d'un `arn:…:root`, sans avoir vérifié ni les
  clés ni la MFA. L'ordre correct est : les clés statiques d'abord, cet
  utilisateur ensuite.

- **Ajouter les documents déposés à la politique de confidentialité.** Elle
  énumère les durées (compte, scans, journaux, facturation) mais **ne dit rien
  des documents remis par les clients**, alors que le dépôt est ouvert depuis le
  2026-08-05. L'article 13 du RGPD impose d'informer sur les durées de
  conservation.
  À écrire : documents remis par le client, effacés 90 jours après la fin de la
  mission ; livrables produits par le consultant, conservés au titre de la
  responsabilité professionnelle. Page
  `frontend/src/app/features/cyberscan/politique-confidentialite/`.

- **Plafond de taille de corps de requête sur l'ALB ou CloudFront.** La lecture
  bornée livrée le 2026-08-03 protège la mémoire, pas la réception : Starlette
  analyse le corps multipart avant que le code applicatif ne s'exécute. Vaut
  pour toute la plateforme, pas seulement le dépôt de documents.

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
  Le prérequis qui figurait ici — un vrai rôle admin, la clé partagée n'étant
  pas une base acceptable pour exposer des données de conversion — est levé
  depuis le 2026-08-02.
- **`tax_behavior=inclusive` chez Stripe** — délibéré, cf. §3.
- **Domaine d'expédition des simulations de phishing** — `cyberscanapp.com`,
  décidé le 2026-08-03 et **en service depuis le 2026-08-04**
  (`PHISHING_FROM_EMAIL = noreply@cyberscanapp.com`, révision 147). Gratuit :
  l'ancien domaine de marque était déjà vérifié chez Resend et n'envoyait plus
  rien. Domaine entièrement distinct, donc isolation de réputation totale.
  ⚠️ **Ne pas le supprimer de Resend.** L'offre annonce « 1 domain » et le
  compte en a deux ; le second est hérité et probablement irremplaçable sans
  passer à Pro (20 $/mois).
  Le nom reste imparfait pour le réalisme — « cyberscan » évoque un outil de
  sécurité. À reprendre avec un domaine fade quand une campagne facturée le
  justifiera, pas avant. Raisonnement : `docs/PHISHING_REDESIGN.md` §5c.
- **Dépôt de documents par les clients** — conception dans
  [`DEPOT_DOCUMENTS.md`](DEPOT_DOCUMENTS.md). Antivirus tranché le 2026-08-03 :
  **GuardDuty Malware Protection for S3**, activé seul, **en service depuis le
  2026-08-05** et prouvé de bout en bout sur un dépôt réel.
  Livrées : signature de début de fichier, registre `fichiers_deposes`, règle de
  délivrance sur les deux voies, traduction des cinq statuts GuardDuty, purge
  des orphelins.
  **Restent l'étape 3** — ouvrir le dépôt côté portail client, débloquée par
  l'antivirus, c'est le besoin d'origine — **et l'étape 4b**, la rétention des
  documents rattachés, qui dépend du champ `origine` apporté par l'étape 3. Le
  cadrage juridique des trois régimes est écrit dans DEPOT_DOCUMENTS.
  L'étape 5, les preuves rattachées aux critères NIS2, change la nature du
  produit et mérite son propre cadrage.

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
