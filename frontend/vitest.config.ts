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
      thresholds: {
        lines: 35,
        functions: 38,
        branches: 35,
      },
    },
  },
});
