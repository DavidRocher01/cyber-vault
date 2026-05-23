import { test, expect } from '@playwright/test';
import { createAndLogin, BASE_PASSWORD } from './helpers';

// ── Affichage formulaires ──────────────────────────────────────────────────────

test.describe('Formulaire de connexion', () => {
  test('affiche le formulaire de connexion', async ({ page }) => {
    await page.goto('/auth/login');
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[autocomplete="current-password"]')).toBeVisible();
    await expect(page.getByRole('button', { name: /se connecter/i })).toBeVisible();
  });

  test('affiche un lien vers l\'inscription', async ({ page }) => {
    await page.goto('/auth/login');
    await expect(page.getByRole('link', { name: /s'inscrire|créer un compte/i })).toBeVisible();
  });

  test('formulaire vide — le bouton submit est désactivé', async ({ page }) => {
    await page.goto('/auth/login');
    await expect(page.getByRole('button', { name: /se connecter/i })).toBeDisabled();
  });

  test('affiche une erreur avec des identifiants invalides', async ({ page }) => {
    await page.goto('/auth/login');
    await page.locator('input[type="email"]').fill('inconnu@test.com');
    await page.locator('input[autocomplete="current-password"]').fill('mauvaisMotDePasse!');
    await page.getByRole('button', { name: /se connecter/i }).click();
    await expect(page.getByText(/Invalid credentials|Erreur de connexion|identifiants|incorrect/i)).toBeVisible({ timeout: 8_000 });
  });
});

// ── Formulaire d'inscription ───────────────────────────────────────────────────

test.describe('Formulaire d\'inscription', () => {
  test('affiche le formulaire d\'inscription', async ({ page }) => {
    await page.goto('/auth/register');
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[autocomplete="new-password"]').first()).toBeVisible();
    await expect(page.getByRole('button', { name: /s'inscrire|créer/i })).toBeVisible();
  });

  test('crée un compte et redirige', async ({ page }) => {
    const email = `e2e_register_${Date.now()}@test.com`;
    await page.goto('/auth/register');
    await page.locator('input[type="email"]').fill(email);
    await page.locator('input[autocomplete="new-password"]').first().fill(BASE_PASSWORD);
    await page.locator('input[autocomplete="new-password"]').last().fill(BASE_PASSWORD);
    await page.getByRole('button', { name: /s'inscrire|créer/i }).click();
    // Après inscription, redirige (vers login ou dashboard)
    await page.waitForURL(url => !url.pathname.includes('/auth/register'), { timeout: 15_000 });
  });

  test('email déjà utilisé — affiche une erreur', async ({ page }) => {
    const email = `e2e_dup_${Date.now()}@test.com`;
    // Premier enregistrement
    await page.goto('/auth/register');
    await page.locator('input[type="email"]').fill(email);
    await page.locator('input[autocomplete="new-password"]').first().fill(BASE_PASSWORD);
    await page.locator('input[autocomplete="new-password"]').last().fill(BASE_PASSWORD);
    await page.getByRole('button', { name: /s'inscrire|créer/i }).click();
    await page.waitForURL(url => !url.pathname.includes('/auth/register'), { timeout: 15_000 });

    // Deuxième enregistrement avec le même email
    await page.goto('/auth/register');
    await page.locator('input[type="email"]').fill(email);
    await page.locator('input[autocomplete="new-password"]').first().fill(BASE_PASSWORD);
    await page.locator('input[autocomplete="new-password"]').last().fill(BASE_PASSWORD);
    await page.getByRole('button', { name: /s'inscrire|créer/i }).click();
    await expect(page.getByText(/déjà utilisé|already|existe/i)).toBeVisible({ timeout: 8_000 });
  });
});

// ── Parcours complet login ─────────────────────────────────────────────────────

test.describe('Parcours login complet', () => {
  test('connexion réussie redirige vers dashboard ou cyberscan', async ({ page }) => {
    await createAndLogin(page);
    await expect(page).toHaveURL(/\/(cyberscan|dashboard)/);
  });

  test('route protégée sans auth redirige vers login', async ({ page }) => {
    await page.goto('/cyberscan/dashboard');
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test('route protégée profile sans auth redirige vers login', async ({ page }) => {
    await page.goto('/cyberscan/profile');
    await expect(page).toHaveURL(/\/auth\/login/);
  });
});

// ── Déconnexion ───────────────────────────────────────────────────────────────

test.describe('Déconnexion', () => {
  test('se déconnecter redirige vers cyberscan', async ({ page }) => {
    await createAndLogin(page);
    // Go to landing page where the user menu with logout is in the nav
    await page.goto('/cyberscan');
    // Open user dropdown (button containing "expand_more" icon text)
    await page.locator('button').filter({ hasText: 'expand_more' }).first().click();
    // Click Déconnexion in the dropdown
    await page.getByRole('button', { name: 'Déconnexion' }).click();
    await page.waitForURL(/\/cyberscan/, { timeout: 8_000 });
  });
});
