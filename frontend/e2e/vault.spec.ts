import { test, expect } from '@playwright/test';

const EMAIL = `e2e_${Date.now()}@test.com`;
const PASSWORD = 'StrongPass123!';
const MASTER = 'MasterPass456!';

test.describe('Parcours Vault', () => {
  test.beforeEach(async ({ page }) => {
    // Inscription
    await page.goto('/auth/register');
    await page.locator('[formcontrolname="email"]').fill(EMAIL);
    await page.locator('[formcontrolname="password"]').fill(PASSWORD);
    await page.locator('[formcontrolname="confirmPassword"]').fill(PASSWORD);
    await page.getByRole('button', { name: /créer mon compte/i }).click();

    // Connexion
    await page.goto('/auth/login');
    await page.locator('[formcontrolname="email"]').fill(EMAIL);
    await page.locator('[formcontrolname="password"]').fill(PASSWORD);
    await page.getByRole('button', { name: /se connecter/i }).click();

    // Mot de passe maître
    await page.waitForURL('**/auth/master-password');
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
    await page.locator('[formcontrolname="password"]').fill('secret123');
    await page.getByRole('button', { name: /enregistrer/i }).click();
    await expect(page.getByText('GitHub')).toBeVisible();
  });

  test('supprime une entrée de la liste', async ({ page }) => {
    // Ajouter d'abord
    await page.getByRole('button', { name: /nouvelle entrée/i }).click();
    await page.locator('[formcontrolname="title"]').fill('ASupprimer');
    await page.locator('[formcontrolname="password"]').fill('pass456');
    await page.getByRole('button', { name: /enregistrer/i }).click();
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
      await page.locator('[formcontrolname="password"]').fill('pass789');
      await page.getByRole('button', { name: /enregistrer/i }).click();
      await expect(page.getByText(title)).toBeVisible();
    }

    // Filtrer
    await page.getByPlaceholder(/Rechercher un identifiant/i).fill('Google');
    await expect(page.getByText('Google')).toBeVisible();
    await expect(page.getByText('Netflix')).not.toBeVisible();
  });
});
