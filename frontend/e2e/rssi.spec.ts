import { test, expect } from '@playwright/test';
import {
  createAndLogin,
  login,
  becomeConsultant,
  createClientAndInvite,
  PASSWORD,
} from './helpers';

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
    await page
      .getByRole('button', { name: /ajouter un client/i })
      .first()
      .click();

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
    await expect(page.getByRole('heading', { name: /activez votre espace client/i })).toBeVisible();
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

  test('le client dépose un document, le consultant le reçoit marqué « Du client »', async ({
    page,
  }) => {
    // LE PARCOURS COMPLET DE L'ÉTAPE 3, de bout en bout et dans un vrai
    // navigateur. Les tests unitaires couvrent les méthodes, les tests d'API
    // couvrent le serveur — aucun des deux ne compile le gabarit ni ne prouve
    // que le fichier part réellement. C'est le seul test qui le fasse.
    //
    // CE QU'IL NE COUVRE PAS, ET POURQUOI : les états `en_analyse` / `rejete` /
    // `indetermine`. En CI, `ANTIVIRUS_DEPOT_ACTIF` est faux — sans bucket S3 il
    // n'y a pas de balise à relire, et un dépôt y resterait bloqué jusqu'au
    // renoncement. Ces états sont couverts par les tests unitaires du composant.

    // 1. Le consultant crée un client et l'invite
    const consultantEmail = await createAndLogin(page);
    await becomeConsultant(page);
    const clientEmail = `e2e_depot_${Date.now()}@test.com`;
    const { clientId, activationPath } = await createClientAndInvite(
      page,
      clientEmail,
      'Dépôt E2E'
    );

    // 2. Le client active son accès
    await page.goto(activationPath);
    await page.locator('[formcontrolname="password"]').fill(PASSWORD);
    await page.locator('[formcontrolname="confirmPassword"]').fill(PASSWORD);
    await page.getByRole('button', { name: /enregistrer le mot de passe/i }).click();
    await expect(page.getByText(/votre espace est prêt/i)).toBeVisible({ timeout: 10_000 });

    // 3. Il se connecte et arrive sur son portail
    await login(page, clientEmail);
    await expect(page).toHaveURL(/\/espace-client/);

    // 4. La zone de dépôt est VISIBLE sans rien avoir à chercher — c'est tout
    //    l'intérêt de l'option retenue : un client qui ignore qu'il peut
    //    remettre un document ne le remettra pas.
    const zone = page.getByText(/glissez un document, ou parcourez vos fichiers/i);
    await expect(zone).toBeVisible({ timeout: 15_000 });

    // Le quota est annoncé AVANT de devenir un refus.
    await expect(page.getByText(/espace utilisé/i)).toBeVisible();

    // 5. Il dépose un vrai fichier
    await page.locator('input[type="file"]').setInputFiles({
      name: 'politique-mots-de-passe.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 politique de mots de passe'),
    });

    // Le nom du fichier sert de titre par défaut : le client n'a rien à saisir.
    const titre = page.getByPlaceholder(/intitulé du document/i);
    await expect(titre).toHaveValue(/politique-mots-de-passe/);
    await titre.fill('Politique de mots de passe');

    await page.getByRole('button', { name: /^transmettre$/i }).click();

    // 6. Le document apparaît dans SA liste, marqué comme venant de lui
    await expect(page.getByText('Politique de mots de passe').first()).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByText(/^Vous$/).first()).toBeVisible();

    // La zone de dépôt est revenue à son état initial : prête pour le suivant.
    await expect(zone).toBeVisible();

    // 7. LE CONSULTANT LE REÇOIT. Sans ça, la fonctionnalité ne sert à rien :
    //    remettre un document que personne ne voit arriver n'est pas le remettre.
    await login(page, consultantEmail);
    await page.goto(`/consultant/clients/${clientId}`);
    await page
      .getByText(/livrables/i)
      .first()
      .click();
    await expect(page.getByText('Politique de mots de passe').first()).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByText(/du client/i).first()).toBeVisible();
  });

  test('isolation : un compte sans lien client ne peut pas accéder à /espace-client', async ({
    page,
  }) => {
    await createAndLogin(page); // simple utilisateur, non rattaché à un client
    await page.goto('/espace-client');
    // rssiClientGuard : /portal/me renvoie 403 → redirection hors du portail
    await page.waitForURL(url => !url.pathname.includes('espace-client'), { timeout: 10_000 });
    await expect(page.getByText(/mon espace sécurité/i)).toHaveCount(0);
  });
});
