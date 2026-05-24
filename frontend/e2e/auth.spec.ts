import { test, expect } from '@playwright/test';

test.describe('Parcours Login', () => {
  test('affiche le formulaire de connexion', async ({ page }) => {
    await page.goto('/auth/login');
    await expect(page.locator('[formcontrolname="email"]')).toBeVisible();
    await expect(page.locator('[formcontrolname="password"]')).toBeVisible();
  });

  test('affiche une erreur avec des identifiants invalides', async ({ page }) => {
    await page.goto('/auth/login');
    await page.locator('[formcontrolname="email"]').fill('inconnu@test.com');
    await page.locator('[formcontrolname="password"]').fill('mauvais');
    await page.getByRole('button', { name: /se connecter/i }).click();
    await expect(page.getByText(/Invalid credentials|Erreur de connexion/i)).toBeVisible();
  });
});
