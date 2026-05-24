import { test, expect } from '@playwright/test';
import { createAndLogin, login } from './helpers';

// ─────────────────────────────────────────────────────────────────────────────
// 1. Garde authentification
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Dark Web — garde auth', () => {
  test('/cyberscan/darkweb redirige vers login sans auth', async ({ page }) => {
    await page.goto('/cyberscan/darkweb');
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test('/cyberscan/darkweb-dossier redirige vers login sans auth', async ({ page }) => {
    await page.goto('/cyberscan/darkweb-dossier');
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test('/cyberscan/darkweb-dossier/new redirige vers login sans auth', async ({ page }) => {
    await page.goto('/cyberscan/darkweb-dossier/new');
    await expect(page).toHaveURL(/\/auth\/login/);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 2. Surveillance Dark Web personnelle
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Dark Web — surveillance personnelle', () => {
  let email: string;

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    email = await createAndLogin(page);
    await page.close();
  });

  test('page darkweb — chargement après login', async ({ page }) => {
    await login(page, email);
    await page.goto('/cyberscan/darkweb');
    await expect(page).toHaveURL(/\/cyberscan\/darkweb/);
    await expect(page.getByRole('heading').first()).toBeVisible({ timeout: 5_000 });
  });

  test('page darkweb — bouton "Vérifier mon email" visible', async ({ page }) => {
    await login(page, email);
    await page.goto('/cyberscan/darkweb');
    await expect(
      page.getByRole('button', { name: /Vérifier|Lancer|Analyser/i }).first()
    ).toBeVisible({ timeout: 5_000 });
  });

  test('page darkweb — adresse email de l\'utilisateur affichée', async ({ page }) => {
    await login(page, email);
    await page.goto('/cyberscan/darkweb');
    await expect(page.getByText(email)).toBeVisible({ timeout: 5_000 });
  });

  test('page darkweb — titre de page correct', async ({ page }) => {
    await login(page, email);
    await page.goto('/cyberscan/darkweb');
    await expect(page).toHaveTitle(/Dark Web|dark web/i);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 3. Dark Web Dossier B2B — liste
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Dark Web Dossier — liste', () => {
  let email: string;

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    email = await createAndLogin(page);
    await page.close();
  });

  test('page dossier — chargement après login', async ({ page }) => {
    await login(page, email);
    await page.goto('/cyberscan/darkweb-dossier');
    await expect(page).toHaveURL(/\/cyberscan\/darkweb-dossier/);
    await expect(page.getByRole('heading').first()).toBeVisible({ timeout: 5_000 });
  });

  test('page dossier — bouton "Nouveau dossier" visible', async ({ page }) => {
    await login(page, email);
    await page.goto('/cyberscan/darkweb-dossier');
    await expect(
      page.getByRole('link', { name: /Nouveau dossier/i }).or(
        page.getByRole('button', { name: /Nouveau dossier/i })
      )
    ).toBeVisible({ timeout: 5_000 });
  });

  test('page dossier — titre de page correct', async ({ page }) => {
    await login(page, email);
    await page.goto('/cyberscan/darkweb-dossier');
    await expect(page).toHaveTitle(/Dossier|dossier/i);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 4. Dark Web Dossier B2B — formulaire de création
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Dark Web Dossier — formulaire nouveau dossier', () => {
  let email: string;

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    email = await createAndLogin(page);
    await page.close();
  });

  test('page /new — chargement du formulaire', async ({ page }) => {
    await login(page, email);
    await page.goto('/cyberscan/darkweb-dossier/new');
    await expect(page).toHaveURL(/\/cyberscan\/darkweb-dossier\/new/);
    await expect(page.getByRole('heading').first()).toBeVisible({ timeout: 5_000 });
  });

  test('formulaire — champ nom de société visible', async ({ page }) => {
    await login(page, email);
    await page.goto('/cyberscan/darkweb-dossier/new');
    await expect(
      page.locator('input').filter({ hasText: '' }).first()
    ).toBeVisible({ timeout: 5_000 });
  });

  test('formulaire — bouton Créer désactivé sans données', async ({ page }) => {
    await login(page, email);
    await page.goto('/cyberscan/darkweb-dossier/new');
    const btn = page.getByRole('button', { name: /Créer|Lancer|Analyser|Soumettre/i }).last();
    await expect(btn).toBeVisible({ timeout: 5_000 });
    await expect(btn).toBeDisabled();
  });

  test('formulaire — bouton Créer toujours désactivé sans fichier CSV', async ({ page }) => {
    await login(page, email);
    await page.goto('/cyberscan/darkweb-dossier/new');
    await page.locator('input').first().fill('Acme SAS');
    await page.locator('input').nth(1).fill('acme.fr');
    const btn = page.getByRole('button', { name: /Créer|Lancer|Analyser|Soumettre/i }).last();
    await expect(btn).toBeDisabled();
  });

  test('formulaire — lien Annuler pointe vers la liste', async ({ page }) => {
    await login(page, email);
    await page.goto('/cyberscan/darkweb-dossier/new');
    const cancelLink = page.getByRole('link', { name: /Annuler|Retour/i }).first();
    await expect(cancelLink).toBeVisible({ timeout: 5_000 });
    await expect(cancelLink).toHaveAttribute('href', /\/cyberscan\/darkweb-dossier$/);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 5. Dashboard — accès aux modules dark web depuis les cartes
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Dashboard — liens quick tools dark web', () => {
  let email: string;

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    email = await createAndLogin(page);
    await page.close();
  });

  test('dashboard — carte "Surveillance Dark Web" visible et lien correct', async ({ page }) => {
    await login(page, email);
    await page.goto('/cyberscan/dashboard');
    const card = page.getByRole('link', { name: /Surveillance Dark Web/i }).or(
      page.getByText(/Surveillance Dark Web/i).first()
    );
    await expect(card).toBeVisible({ timeout: 5_000 });
  });

  test('dashboard — carte "Dark Web Dossier" visible', async ({ page }) => {
    await login(page, email);
    await page.goto('/cyberscan/dashboard');
    const card = page.getByRole('link', { name: /Dark Web Dossier/i }).or(
      page.getByText(/Dark Web Dossier/i).first()
    );
    await expect(card).toBeVisible({ timeout: 5_000 });
  });
});
