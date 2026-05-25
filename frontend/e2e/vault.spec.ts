import { test, expect } from '@playwright/test';

const EMAIL = `e2e_${Date.now()}@test.com`;
const PASSWORD = 'StrongPass123!';
const MASTER = 'MasterPass456!';

test.describe('Parcours Vault', () => {
  test.describe.configure({ mode: 'serial' });

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    await page.goto('/auth/register');
    await page.locator('[formcontrolname="email"]').fill(EMAIL);
    await page.locator('[formcontrolname="password"]').fill(PASSWORD);
    await page.locator('[formcontrolname="confirmPassword"]').fill(PASSWORD);
    await page.getByRole('button', { name: /créer mon compte/i }).click();
    // On retry, email may already exist — silently continue in that case
    await page.waitForURL(/\/cyberscan/, { waitUntil: 'commit', timeout: 10_000 }).catch(() => {});
    await page.close();
  });

  test.beforeEach(async ({ page }) => {
    await page.goto('/auth/login');
    await page.locator('[formcontrolname="email"]').fill(EMAIL);
    await page.locator('[formcontrolname="password"]').fill(PASSWORD);
    await page.getByRole('button', { name: /se connecter/i }).click();
    await page.waitForURL(/\/cyberscan/, { waitUntil: 'commit' });

    // Accès vault → cryptoGuard redirige vers master-password
    await page.goto('/vault');
    await page.waitForURL(/\/auth\/master-password/);
    await page.locator('[formcontrolname="masterPassword"]').fill(MASTER);
    await page.getByRole('button', { name: /déverrouiller/i }).click();
    await page.waitForURL('**/vault');
  });

  test('affiche le dashboard vault après connexion', async ({ page }) => {
    await expect(page.getByText('Mon Vault')).toBeVisible();
  });

  test('ajoute une nouvelle entrée et la voit dans la liste', async ({ page }) => {
    await page.getByRole('button', { name: /nouvelle entrée/i }).click();
    await page.locator('[formcontrolname="title"]').fill('GitHub');
    await page.locator('[formcontrolname="password_encrypted"]').fill('secret123');
    await page.locator('button[type="submit"]').click();
    await expect(page.getByText('GitHub')).toBeVisible();
  });

  test('supprime une entrée de la liste', async ({ page }) => {
    // Ajouter d'abord
    await page.getByRole('button', { name: /nouvelle entrée/i }).click();
    await page.locator('[formcontrolname="title"]').fill('ASupprimer');
    await page.locator('[formcontrolname="password_encrypted"]').fill('pass456');
    await page.locator('button[type="submit"]').click();
    await expect(page.getByText('ASupprimer')).toBeVisible();

    // Supprimer
    await page.getByTitle('Supprimer').first().click();
    await expect(page.getByText('ASupprimer')).not.toBeVisible();
  });

  test('la recherche filtre les entrées', async ({ page }) => {
    // Ajouter deux entrées
    for (const title of ['Google', 'Netflix']) {
      await page.getByRole('button', { name: /nouvelle entrée/i }).click();
      await page.locator('[formcontrolname="title"]').fill(title);
      await page.locator('[formcontrolname="password_encrypted"]').fill('pass789');
      await page.locator('button[type="submit"]').click();
      await expect(page.getByText(title)).toBeVisible();
    }

    // Filtrer
    await page.getByPlaceholder(/Rechercher un identifiant/i).fill('Google');
    await expect(page.getByText('Google')).toBeVisible();
    await expect(page.getByText('Netflix')).not.toBeVisible();
  });
});
