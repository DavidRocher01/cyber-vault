import { defineConfig, devices } from '@playwright/test';

/**
 * Suite E2E qui tape le BUILD DE PRODUCTION servi en statique, et non
 * `ng serve`.
 *
 * `playwright.config.ts` lance `npm start`, donc la configuration
 * `development`. Tout ce qui ne vit que dans `production` — prerendu,
 * hydratation, optimisations, budgets — lui est invisible. C'est ainsi que la
 * regression de connexion du 2026-08-09 a traverse 84 e2e verts.
 *
 * Cette suite est volontairement COURTE. Elle ne redouble pas la couverture
 * fonctionnelle : elle ne garde que ce qui depend de la configuration livree.
 * La faire grossir la rendrait lente sans la rendre plus utile — un build de
 * production par execution se paie deja.
 */
export default defineConfig({
  testDir: './e2e/build-servi',
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env['CI'],
  retries: process.env['CI'] ? 1 : 0,
  timeout: 60_000,
  reporter: process.env['CI'] ? 'list' : 'html',
  use: {
    baseURL: 'http://localhost:4300',
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    // Le build fait partie du harnais : servir un `dist/` perime testerait
    // l'avant-derniere version et mentirait sans bruit.
    command: 'npm run build && node scripts/servir-build.mjs',
    url: 'http://localhost:4300',
    // Un build de production complet depasse largement les 60 s par defaut.
    timeout: 420_000,
    reuseExistingServer: false,
    stdout: 'pipe',
  },
});
