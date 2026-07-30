# Montées de dépendances — reste à faire

> État au **2026-07-30**, après l'audit de dépendances et les montées sans impact
> code. Ce document ne liste que ce qui **reste** ; l'historique de ce qui a été
> fait est dans `git log` (commits `9ca6d47`, `e94fe90`, `e102758`).

---

## Où on en est

**L'arbre de dépendances est cohérent avec lui-même.** Prod, CI et postes de dev
installent les mêmes versions : `requirements.txt` hérite de
`requirements.prod.txt` via `-r`, et le front est verrouillé par
`package-lock.json`. Aucune dérive interne — vérifié paquet par paquet.

**Aucune vulnérabilité connue en production.** `npm audit --omit=dev` : 0.
`pip-audit` : 0. Le retard porte sur l'outillage, pas sur ce qui est livré.

**Une advisory ouverte, dev uniquement** : `brace-expansion`
[GHSA-mh99-v99m-4gvg](https://github.com/advisories/GHSA-mh99-v99m-4gvg) (DoS),
via toute la chaîne de dépendances d'ESLint 8. N'atteint jamais le navigateur.
Corrigée par le passage à ESLint 9.

---

## Le risque réel : la distance, pas la CVE

Rien ne justifie une action en urgence. Mais l'absence de faille aujourd'hui ne
rend pas le retard gratuit : **plus on est loin, moins on peut réagir vite**.

Si une faille critique tombe sur Stripe, on ne monte pas d'une version — on
traverse cinq majeures en urgence, avec un changement de version d'API au
passage, sur la chaîne de paiement, sous pression. ESLint 8 illustre déjà le
mécanisme : il ne reçoit plus de correctifs, donc l'advisory ci-dessus ne sera
**jamais** corrigée dans cette branche.

---

## Les quatre chantiers, dans l'ordre

L'ordre n'est pas arbitraire : ESLint doit passer avant Angular, car
`@angular-eslint` 20 (exigé par Angular 22) exige ESLint 9. Le faire après, c'est
le faire deux fois.

### 1. ESLint 8 → 9

- **Débloque** : Angular 22 ; ferme l'advisory `brace-expansion`.
- **Ce que ça implique** : ESLint 9 impose la configuration « flat ».
  `frontend/.eslintrc.json` est à réécrire en `eslint.config.js`. Entraîne
  `@typescript-eslint` 7 → 8 et `@angular-eslint` 17 → 20.
- **Risque** : nul sur le bundle livré — outillage pur.
- **Validation** : binaire, le lint passe ou non. `npx eslint src/` puis la CI.
- **Prérequis** : aucun. C'est le chantier à prendre en premier.

### 2. Angular 20 → 22

- **Ce que ça implique** : montée coordonnée de **13 paquets** `@angular/*` plus
  le CLI et le devkit. Se fait avec `ng update`, qui applique des migrations
  automatiques sur le code applicatif.
- **Risque** : deux majeures d'écart, sur l'interface vue par les clients.
- **Validation disponible** : 3 057 tests unitaires, build AOT, E2E Playwright.
  Le filet existe et est sérieux.
- **Prérequis** : ESLint 9 (voir ci-dessus).
- ⚠️ **Ne jamais fusionner une PR Dependabot Angular isolée.** Le groupement mis
  en place dans `.github/dependabot.yml` fait désormais arriver la famille en une
  seule PR — c'est celle-là qu'il faut, jamais un paquet seul.

### 3. Stripe 10.5.0 → 15.3.1

- **Ce que ça implique** : cinq majeures. Surface d'usage modeste — 10 points
  d'API sur 3 fichiers (`checkout.Session.create`, `Webhook.construct_event`,
  `Subscription.retrieve`/`cancel`, `Customer.create`, `billing_portal`,
  `Balance.retrieve`).
- **Prérequis levé le 2026-07-30** : `stripe.api_version` est désormais épinglé
  à `2024-06-20` dans `stripe_service.py`. Le contrat serveur ne bougera donc
  **pas** en même temps que le SDK — la montée est devenue un changement
  purement Python, et le passage à une version d'API plus récente une décision
  distincte, testable et réversible seule. **Faire les deux séparément.**
- **Validation disponible** : 88 tests sur la surface paiement + l'E2E
  `frontend/e2e/checkout.spec.ts`. Couverture mesurée depuis le 2026-07-30 :
  `stripe_service.py` 95 %, `webhooks.py` 82 %.
- **Angles morts identifiés** : les 17 lignes non couvertes de `webhooks.py`
  (branches d'erreur). Les couvrir avant la montée — c'est une liste finie,
  obtenue avec `pytest --cov=app --cov-report=term-missing`.
- **À faire aussi** : un parcours d'abonnement complet en mode test Stripe.
  Aucun test automatisé ne remplace ça sur une chaîne de paiement.

### 4. Tailwind 3 → 4

- **Ce que ça implique** : nouveau moteur, configuration repensée.
- **Risque** : régression visuelle diffuse sur toute l'application.
- **Validation disponible : AUCUNE.** Ni les 3 057 tests unitaires ni les E2E ne
  détectent un changement de rendu — ils vérifient des comportements, pas des
  pixels. C'est le seul des quatre chantiers sans filet.
- **Prérequis** : se donner un filet visuel. **Storybook 8.6 est déjà installé** :
  c'est le bon endroit pour poser des captures de référence avant de bouger.
  Sinon, assumer une revue manuelle page par page.

---

## Ce qui empêche de redécrocher

- **`.github/dependabot.yml` groupe par famille** (angular, lint, storybook,
  test, styles, aws, backend-dev, actions). Chaque famille arrive en une PR
  cohérente au lieu d'un paquet par PR.
- **`scripts/check_runtime_versions.py`** (lancé en CI) garde Python et Node
  alignés entre `.python-version`, `.nvmrc`, le `Dockerfile` et `engines.node`.
- **Seuil de couverture à 90 %** (`pytest.ini`), relevé depuis 82 % pour
  verrouiller les ~94 % réels.

## Points de vigilance appris en route

- Les PR Dependabot sur les **actions GitHub** mettent bien à jour le SHA, mais
  peuvent laisser un commentaire de version incohérent (`# v6` sur un SHA de
  v7). Vérifier le SHA contre le tag officiel avant de fusionner :
  `gh api repos/actions/<action>/git/ref/tags/<tag> -q .object.sha`
- `npm update` peut dépasser ce que propose Dependabot (undici est monté en 7.x
  là où la PR proposait 6.27.0). Vérifier qui déclare la dépendance avant
  d'accepter : ici `jsdom` exigeait `^7.24.5`, la résolution était correcte.
