// @ts-check
/**
 * Configuration ESLint « flat » — remplace `.eslintrc.json` (2026-07-31).
 *
 * ESLint 9 ne lit plus le format `eslintrc`. La migration etait un prerequis
 * documente dans docs/MONTEES_DEPENDANCES.md.
 *
 * CORRECTION AU PLAN INITIAL : le plan visait ESLint 10 directement. Ce n'est
 * pas atteignable tant qu'on est sur Angular 20 —
 * `@angular-eslint` suit la majeure d'Angular en verrou, et seule la v22
 * (qui exige `@angular/cli >= 22`) accepte ESLint 10. La v20, compatible
 * Angular 20, plafonne a `eslint ^8.57 || ^9`. On s'arrete donc a ESLint 9,
 * qui utilise deja la config flat : tout le travail de format est fait, et le
 * passage a Angular 22 n'aura plus qu'a monter les versions.
 *
 * PERIMETRE VOLONTAIREMENT IDENTIQUE A L'ANCIENNE CONFIG : mêmes extends, mêmes
 * regles. On migre le FORMAT, pas le jeu de regles — activer
 * `eslint:recommended` ou `typescript-eslint` reglerait un autre probleme et
 * merite sa propre decision.
 */
const angular = require('angular-eslint');
const tseslint = require('typescript-eslint');

module.exports = tseslint.config(
  {
    ignores: ['projects/**/*', 'dist/**/*'],
  },
  {
    files: ['**/*.ts'],
    extends: [...angular.configs.tsRecommended],
    processor: angular.processInlineTemplates,
    rules: {
      '@angular-eslint/directive-selector': [
        'error',
        { type: 'attribute', prefix: 'app', style: 'camelCase' },
      ],
      '@angular-eslint/component-selector': [
        'error',
        { type: 'element', prefix: 'app', style: 'kebab-case' },
      ],
      // Regle NOUVELLE en v20, absente du `recommended` de la v17 : elle
      // signale 16 injections par constructeur encore presentes (auth.store,
      // vault.store, admin-auth.service, not-found, cyber-loader, globe).
      // Desactivee ICI pour que ce commit ne porte QUE la migration de format :
      // convertir ces 16 sites touche l'authentification et le coffre-fort, ca
      // merite son propre commit et sa propre relecture. A rallumer ensuite.
      '@angular-eslint/prefer-inject': 'off',
    },
  },
  {
    files: ['**/*.html'],
    extends: [...angular.configs.templateRecommended],
    rules: {},
  }
);
