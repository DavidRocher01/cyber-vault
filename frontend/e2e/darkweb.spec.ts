import { test, expect } from '@playwright/test';
import { createAndLogin, login } from './helpers';

// ─────────────────────────────────────────────────────────────────────────────
// 1. Garde authentification
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Dark Web — garde auth', () => {
  test('/darkweb redirige vers login sans auth', async ({ page }) => {
    await page.goto('/darkweb');
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test('/darkweb-dossier redirige vers login sans auth', async ({ page }) => {
    await page.goto('/darkweb-dossier');
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test('/darkweb-dossier/new redirige vers login sans auth', async ({ page }) => {
    await page.goto('/darkweb-dossier/new');
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
    await page.goto('/darkweb');
    await expect(page).toHaveURL(/\/darkweb/);
    // Le titre utilise un <span>, pas un heading — on vérifie le badge toujours visible
    await expect(page.getByText('SURVEILLANCE').first()).toBeVisible({ timeout: 10_000 });
  });

  test('page darkweb — bouton "Vérifier mon email" visible', async ({ page }) => {
    await login(page, email);
    await page.goto('/darkweb');
    await expect(
      page.getByRole('button', { name: /Vérifier|Lancer|Analyser/i }).first()
    ).toBeVisible({ timeout: 15_000 });
  });

  test('page darkweb — adresse email de l\'utilisateur affichée', async ({ page }) => {
    await login(page, email);
    await page.goto('/darkweb');
    await expect(page.getByText(email)).toBeVisible({ timeout: 15_000 });
  });

  test('page darkweb — titre de page correct', async ({ page }) => {
    await login(page, email);
    await page.goto('/darkweb');
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
    await page.goto('/darkweb-dossier');
    await expect(page).toHaveURL(/\/darkweb-dossier/);
    // <h2> n'apparaît qu'après chargement (état vide) — attendre plus longtemps en CI
    await expect(page.getByRole('heading').first()).toBeVisible({ timeout: 15_000 });
  });

  test('page dossier — bouton "Nouveau dossier" visible', async ({ page }) => {
    await login(page, email);
    await page.goto('/darkweb-dossier');
    await expect(
      page.getByRole('link', { name: /Nouveau dossier/i }).or(
        page.getByRole('button', { name: /Nouveau dossier/i })
      )
    ).toBeVisible({ timeout: 10_000 });
  });

  test('page dossier — titre de page correct', async ({ page }) => {
    await login(page, email);
    await page.goto('/darkweb-dossier');
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
    await page.goto('/darkweb-dossier/new');
    await expect(page).toHaveURL(/\/darkweb-dossier\/new/);
    await expect(page.getByRole('heading').first()).toBeVisible({ timeout: 10_000 });
  });

  test('formulaire — champ nom de société visible', async ({ page }) => {
    await login(page, email);
    await page.goto('/darkweb-dossier/new');
    await expect(
      page.locator('input').filter({ hasText: '' }).first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test('formulaire — bouton Créer désactivé sans données', async ({ page }) => {
    await login(page, email);
    await page.goto('/darkweb-dossier/new');
    const btn = page.getByRole('button', { name: /Créer|Lancer|Analyser|Soumettre/i }).last();
    await expect(btn).toBeVisible({ timeout: 10_000 });
    await expect(btn).toBeDisabled();
  });

  test('formulaire — bouton Créer toujours désactivé sans fichier CSV', async ({ page }) => {
    await login(page, email);
    await page.goto('/darkweb-dossier/new');
    await page.locator('input').first().fill('Acme SAS');
    await page.locator('input').nth(1).fill('acme.fr');
    const btn = page.getByRole('button', { name: /Créer|Lancer|Analyser|Soumettre/i }).last();
    await expect(btn).toBeDisabled();
  });

  test('formulaire — lien Annuler pointe vers la liste', async ({ page }) => {
    await login(page, email);
    await page.goto('/darkweb-dossier/new');
    const cancelLink = page.getByRole('link', { name: /Annuler|Retour/i }).first();
    await expect(cancelLink).toBeVisible({ timeout: 10_000 });
    await expect(cancelLink).toHaveAttribute('href', /\/darkweb-dossier$/);
  });
});
