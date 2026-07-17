import { defineConfig, devices } from '@playwright/test';

/**
 * Config Playwright de RECETTE post-mise-en-production.
 *
 * Contrairement a playwright.config.ts (qui boot un serveur local sur :4200),
 * celle-ci tape une instance DEPLOYEE (prod par defaut) : PAS de webServer.
 * Les parcours restent volontairement minimalistes et robustes (peu de faux
 * positifs) car un echec ici declenche un rollback ECS automatique.
 *
 *   RECETTE_BASE_URL   racine du site deploye (defaut prod)
 *   RECETTE_EMAIL/PASSWORD  compte canari dedie (parcours authentifies)
 */
const BASE_URL = process.env.RECETTE_BASE_URL || 'https://rochercybersecurite.com';

export default defineConfig({
  testDir: './e2e/recette',
  fullyParallel: false,
  workers: 1,
  retries: 2,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: process.env.CI ? [['github'], ['list']] : 'list',
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
