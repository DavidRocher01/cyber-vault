import { test, expect } from '@playwright/test';

const EMAIL = `e2e_${Date.now()}@test.com`;
const PASSWORD = 'StrongPass123!';
const MASTER = 'MasterPass456!';

test.describe('Parcours Vault', () => {
  test.beforeEach(async ({ page }) => {
    // Inscription
    await page.goto('/auth/register');
    await page.getByLabel('Email').fill(EMAIL);
    await page.getByLabel('Mot de passe').fill(PASSWORD);
    await page.getByRole('button', { name: /s'inscrire/i }).click();

    // Connexion
    await page.goto('/auth/login');
    await page.getByLabel('Email').fill(EMAIL);
    await page.getByLabel('Mot de passe').fill(PASSWORD);
    await page.getByRole('button', { name: /se connecter/i }).click();

    // Mot de passe maître
    await page.waitForURL('**/auth/master-password');
    await page.getByLabel('Mot de passe maître').fill(MASTER);
    await page.getByRole('button', { name: /déverrouiller/i }).click();
    await page.waitForURL('**/vault');
  });

  test('affiche le dashboard vault après connexion', async ({ page }) => {
    await expect(page.getByText('Mon Vault')).toBeVisible();
  });

  test('ajoute une nouvelle entrée et la voit dans la liste', async ({ page }) => {
    await page.getByRole('button', { name: /nouvelle entrée/i }).click();
    await page.getByLabel('Titre').fill('GitHub');
    await page.getByLabel('Mot de passe').fill('secret123');
    await page.getByRole('button', { name: /enregistrer/i }).click();
    await expect(page.getByText('GitHub')).toBeVisible();
  });

  test('supprime une entrée de la liste', async ({ page }) => {
    // Ajouter d'abord
    await page.getByRole('button', { name: /nouvelle entrée/i }).click();
    await page.getByLabel('Titre').fill('ASupprimer');
    await page.getByLabel('Mot de passe').fill('pass456');
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
      await page.getByLabel('Titre').fill(title);
      await page.getByLabel('Mot de passe').fill('pass789');
      await page.getByRole('button', { name: /enregistrer/i }).click();
      await expect(page.getByText(title)).toBeVisible();
    }

    // Filtrer
    await page.getByLabel('Rechercher').fill('Google');
    await expect(page.getByText('Google')).toBeVisible();
    await expect(page.getByText('Netflix')).not.toBeVisible();
  });
});
