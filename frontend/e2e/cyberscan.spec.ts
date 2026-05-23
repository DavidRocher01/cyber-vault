import { test, expect } from '@playwright/test';
import { createAndLogin } from './helpers';

// Chaque test crée son propre compte pour l'isolation.

test.describe('Dashboard CyberScan', () => {
  test('dashboard — chargement et titre', async ({ page }) => {
    await createAndLogin(page);
    await page.goto('/cyberscan/dashboard');
    await expect(page).toHaveURL(/\/cyberscan\/dashboard/);
    await expect(page.getByRole('heading').first()).toBeVisible();
  });

  test('dashboard — nav-buttons présents', async ({ page }) => {
    await createAndLogin(page);
    await page.goto('/cyberscan/dashboard');
    // Le composant NavButtons doit rendre au moins un lien de navigation
    await expect(page.getByRole('link').first()).toBeVisible();
  });
});

test.describe('Profil utilisateur', () => {
  test('page profil — chargement', async ({ page }) => {
    await createAndLogin(page);
    await page.goto('/cyberscan/profile');
    await expect(page).toHaveURL(/\/cyberscan\/profile/);
    await expect(page.getByRole('heading').first()).toBeVisible();
  });

  test('page profil — affiche l\'email de l\'utilisateur', async ({ page }) => {
    const email = await createAndLogin(page);
    await page.goto('/cyberscan/profile');
    await expect(page.getByText(email)).toBeVisible({ timeout: 5_000 });
  });
});

test.describe('URL Scanner', () => {
  test('page URL scanner — formulaire visible', async ({ page }) => {
    await createAndLogin(page);
    await page.goto('/cyberscan/url-scanner');
    await expect(page).toHaveURL(/\/cyberscan\/url-scanner/);
    // Un champ de saisie URL doit être présent
    const input = page.locator('input[type="text"], input[type="url"]').first();
    await expect(input).toBeVisible();
  });

  test('URL scanner — soumettre une URL déclenche un scan', async ({ page }) => {
    await createAndLogin(page);
    await page.goto('/cyberscan/url-scanner');
    const input = page.locator('input[type="text"], input[type="url"]').first();
    await input.fill('https://example.com');
    await page.getByRole('button', { name: /analyser|scanner|lancer|vérifier/i }).click();
    // L'interface doit montrer un état de chargement ou de résultat
    await expect(
      page.getByText(/analyse|scan|résultat|chargement|erreur/i).first()
    ).toBeVisible({ timeout: 15_000 });
  });
});

test.describe('Conformité NIS2', () => {
  test('page NIS2 — chargement', async ({ page }) => {
    await createAndLogin(page);
    await page.goto('/cyberscan/nis2');
    await expect(page).toHaveURL(/\/cyberscan\/nis2/);
    await expect(page.getByRole('heading').first()).toBeVisible();
  });

  test('NIS2 — items de conformité affichés', async ({ page }) => {
    await createAndLogin(page);
    await page.goto('/cyberscan/nis2');
    // La page doit afficher des items de conformité (checkboxes ou labels)
    await expect(
      page.locator('mat-checkbox, input[type="checkbox"], .compliance-item, [class*="item"]').first()
    ).toBeVisible({ timeout: 5_000 });
  });
});

test.describe('Conformité ISO 27001', () => {
  test('page ISO 27001 — chargement', async ({ page }) => {
    await createAndLogin(page);
    await page.goto('/cyberscan/iso27001');
    await expect(page).toHaveURL(/\/cyberscan\/iso27001/);
    await expect(page.getByRole('heading').first()).toBeVisible();
  });
});

test.describe('PCA Light', () => {
  test('page PCA — formulaire visible', async ({ page }) => {
    await createAndLogin(page);
    await page.goto('/cyberscan/pca');
    await expect(page).toHaveURL(/\/cyberscan\/pca/);
    // PCA uses a <span> for the title, not <h1>
    await expect(page.getByText('PCA Light').first()).toBeVisible();
  });
});

test.describe('Dark Web', () => {
  test('page dark web — chargement', async ({ page }) => {
    await createAndLogin(page);
    await page.goto('/cyberscan/darkweb');
    await expect(page).toHaveURL(/\/cyberscan\/darkweb/);
    // Dark Web uses a <span> for the title, not <h1>
    await expect(page.getByText('Dark Web').first()).toBeVisible();
  });
});

test.describe('Sensibilisation', () => {
  test('page sensibilisation — chargement', async ({ page }) => {
    await createAndLogin(page);
    await page.goto('/cyberscan/sensibilisation');
    await expect(page).toHaveURL(/\/cyberscan\/sensibilisation/);
    // Sensibilisation uses a <span> for the title, not <h1>
    await expect(page.getByText('Sensibilisation').first()).toBeVisible();
  });
});

test.describe('Analyse de code', () => {
  test('page code-scan — chargement', async ({ page }) => {
    await createAndLogin(page);
    await page.goto('/cyberscan/code-scan');
    await expect(page).toHaveURL(/\/cyberscan\/code-scan/);
    await expect(page.getByRole('heading').first()).toBeVisible();
  });
});

test.describe('Factures', () => {
  test('page factures — chargement', async ({ page }) => {
    await createAndLogin(page);
    await page.goto('/cyberscan/factures');
    await expect(page).toHaveURL(/\/cyberscan\/factures/);
    await expect(page.getByRole('heading').first()).toBeVisible();
  });
});

test.describe('Phishing — campagnes', () => {
  test('page campagnes phishing — chargement', async ({ page }) => {
    await createAndLogin(page);
    await page.goto('/cyberscan/phishing/campaigns');
    await expect(page).toHaveURL(/\/cyberscan\/phishing\/campaigns/);
    await expect(page.getByRole('heading').first()).toBeVisible();
  });
});
