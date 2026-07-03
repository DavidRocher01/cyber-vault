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
      // Ratchet : ces planchers ne doivent que MONTER. Relevés le 2026-07-03
      // après Phase 3 (stores/guards/interceptor/services). Baseline 36.8/46.8/38.7/36.6.
      thresholds: {
        statements: 36,
        lines: 36,
        functions: 38,
        branches: 46,
      },
    },
  },
});
