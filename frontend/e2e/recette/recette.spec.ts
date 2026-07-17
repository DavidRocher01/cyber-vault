import { test, expect, Page } from '@playwright/test';

/**
 * Recette UI post-prod — parcours critiques en navigateur reel contre le site
 * DEPLOYE. Objectif : detecter ce que la recette API ne voit pas (bundle JS
 * casse, routing SPA HS, mauvaise base URL d'API cote front).
 *
 * Robustesse volontaire : on verifie que ca REND et que l'auth aboutit, sans
 * s'accrocher a des details fragiles — un echec ici provoque un rollback ECS.
 */

const EMAIL = process.env.RECETTE_EMAIL || '';
const PASSWORD = process.env.RECETTE_PASSWORD || '';
const hasCanary = Boolean(EMAIL && PASSWORD);

async function acceptCookies(page: Page): Promise<void> {
  await page.addInitScript(() => localStorage.setItem('cyberscan_cookie_consent', 'accepted'));
}

async function loginCanary(page: Page): Promise<void> {
  await acceptCookies(page);
  await page.goto('/auth/login');
  await page.locator('[formcontrolname="email"]').fill(EMAIL);
  await page.locator('[formcontrolname="password"]').fill(PASSWORD);
  await page.getByRole('button', { name: /se connecter/i }).click();
  await page.waitForURL((url) => !url.pathname.startsWith('/auth'), { timeout: 20_000 });
}

test.describe('Recette prod — parcours critiques UI', () => {
  test('la vitrine se charge et Angular rend le contenu', async ({ page }) => {
    const resp = await page.goto('/');
    expect(resp && resp.status(), 'la home doit repondre <400').toBeLessThan(400);
    await expect(page).toHaveTitle(/cyber|s[eé]curit/i);
    // Le bundle Angular a execute et hydrate du contenu (pas une page blanche/erreur).
    await expect(page.locator('body')).toContainText(/s[eé]curit[eé]/i);
  });

  test('connexion canari via UI puis espace authentifie', async ({ page }) => {
    test.skip(!hasCanary, 'RECETTE_EMAIL / RECETTE_PASSWORD absents');
    await loginCanary(page);
    const token = await page.evaluate(() => sessionStorage.getItem('cv_token'));
    expect(token, 'token cv_token absent apres login = auth front cassee').toBeTruthy();
  });

  // Pages protegees par authGuard : apres login, elles doivent RENDRE (on reste
  // sur la route, le titre attendu s'applique) et non rediriger vers /auth ni
  // planter. Signal fort que le bundle authentifie + le guard fonctionnent.
  const AUTH_PAGES: Array<{ path: string; title: RegExp }> = [
    { path: '/dashboard', title: /dashboard/i },
    { path: '/url-scanner', title: /url|scan/i },
    { path: '/profile', title: /profil/i },
  ];

  for (const { path, title } of AUTH_PAGES) {
    test(`page authentifiee ${path} rend apres login`, async ({ page }) => {
      test.skip(!hasCanary, 'RECETTE_EMAIL / RECETTE_PASSWORD absents');
      const errors: string[] = [];
      page.on('pageerror', (e) => errors.push(String(e)));

      await loginCanary(page);
      await page.goto(path);

      // On ne doit PAS avoir ete renvoye vers /auth (guard OK) ...
      await expect(page).toHaveURL(new RegExp(`${path}(/|\\?|$)`));
      // ... et le titre de la route doit s'appliquer (composant charge).
      await expect(page).toHaveTitle(title);
      expect(errors, `erreurs JS sur ${path}: ${errors.join(' | ')}`).toHaveLength(0);
    });
  }
});
