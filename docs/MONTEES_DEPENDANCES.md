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
Corrigée par le passage à ESLint 10.

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

> **Mise à jour du 2026-07-31 — les chantiers 1 et 3 sont faits, le 2 est
> partiellement fait et bloqué en amont.** Voir le détail dans chaque section.
> L'ordre initialement écrit ici était erroné : il supposait qu'on pouvait
> passer à ESLint 10 avant Angular. C'est l'inverse — `@angular-eslint` suit la
> majeure d'Angular en verrou, et seule sa v21+ accepte ESLint 10. Le bon
> enchaînement est donc Angular d'abord, ESLint dans la foulée.

### 1. ESLint 8 → 10 — ✅ FAIT (2026-07-31)

- **Débloque** : Angular 22 ; ferme l'advisory `brace-expansion`.
- **Ce que ça implique** : ESLint 10 impose la configuration « flat ».
  `frontend/.eslintrc.json` est à réécrire en `eslint.config.js`. Entraîne
  `@typescript-eslint` 7 → 8 et `@angular-eslint` 17 → 20.
- **Risque** : nul sur le bundle livré — outillage pur.
- **Validation** : binaire, le lint passe ou non. `npx eslint src/` puis la CI.
- **Prérequis** : ~~aucun~~ — en réalité Angular 21. La config flat a été posée
  d'abord sur ESLint **9** (seul palier compatible Angular 20), puis ESLint 10
  est arrivé avec `@angular-eslint` 21. Deux étapes le même jour, commits
  `e7c912e` et `196d330`.

### 2. Angular 20 → 22 — ⚠️ ARRÊTÉ À 21, BLOQUÉ EN AMONT (2026-07-31)

- **Ce que ça implique** : montée coordonnée de **13 paquets** `@angular/*` plus
  le CLI et le devkit. Se fait avec `ng update`, qui applique des migrations
  automatiques sur le code applicatif.
- **Risque** : deux majeures d'écart, sur l'interface vue par les clients.
- **Validation disponible** : 3 057 tests unitaires, build AOT, E2E Playwright.
  Le filet existe et est sérieux.
- **Prérequis** : ESLint 10 (voir ci-dessus), et **`typescript` monte avec le
  groupe angular** — le compilateur Angular épingle une plage TS stricte
  (constaté en CI : « requires TypeScript >=6.0.0 and <6.1.0 but 5.8.3 was
  found »). Le groupe `angular` de `dependabot.yml` inclut donc `typescript`.
- ⚠️ **Ne jamais fusionner une PR Dependabot Angular isolée.** Le groupement mis
  en place dans `.github/dependabot.yml` fait désormais arriver la famille en une
  seule PR — c'est celle-là qu'il faut, jamais un paquet seul.

**Ce qui bloque Angular 22, vérifié le 2026-07-31 :**

| Paquet | Dernière version | Contrainte |
|--------|------------------|-----------|
| `@ngrx/component-store` | 21.1.1 — **pas de v22** | `@angular/core ^21` |
| `lucide-angular` | — | `13.x - 21.x` |

`ComponentStore` porte `auth.store.ts` et `vault.store.ts`. Passer à Angular 22
suppose donc soit d'attendre les versions amont, soit de sortir ComponentStore
de l'authentification et du coffre-fort — un chantier à part entière sur le
code le plus sensible du dépôt, avec réécriture des specs associées.

**Correction sur TypeScript.** Angular 22 exige `>=6.0 <6.1`, **pas 7**. La PR
Dependabot #95 proposait `typescript ~7.0.2`, donc hors plage : elle aurait
échoué là-dessus même son problème `@angular-eslint` résolu. Le groupe `angular`
contient bien `typescript`, mais Dependabot y met la DERNIÈRE version publiée,
pas celle qu'Angular supporte — le groupement ne suffit pas, il faut vérifier la
plage à chaque fois.

**Fait en Angular 21** : `ng update` a migré la syntaxe de contrôle de flux sur
6 fichiers, `main.server.ts`, et la signature de `tapResponse` dans les deux
stores. Deux corrections manuelles ont été nécessaires — le typage générique de
`Uint8Array` depuis TS 5.7 dans `crypto.service.ts`, et une projection de
contenu `NG8011` dans `consultant-profile`.

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
