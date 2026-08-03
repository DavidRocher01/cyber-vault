import { test, expect } from '@playwright/test';
import { createAndLogin } from './helpers';

/**
 * Garde d'accès au back-office, vue depuis un navigateur.
 *
 * Pourquoi ce fichier existe : jusqu'au 2026-08-02, l'administration s'ouvrait
 * par une clé `X-Admin-Key` saisie à la main — un secret partagé sans identité
 * ni révocation, relevé par l'audit du 2026-07-27. Le droit est désormais porté
 * par un compte (`users.is_admin`).
 *
 * Le remplacement a fait apparaître qu'il existait **trois** portails
 * indépendants : le shell admin, une copie côté serveur dans `admin_quotes`, et
 * la page agenda — cette dernière silencieusement cassée, parce qu'aucun test
 * ne l'ouvrait jamais dans un navigateur. D'où ces scénarios.
 *
 * Ce qui n'est PAS couvert, et c'est délibéré : le back-office une fois dedans.
 * Y accéder demanderait un compte administrateur, donc une route
 * `/dev/become-admin` — qui percerait exactement la propriété qu'on protège :
 * ce droit ne s'accorde par aucune API, seulement en accès direct au conteneur.
 * Si ces écrans devaient bouger souvent, la bonne façon serait de poser le
 * drapeau en base depuis le `globalSetup` de Playwright, jamais par HTTP.
 */

/** Marqueurs du back-office : leur présence signerait une fuite d'accès. */
const MARQUEURS_BACK_OFFICE = ["Vue d'ensemble", 'Acquisition', 'Utilisateurs'];

async function aucunMarqueurDeBackOffice(page: import('@playwright/test').Page) {
  for (const marqueur of MARQUEURS_BACK_OFFICE) {
    await expect(page.getByRole('link', { name: marqueur })).toHaveCount(0);
  }
}

test.describe("Back-office — garde d'accès", () => {
  test('un visiteur anonyme ne voit pas le back-office', async ({ page }) => {
    await page.goto('/admin');

    // L'ecran de refus du shell ne s'affiche PAS ici : l'appel a /users/me
    // repond 401, l'intercepteur echoue a rafraichir la session et renvoie a
    // l'accueil (`router.navigate(['/'])`). On quitte donc /admin avant tout
    // rendu. La propriete qui compte tient quand meme, et c'est elle qu'on
    // verifie — pas le chemin emprunte pour y arriver.
    await expect(page).not.toHaveURL(/\/admin/);
    await aucunMarqueurDeBackOffice(page);
  });

  test('un compte ordinaire connecté est refusé', async ({ page }) => {
    // Le point qui compte : être authentifié ne suffit pas. C'est la seule
    // assertion de sécurité que ce fichier apporte par rapport aux tests d'API.
    await createAndLogin(page);

    await page.goto('/admin');
    await expect(page.getByText(/réservé aux comptes administrateurs/i)).toBeVisible();
    await aucunMarqueurDeBackOffice(page);
  });

  test('la page agenda applique la même garde', async ({ page }) => {
    // Elle a son propre portail, hors du shell : c'est celui qui était cassé
    // sans que personne ne le voie.
    await createAndLogin(page);

    await page.goto('/admin/ba61c5a60113/agenda');
    await expect(page.getByText(/réservé aux comptes administrateurs/i)).toBeVisible();
    // Le contenu de l'agenda ne doit pas apparaître derrière l'écran de refus.
    await expect(page.getByRole('button', { name: /ajouter un créneau/i })).toHaveCount(0);
  });

  test('aucun champ de clé admin ne subsiste', async ({ page }) => {
    // Non-régression du retrait : plus aucun écran ne doit demander de secret
    // partagé, sur aucune des deux entrées.
    await page.goto('/admin');
    await expect(page.locator('input[type="password"]')).toHaveCount(0);

    await page.goto('/admin/ba61c5a60113/agenda');
    await expect(page.locator('input[type="password"]')).toHaveCount(0);
  });
});
