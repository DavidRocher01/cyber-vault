import { test, expect } from '@playwright/test';

test.describe('Pages publiques', () => {

  test('landing — titre et CTA visibles', async ({ page }) => {
    await page.goto('/cyberscan');
    await expect(page).toHaveTitle(/CyberScan/i);
    // Le titre principal doit être présent
    await expect(page.getByRole('heading', { level: 1 }).first()).toBeVisible();
  });

  test('landing — lien vers login visible', async ({ page }) => {
    await page.goto('/cyberscan');
    await expect(page.getByRole('link', { name: /connexion|se connecter|login/i }).first()).toBeVisible();
  });

  test('scan gratuit — formulaire de saisie visible', async ({ page }) => {
    await page.goto('/cyberscan/scan-gratuit');
    await expect(page).toHaveTitle(/scan|gratuit/i);
    // Un champ URL ou domaine doit être présent
    const input = page.locator('input[type="text"], input[type="url"], input[placeholder*="domaine"], input[placeholder*="url"]').first();
    await expect(input).toBeVisible();
  });

  test('page CGU accessible', async ({ page }) => {
    await page.goto('/cyberscan/cgu');
    await expect(page).toHaveTitle(/CGU/i);
    await expect(page.getByRole('heading').first()).toBeVisible();
  });

  test('page politique de confidentialité accessible', async ({ page }) => {
    await page.goto('/cyberscan/politique-confidentialite');
    await expect(page.getByRole('heading').first()).toBeVisible();
  });

  test('page mentions légales accessible', async ({ page }) => {
    await page.goto('/cyberscan/mentions-legales');
    await expect(page.getByRole('heading').first()).toBeVisible();
  });

  test('page blog accessible', async ({ page }) => {
    await page.goto('/cyberscan/blog');
    await expect(page).toHaveTitle(/blog/i);
  });

  test('page ressources accessible', async ({ page }) => {
    await page.goto('/cyberscan/ressources');
    await expect(page.getByRole('heading').first()).toBeVisible();
  });

  test('page bonnes pratiques accessible', async ({ page }) => {
    await page.goto('/cyberscan/bonnes-pratiques');
    await expect(page.getByRole('heading').first()).toBeVisible();
  });

  test('calculateur coût cyberattaque accessible', async ({ page }) => {
    await page.goto('/cyberscan/cout-cyberattaque');
    await expect(page.getByRole('heading').first()).toBeVisible();
  });

  test('quiz maturité accessible', async ({ page }) => {
    await page.goto('/cyberscan/quiz-maturite');
    await expect(page.getByRole('heading').first()).toBeVisible();
  });

  test('simulation phishing accessible', async ({ page }) => {
    await page.goto('/cyberscan/simulation-phishing');
    await expect(page.getByRole('heading').first()).toBeVisible();
  });

  test('page contact accessible', async ({ page }) => {
    await page.goto('/cyberscan/contact');
    await expect(page).toHaveTitle(/contact/i);
  });

  test('route inconnue → page 404', async ({ page }) => {
    await page.goto('/cyberscan/cette-page-nexiste-pas-du-tout');
    // La page 404 doit afficher un message ou un lien de retour
    await expect(page.getByRole('heading').first()).toBeVisible();
  });

  test('racine "/" redirige vers /cyberscan', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL(/\/cyberscan/);
  });
});
