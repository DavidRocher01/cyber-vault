import { test, expect } from '@playwright/test';
import { createAndLogin, login, becomeConsultant, createClientAndInvite, PASSWORD } from './helpers';

/**
 * E2E du module RSSI externalisé (consultant + portail client).
 * Couvre : création client via le formulaire refondu, ouverture de la fiche,
 * et le parcours critique invitation → activation → connexion → routage par rôle
 * vers /espace-client, plus l'isolation du portail.
 *
 * Prérequis backend : DEV_MODE actif (APP_ENV=development) pour /dev/become-consultant
 * et l'exposition du lien d'activation par l'endpoint invite.
 */

test.describe('RSSI externalisé — consultant', () => {
  test('crée un client via le formulaire et le voit dans la liste', async ({ page }) => {
    await createAndLogin(page);
    await becomeConsultant(page);

    await page.goto('/consultant');
    // Onglet "Clients"
    await page.getByRole('button').filter({ hasText: 'Clients' }).first().click();
    // Ouvre le formulaire de création (le bouton d'en-tête ; l'état vide en a un 2e)
    await page.getByRole('button', { name: /ajouter un client/i }).first().click();

    const name = `Acme E2E ${Date.now()}`;
    // Form d'edition inactif -> le champ name et le submit du form d'ajout sont uniques
    await page.locator('[formcontrolname="name"]').fill(name);
    await page.locator('button[type="submit"]').click();

    // exact: true -> cible l'item de liste, pas le toast « Client "…" ajouté »
    await expect(page.getByText(name, { exact: true })).toBeVisible({ timeout: 10_000 });
  });

  test('ouvrir la fiche client affiche les actions et onglets', async ({ page }) => {
    await createAndLogin(page);
    await becomeConsultant(page);

    const email = `e2e_fiche_${Date.now()}@test.com`;
    const { clientId } = await createClientAndInvite(page, email, 'Fiche E2E');

    await page.goto(`/consultant/clients/${clientId}`);
    await expect(page).toHaveURL(new RegExp(`/consultant/clients/${clientId}`));
    await expect(page.getByText('Fiche E2E').first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole('button', { name: /inviter le client/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /générer le rapport pdf/i })).toBeVisible();
  });
});

test.describe('RSSI externalisé — portail client', () => {
  test('invitation → activation → connexion → atterrit sur /espace-client', async ({ page }) => {
    // 1. Consultant : crée un client et l'invite (setup via API)
    await createAndLogin(page);
    await becomeConsultant(page);
    const clientEmail = `e2e_portal_${Date.now()}@test.com`;
    const { activationPath } = await createClientAndInvite(page, clientEmail, 'Portail E2E');

    // 2. Activation : la page d'invitation affiche le libellé adapté (pas "réinitialisation")
    await page.goto(activationPath);
    await expect(
      page.getByRole('heading', { name: /activez votre espace client/i })
    ).toBeVisible();
    await page.locator('[formcontrolname="password"]').fill(PASSWORD);
    await page.locator('[formcontrolname="confirmPassword"]').fill(PASSWORD);
    await page.getByRole('button', { name: /enregistrer le mot de passe/i }).click();
    await expect(page.getByText(/votre espace est prêt/i)).toBeVisible({ timeout: 10_000 });

    // 3. Connexion du client → routage par rôle → /espace-client (sans returnUrl explicite)
    await login(page, clientEmail);
    await expect(page).toHaveURL(/\/espace-client/);

    // 4. Le portail affiche les infos du client + son consultant (lecture seule)
    await expect(page.getByText(/mon espace sécurité/i)).toBeVisible();
    await expect(page.getByRole('heading', { name: /portail e2e/i })).toBeVisible();
    await expect(page.getByText(/votre rssi dédié/i)).toBeVisible();
  });

  test('isolation : un compte sans lien client ne peut pas accéder à /espace-client', async ({
    page,
  }) => {
    await createAndLogin(page); // simple utilisateur, non rattaché à un client
    await page.goto('/espace-client');
    // rssiClientGuard : /portal/me renvoie 403 → redirection hors du portail
    await page.waitForURL((url) => !url.pathname.includes('espace-client'), { timeout: 10_000 });
    await expect(page.getByText(/mon espace sécurité/i)).toHaveCount(0);
  });
});
