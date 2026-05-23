import { test, expect } from '@playwright/test';
import { createAndLogin, login, BASE_PASSWORD } from './helpers';

const MASTER = 'MasterPass456!';
let sharedEmail: string;

test.beforeAll(async ({ browser }) => {
  const page = await browser.newPage();
  sharedEmail = await createAndLogin(page);
  await page.close();
});

test.beforeEach(async ({ page }) => {
  await login(page, sharedEmail);
  // Trigger cryptoGuard → redirects to /auth/master-password
  await page.goto('/vault');
  // cryptoGuard redirects to /auth/master-password?returnUrl=... — use regex to match with query params
  await page.waitForURL(/\/auth\/master-password/, { timeout: 10_000 });
  // Unlock vault with master password (form uses unassociated label)
  await page.locator('input[type="password"]').fill(MASTER);
  await page.getByRole('button', { name: /déverrouiller/i }).click();
  await page.waitForURL(url => url.pathname === '/vault', { timeout: 10_000 });
});

test.describe('Parcours Vault', () => {
  test('affiche le dashboard vault après connexion', async ({ page }) => {
    await expect(page.getByText('Mon Vault')).toBeVisible();
  });

  test('ajoute une nouvelle entrée et la voit dans la liste', async ({ page }) => {
    const title = `GitHub_${Date.now()}`;
    await page.getByRole('button', { name: /nouvelle entrée/i }).click();
    await page.locator('input[title="Titre de l\'entrée"]').fill(title);
    await page.locator('input[type="password"]').fill('secret123');
    await page.getByRole('button', { name: /^Ajouter$/i }).click();
    await expect(page.getByText(title)).toBeVisible({ timeout: 8_000 });
  });

  test('supprime une entrée de la liste', async ({ page }) => {
    const title = `ASupprimer_${Date.now()}`;
    // Add the entry first
    await page.getByRole('button', { name: /nouvelle entrée/i }).click();
    await page.locator('input[title="Titre de l\'entrée"]').fill(title);
    await page.locator('input[type="password"]').fill('pass456');
    await page.getByRole('button', { name: /^Ajouter$/i }).click();
    await expect(page.getByText(title)).toBeVisible({ timeout: 8_000 });

    // Delete the specific entry (find delete button within that vault-card)
    await page.locator('.vault-card').filter({ hasText: title })
      .locator('button').filter({ has: page.locator('mat-icon', { hasText: 'delete' }) })
      .click();
    await expect(page.getByText(title)).not.toBeVisible({ timeout: 5_000 });
  });

  test('la recherche filtre les entrées', async ({ page }) => {
    const suffix = Date.now();
    for (const title of [`Google_${suffix}`, `Netflix_${suffix}`]) {
      await page.getByRole('button', { name: /nouvelle entrée/i }).click();
      await page.locator('input[title="Titre de l\'entrée"]').fill(title);
      await page.locator('input[type="password"]').fill('pass789');
      await page.getByRole('button', { name: /^Ajouter$/i }).click();
      await expect(page.getByText(title)).toBeVisible({ timeout: 8_000 });
    }

    // Filter by Google — Netflix should disappear
    await page.locator('input[placeholder*="Rechercher"]').fill(`Google_${suffix}`);
    await expect(page.getByText(`Google_${suffix}`)).toBeVisible();
    await expect(page.getByText(`Netflix_${suffix}`)).not.toBeVisible();
  });
});
