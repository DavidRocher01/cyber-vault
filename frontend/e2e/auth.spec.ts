import { test, expect } from '@playwright/test';

test.describe('Parcours Login', () => {
  test('affiche le formulaire de connexion', async ({ page }) => {
    await page.goto('/auth/login');
    await expect(page.getByLabel('Email')).toBeVisible();
    await expect(page.getByLabel('Mot de passe')).toBeVisible();
  });

  test('affiche une erreur avec des identifiants invalides', async ({ page }) => {
    await page.goto('/auth/login');
    await page.getByLabel('Email').fill('inconnu@test.com');
    await page.getByLabel('Mot de passe').fill('mauvais');
    await page.getByRole('button', { name: /se connecter/i }).click();
    await expect(page.getByText(/Invalid credentials|Erreur de connexion/i)).toBeVisible();
  });
});
