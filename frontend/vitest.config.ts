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
        'src/app/core/services/animation.service.ts',
        'src/app/core/services/theme.service.ts',
        'src/app/core/services/clipboard.service.ts',
        'src/app/core/services/i18n.service.ts',
        'src/app/core/guards/crypto.guard.ts',
        // Non testable unitairement : rendu WebGL/canvas (globe 3D interactif,
        // ~490 lignes de logique three.js/animation). Testé visuellement, pas en unit.
        'src/app/shared/globe/**',
      ],
      // Ratchet : ces planchers ne doivent que MONTER. Relevés le 2026-07-22
      // après la vague de tests features/ (18 composants) + passe ciblée
      // auth/vault. Mesuré local Win : 64.5/75.0/68.4/64.0 ; planchers posés
      // ~1 pt en dessous pour absorber l'écart CI-Linux (~-0.15%).
      thresholds: {
        statements: 63,
        lines: 63,
        functions: 67,
        branches: 74,
      },
    },
  },
});
