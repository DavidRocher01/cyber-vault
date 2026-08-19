import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['src/test-setup.ts'],
    include: ['src/**/*.spec.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      include: ['src/app/**/*.ts'],
      exclude: [
        'src/app/app.config.ts',
        'src/app/app.config.server.ts',
        'src/app/app.routes.ts',
        'src/app/app.component.ts',
        'src/app/**/*.routes.ts',
        'src/app/**/*.module.ts',
        // RÈGLE : toute exclusion porte sa raison. Une exclusion muette ne dit
        // pas si le code est testé ou à découvert — elle le rend seulement
        // invisible, ce qui est pire, parce qu'on cesse de se poser la question.
        //
        // HISTORIQUE — 2026-08-18 : cinq fichiers de `core/` figuraient ici sans
        // aucune justification. Mesure faite après les avoir retirés :
        //   crypto.guard.ts      100 %  — testé depuis toujours, simplement
        //                                 invisible. L'exclusion cachait une
        //                                 réussite, et surtout laissait le garde
        //                                 du coffre régresser sans alerte.
        //   clipboard.service     18 %  \
        //   theme.service         13 %   |  réellement à découvert : 207 lignes
        //   i18n.service          21 %   |  de `core/`, dont deux services qui
        //   animation.service      0 %  /   écrivent dans localStorage.
        // Les quatre premiers ont désormais leurs tests. C'est la même leçon que
        // `backend/.coveragerc`, tirée le 2026-07-30 pour les mêmes raisons.

        // Non testable unitairement : quatre tweens GSAP posés sur des
        // `HTMLElement` (révélation de mot de passe, fondu, secousse d'erreur).
        // Un test ne pourrait qu'affirmer que GSAP a été appelé, ce qui ne dit
        // rien de ce qui compte ici — l'effet visuel. Même famille que le globe
        // ci-dessous, et même traitement : vérifié à l'œil, pas en unitaire.
        'src/app/core/services/animation.service.ts',

        // Non testable unitairement : rendu WebGL/canvas (globe 3D interactif,
        // ~490 lignes de logique three.js/animation). Testé visuellement, pas en unit.
        'src/app/shared/globe/**',
      ],
      // Ratchet : ces planchers ne doivent que MONTER.
      //
      // Relevés le 2026-08-17. Les précédents (63/63/67/74) dataient du
      // 2026-07-22 et la couverture réelle avait pris ~4,5 points depuis : le
      // cliquet ne cliquetait plus, on pouvait supprimer quatre points de tests
      // sans que rien ne bronche. Mesuré local Win après les specs
      // cookie-banner / nav-buttons / maintenance-banner / verify-certificate.
      //
      // MESURÉ DEUX FOIS, À CODE IDENTIQUE, ET LES DEUX RELEVÉS DIFFÈRENT :
      //   67.99 / 67.77 / 71.46 / 78.71   (statements / lines / functions / branches)
      //   68.84 / 68.63 / 72.49 / 79.75
      // Presque un point d'écart, dénominateurs identiques — le fournisseur v8
      // ne recompte pas tout à l'identique d'une exécution à l'autre.
      //
      // Les planchers sont donc calés ~1 pt SOUS LE RELEVÉ LE PLUS BAS, pas sous
      // la meilleure mesure : un seuil qui passe une fois sur deux n'apprend
      // qu'une chose, ignorer les échecs. S'y ajoute l'écart CI-Linux (~-0.15%).
      thresholds: {
        statements: 67,
        lines: 67,
        functions: 70,
        branches: 78,
      },
    },
  },
});
