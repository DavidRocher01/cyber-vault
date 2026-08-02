# ADR 0004 — Angular 19 Standalone Components

**Statut** : Accepté
**Date** : 2024-01

---

## Contexte

Le frontend doit être un SPA (Single Page Application) avec :

- Composants modulaires et réutilisables
- Gestion d'état pour le vault chiffré (données sensibles en mémoire)
- TypeScript strict
- Tests unitaires rapides
- Taille de bundle optimisée

## Options évaluées

| Framework | Avantages | Inconvénients |
|-----------|-----------|---------------|
| **Angular 19 Standalone** | Typage strict, standalone simplifie l'archi, NgRx ComponentStore | Verbose, courbe d'apprentissage |
| **React + Zustand** | Flexible, grand écosystème | Moins opinionated, choix de lib à chaque niveau |
| **Vue 3 + Pinia** | Progressif, syntaxe simple | Moins adopté en B2B/entreprise |

## Décision

**Angular 19 avec Standalone Components** :

- **Standalone Components** : plus besoin de `NgModule`, archi simplifiée
- **NgRx ComponentStore** : gestion d'état locale par feature (vault, auth, darkweb…)
- **TypeScript strict** : `strict: true`, `strictTemplates: true`
- **Vitest** pour les tests unitaires (plus rapide que Karma/Jest)
- **Playwright** pour les tests E2E

## Conséquences

**Positives :**
- Standalone élimine la complexité des `NgModule`
- ComponentStore isolé par feature → pas d'état global monolithique
- TypeScript strict détecte les erreurs à la compilation
- Vitest nettement plus rapide que Karma pour les tests unitaires

**Négatives :**
- Angular plus verbeux que React/Vue pour les petits composants
- Standalone = rupture avec les patterns NgModule historiques

**Mitigation :**
- CLAUDE.md documente les conventions Angular du projet
- Chaque feature a son propre dossier avec composants + store + service
- Guard `cryptoGuard` protège les routes sensibles (vault)

---

## Évolution depuis (note, pas révision)

> Un ADR consigne une décision **à sa date**. Le corps ci-dessus reste donc écrit
> au présent d'Angular 19 et ne doit pas être réécrit : le relire, c'est
> comprendre ce qui était connu au moment du choix.

- **2026-07-31** — Le frontend est monté en **Angular 21** (TypeScript 5.9,
  ESLint 10 en configuration « flat »). La décision de fond — standalone,
  signals, ComponentStore par feature — n'a pas été remise en cause : les trois
  montées successives l'ont confortée.
- **Angular 22 est bloqué en amont**, par `@ngrx/component-store` (pas de v22) et
  `lucide-angular`. Détail et prérequis : `docs/MONTEES_DEPENDANCES.md`.
- La dépendance à `@ngrx/component-store` est aujourd'hui le principal frein à la
  montée de version. Si elle devait redevenir bloquante durablement, c'est cet
  ADR qu'il faudrait **remplacer** par un nouveau, pas amender.
