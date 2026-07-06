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
        'src/app/app.routes.ts',
        'src/app/app.component.ts',
        'src/app/**/*.routes.ts',
        'src/app/**/*.module.ts',
        'src/app/core/services/animation.service.ts',
        'src/app/core/services/theme.service.ts',
        'src/app/core/services/clipboard.service.ts',
        'src/app/core/services/i18n.service.ts',
        'src/app/core/guards/crypto.guard.ts',
      ],
      // Ratchet : ces planchers ne doivent que MONTER. Relevés le 2026-07-05
      // après la couverture des composants (parcours paiement, auth, formulaires).
      // Baseline mesurée 43.9/54.6/43.8/43.7.
      thresholds: {
        statements: 43,
        lines: 43,
        functions: 43,
        branches: 54,
      },
    },
  },
});
