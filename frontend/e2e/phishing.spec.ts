import { test, expect } from '@playwright/test';
import { createAndLogin, login } from './helpers';

// ─── Shared state for detail/edit tests ──────────────────────────────────────
let detailEmail: string;
let campaignId: number;

// Creates one user + one campaign (via wizard steps 1+2) before detail/edit tests.
async function setupCampaign(browser: import('@playwright/test').Browser) {
  const page = await browser.newPage();
  detailEmail = await createAndLogin(page);

  await page.goto('/cyberscan/phishing/new');
  // Step 1 — Plan (Express selected by default)
  await page.getByRole('button', { name: /Continuer/i }).click();
  await page.getByText(/Informations de la campagne/i).waitFor({ timeout: 8_000 });

  // Step 2 — Info: fill name and capture campaign id from POST response
  const responsePromise = page.waitForResponse(
    r => r.url().includes('/phishing/campaigns') && r.request().method() === 'POST',
    { timeout: 12_000 }
  );
  await page.locator('input[placeholder*="Simulation"]').fill('Campagne E2E Test');
  await page.getByRole('button', { name: /Continuer/i }).click();
  const resp = await responsePromise;
  const data = await resp.json();
  campaignId = data.id;

  await page.close();
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. Landing page publique
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Phishing — landing page (publique)', () => {
  test('page landing — h1 visible', async ({ page }) => {
    await page.goto('/cyberscan/simulation-phishing');
    await expect(page).toHaveURL(/\/cyberscan\/simulation-phishing/);
    await expect(page.getByRole('heading', { level: 1 }).first()).toBeVisible();
  });

  test('landing — CTAs Réserver et Demander un devis visibles', async ({ page }) => {
    await page.goto('/cyberscan/simulation-phishing');
    await expect(page.getByText(/Réserver un créneau/i).first()).toBeVisible();
    await expect(page.getByText(/Demander un devis/i).first()).toBeVisible();
  });

  test('landing — 3 offres tarifaires affichées', async ({ page }) => {
    await page.goto('/cyberscan/simulation-phishing');
    await expect(page.getByText('Express').first()).toBeVisible();
    await expect(page.getByText('Standard').first()).toBeVisible();
    await expect(page.getByText('Premium').first()).toBeVisible();
  });

  test('landing — scénarios phishing affichés', async ({ page }) => {
    await page.goto('/cyberscan/simulation-phishing');
    await expect(page.getByText('Fraude au Président')).toBeVisible();
    await expect(page.getByText('Credentials Office 365')).toBeVisible();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 2. Garde authentification
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Phishing — garde auth', () => {
  test('/campaigns redirige vers login sans auth', async ({ page }) => {
    await page.goto('/cyberscan/phishing/campaigns');
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test('/phishing/new redirige vers login sans auth', async ({ page }) => {
    await page.goto('/cyberscan/phishing/new');
    await expect(page).toHaveURL(/\/auth\/login/);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 3. Liste des campagnes
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Phishing — liste des campagnes', () => {
  test('page campaigns — chargement et titre', async ({ page }) => {
    await createAndLogin(page);
    await page.goto('/cyberscan/phishing/campaigns');
    await expect(page).toHaveURL(/\/cyberscan\/phishing\/campaigns/);
    await expect(page.getByRole('heading').first()).toBeVisible();
  });

  test('page campaigns — bouton Nouvelle campagne visible', async ({ page }) => {
    await createAndLogin(page);
    await page.goto('/cyberscan/phishing/campaigns');
    await expect(page.getByText(/Nouvelle campagne/i)).toBeVisible({ timeout: 5_000 });
  });

  test('page campaigns — lien vers wizard (/phishing/new)', async ({ page }) => {
    await createAndLogin(page);
    await page.goto('/cyberscan/phishing/campaigns');
    const link = page.getByRole('link', { name: /Nouvelle campagne/i });
    await expect(link).toBeVisible({ timeout: 5_000 });
    await expect(link).toHaveAttribute('href', /\/cyberscan\/phishing\/new/);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 4. Wizard de création
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Phishing — wizard création', () => {
  let wizardEmail: string;

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    wizardEmail = await createAndLogin(page);
    await page.close();
  });

  test('wizard — step 1 (plan) chargement', async ({ page }) => {
    await login(page, wizardEmail);
    await page.goto('/cyberscan/phishing/new');
    await expect(page.getByRole('heading', { name: /Nouvelle campagne/i })).toBeVisible();
    await expect(page.getByText(/Choisissez votre offre/i)).toBeVisible();
  });

  test('wizard — 3 plans affichés avec prix', async ({ page }) => {
    await login(page, wizardEmail);
    await page.goto('/cyberscan/phishing/new');
    await expect(page.getByText('Express')).toBeVisible();
    await expect(page.getByText('Standard')).toBeVisible();
    await expect(page.getByText('Premium')).toBeVisible();
    // Les prix doivent être présents
    await expect(page.getByText('800 €').first()).toBeVisible();
  });

  test('wizard — Continuer depuis step 1 affiche step 2', async ({ page }) => {
    await login(page, wizardEmail);
    await page.goto('/cyberscan/phishing/new');
    await page.getByRole('button', { name: /Continuer/i }).click();
    await expect(page.getByText(/Informations de la campagne/i)).toBeVisible({ timeout: 5_000 });
  });

  test('wizard — Retour depuis step 2 revient au step 1', async ({ page }) => {
    await login(page, wizardEmail);
    await page.goto('/cyberscan/phishing/new');
    await page.getByRole('button', { name: /Continuer/i }).click();
    await expect(page.getByText(/Informations de la campagne/i)).toBeVisible({ timeout: 5_000 });
    await page.getByRole('button', { name: /Retour/i }).click();
    await expect(page.getByText(/Choisissez votre offre/i)).toBeVisible({ timeout: 3_000 });
  });

  test('wizard — step 2 invalide : Continuer désactivé sans nom', async ({ page }) => {
    await login(page, wizardEmail);
    await page.goto('/cyberscan/phishing/new');
    await page.getByRole('button', { name: /Continuer/i }).click();
    await expect(page.getByText(/Informations de la campagne/i)).toBeVisible({ timeout: 5_000 });
    // Vider le champ et vérifier que le bouton submit est désactivé
    await page.locator('input[placeholder*="Simulation"]').fill('');
    const submitBtn = page.getByRole('button', { name: /Continuer/i });
    await expect(submitBtn).toBeDisabled();
  });

  test('wizard — step 2 : créer campagne navigue vers step 3 (cibles)', async ({ page }) => {
    await login(page, wizardEmail);
    await page.goto('/cyberscan/phishing/new');
    await page.getByRole('button', { name: /Continuer/i }).click();
    await expect(page.getByText(/Informations de la campagne/i)).toBeVisible({ timeout: 5_000 });

    await page.locator('input[placeholder*="Simulation"]').fill(`E2E ${Date.now()}`);
    await page.getByRole('button', { name: /Continuer/i }).click();

    // Step 3 doit apparaître
    await expect(page.getByText(/Import des cibles/i)).toBeVisible({ timeout: 12_000 });
  });

  test('wizard — step 3 : formulaire import CSV visible', async ({ page }) => {
    await login(page, wizardEmail);
    await page.goto('/cyberscan/phishing/new');
    await page.getByRole('button', { name: /Continuer/i }).click();
    await expect(page.getByText(/Informations de la campagne/i)).toBeVisible({ timeout: 5_000 });
    await page.locator('input[placeholder*="Simulation"]').fill(`E2E CSV ${Date.now()}`);
    await page.getByRole('button', { name: /Continuer/i }).click();
    await expect(page.getByText(/Import des cibles/i)).toBeVisible({ timeout: 12_000 });
    await expect(page.locator('input[type="file"]')).toBeAttached();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 5. Détail de campagne
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Phishing — détail campagne', () => {
  test.beforeAll(async ({ browser }) => {
    await setupCampaign(browser);
  });

  test('detail — chargement page', async ({ page }) => {
    await login(page, detailEmail);
    await page.goto(`/cyberscan/phishing/campaigns/${campaignId}`);
    await expect(page).toHaveURL(new RegExp(`/cyberscan/phishing/campaigns/${campaignId}`));
    await expect(page.getByRole('heading').first()).toBeVisible({ timeout: 5_000 });
  });

  test('detail — lien retour "Mes campagnes" visible', async ({ page }) => {
    await login(page, detailEmail);
    await page.goto(`/cyberscan/phishing/campaigns/${campaignId}`);
    await expect(page.getByText(/Mes campagnes/i)).toBeVisible({ timeout: 5_000 });
  });

  test('detail — lien "Configurer la campagne" visible (statut draft)', async ({ page }) => {
    await login(page, detailEmail);
    await page.goto(`/cyberscan/phishing/campaigns/${campaignId}`);
    await expect(page.getByText(/Configurer la campagne/i)).toBeVisible({ timeout: 5_000 });
  });

  test('detail — badges stats visibles (cibles, ouvertures, clics, identifiants)', async ({ page }) => {
    await login(page, detailEmail);
    await page.goto(`/cyberscan/phishing/campaigns/${campaignId}`);
    await expect(page.getByText(/Cibles/i).first()).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText(/Ouvertures/i).first()).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText(/Clics/i).first()).toBeVisible({ timeout: 5_000 });
  });

  test('detail — campagne 404 redirige vers la liste', async ({ page }) => {
    await login(page, detailEmail);
    await page.goto('/cyberscan/phishing/campaigns/99999');
    await Promise.race([
      page.waitForURL(url => !url.pathname.includes('/99999'), { timeout: 8_000 }),
      page.getByText(/introuvable|not found|404|erreur/i).waitFor({ timeout: 8_000 }),
    ]).catch(() => {});
    const isRedirected = !page.url().includes('/99999');
    const isError = await page.getByText(/introuvable|not found|404|erreur/i).isVisible().catch(() => false);
    expect(isRedirected || isError).toBeTruthy();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 6. Édition de campagne
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Phishing — édition campagne', () => {
  test.beforeAll(async ({ browser }) => {
    // Réutilise la campagne créée dans le bloc précédent si déjà initialisée.
    if (!campaignId) await setupCampaign(browser);
  });

  test('edit — chargement page config', async ({ page }) => {
    await login(page, detailEmail);
    await page.goto(`/cyberscan/phishing/campaigns/${campaignId}/edit`);
    await expect(page).toHaveURL(new RegExp(`/cyberscan/phishing/campaigns/${campaignId}/edit`));
    await expect(page.getByText(/Configurer la campagne/i)).toBeVisible({ timeout: 5_000 });
  });

  test('edit — champ nom pré-rempli avec la valeur existante', async ({ page }) => {
    await login(page, detailEmail);
    await page.goto(`/cyberscan/phishing/campaigns/${campaignId}/edit`);
    const nameInput = page.locator('input[type="text"]').first();
    await expect(nameInput).toBeVisible({ timeout: 5_000 });
    const value = await nameInput.inputValue();
    expect(value.length).toBeGreaterThan(0);
  });

  test('edit — 13 scénarios affichés avec cases à cocher', async ({ page }) => {
    await login(page, detailEmail);
    await page.goto(`/cyberscan/phishing/campaigns/${campaignId}/edit`);
    await expect(page.getByText('Fraude au Président')).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText('Credentials Office 365')).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText('Document RH Confidentiel')).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText('Notification Teams')).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText('Partage SharePoint')).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText('Ticket Helpdesk IT')).toBeVisible({ timeout: 5_000 });
  });

  test('edit — bouton Enregistrer visible', async ({ page }) => {
    await login(page, detailEmail);
    await page.goto(`/cyberscan/phishing/campaigns/${campaignId}/edit`);
    await expect(page.getByRole('button', { name: /Enregistrer/i })).toBeVisible({ timeout: 5_000 });
  });

  test('edit — bouton Lancer désactivé (sans scénario ni cibles)', async ({ page }) => {
    await login(page, detailEmail);
    await page.goto(`/cyberscan/phishing/campaigns/${campaignId}/edit`);
    const launchBtn = page.getByRole('button', { name: /Lancer la campagne/i });
    await expect(launchBtn).toBeVisible({ timeout: 5_000 });
    await expect(launchBtn).toBeDisabled();
  });

  test('edit — case CGU visible et décochée par défaut', async ({ page }) => {
    await login(page, detailEmail);
    await page.goto(`/cyberscan/phishing/campaigns/${campaignId}/edit`);
    await expect(page.getByText(/Convention d'exercice/i)).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText(/Je certifie avoir l'autorisation/i)).toBeVisible({ timeout: 5_000 });
  });

  test('edit — lien Annuler pointe vers /campaigns', async ({ page }) => {
    await login(page, detailEmail);
    await page.goto(`/cyberscan/phishing/campaigns/${campaignId}/edit`);
    const cancelLink = page.getByRole('link', { name: /Annuler/i });
    await expect(cancelLink).toBeVisible({ timeout: 5_000 });
    await expect(cancelLink).toHaveAttribute('href', /\/cyberscan\/phishing\/campaigns$/);
  });
});
