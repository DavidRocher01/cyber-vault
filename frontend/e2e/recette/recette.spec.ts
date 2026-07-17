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
    await acceptCookies(page);

    await page.goto('/auth/login');
    await page.locator('[formcontrolname="email"]').fill(EMAIL);
    await page.locator('[formcontrolname="password"]').fill(PASSWORD);
    await page.getByRole('button', { name: /se connecter/i }).click();

    // On doit quitter /auth (login abouti) et avoir un token en sessionStorage.
    await page.waitForURL((url) => !url.pathname.startsWith('/auth'), { timeout: 20_000 });
    const token = await page.evaluate(() => sessionStorage.getItem('cv_token'));
    expect(token, 'token cv_token absent apres login = auth front cassee').toBeTruthy();
  });
});
