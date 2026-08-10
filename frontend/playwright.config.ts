import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  // Deux suites ont leur propre config et ne doivent pas tourner ici :
  //  - e2e/recette/     tape une instance DEPLOYEE (playwright.recette.config.ts) ;
  //  - e2e/build-servi/ tape le BUILD DE PRODUCTION (playwright.build.config.ts),
  //    alors que ce fichier lance `ng serve`, donc la configuration `development`.
  testIgnore: ['**/recette/**', '**/build-servi/**'],
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
