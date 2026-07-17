import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  // La recette post-prod (e2e/recette/) tape une instance deployee et a sa
  // propre config (playwright.recette.config.ts) — l'exclure de la suite locale.
  testIgnore: '**/recette/**',
  // E2E tests share a single DB — serial execution avoids concurrent beforeAll race conditions
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env['CI'],
  retries: process.env['CI'] ? 2 : 1,
  timeout: 90_000,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:4200',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: {
    command: 'npm start',
    url: 'http://localhost:4200',
    reuseExistingServer: !process.env['CI'],
  },
});
