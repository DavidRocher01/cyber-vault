import { test, expect, Page } from '@playwright/test';

/**
 * CE QUE CES TESTS DEFENDENT : un formulaire qui S'AFFICHE doit ACCEPTER la
 * saisie. Pas trois secondes plus tard — tout de suite.
 *
 * LE DEFAUT QU'ILS REPRODUISENT. Le 2026-08-09, le prerendu a mis en
 * production des pages qui s'affichaient avant d'etre hydratees, donc avant
 * d'etre interactives. Ce qui etait tape pendant cette fenetre etait ecrit
 * dans le DOM sans qu'Angular le voie : le formulaire restait invalide et son
 * bouton grise. La connexion etait cassee pour qui tapait vite.
 *
 * POURQUOI ILS VIVENT ICI ET PAS DANS `e2e/`. La suite normale tape
 * `ng serve`, ou le formulaire n'apparait qu'une fois Angular demarre : la
 * fenetre n'existe pas, et le defaut est INVISIBLE. Il ne se voit que sur le
 * build de production, servi comme le CDN le sert.
 *
 * ON NE TEMPORISE JAMAIS AVANT DE SAISIR. C'est tout le propos : `fill` part
 * des que le champ existe. Ajouter une attente ici rendrait ces tests verts
 * sur le defaut meme qu'ils existent pour attraper.
 */

const MDP = 'MotDePasseAssezLong123!';

async function ouvrir(page: Page, chemin: string) {
  await page.addInitScript(() => localStorage.setItem('cyberscan_cookie_consent', 'accepted'));
  await page.goto(chemin, { waitUntil: 'domcontentloaded' });
}

test.describe('Le build de production accepte la saisie des son affichage', () => {
  test('connexion : le bouton s\'active meme si l\'on tape immediatement', async ({ page }) => {
    await ouvrir(page, '/auth/login');

    await page.locator('[formcontrolname="email"]').fill('essai@exemple.fr');
    await page.locator('[formcontrolname="password"]').fill(MDP);

    // Le champ garde bien sa valeur — verifie en rallumant le prerendu, ou
    // cette ligne PASSE pendant que la suivante tombe. C'est ce qui rend le
    // defaut si trompeur : rien ne disparait a l'ecran, Angular n'a
    // simplement jamais vu la saisie. D'ou l'interet de garder les deux
    // assertions : la premiere situe le defaut, la seconde le prouve.
    await expect(page.locator('[formcontrolname="email"]')).toHaveValue('essai@exemple.fr');
    await expect(page.getByRole('button', { name: /se connecter/i })).toBeEnabled();
  });

  test('inscription : le bouton s\'active meme si l\'on tape immediatement', async ({ page }) => {
    await ouvrir(page, '/auth/register');

    await page.locator('[formcontrolname="email"]').fill('essai@exemple.fr');
    await page.locator('[formcontrolname="password"]').fill(MDP);
    await page.locator('[formcontrolname="confirmPassword"]').fill(MDP);

    await expect(page.locator('[formcontrolname="email"]')).toHaveValue('essai@exemple.fr');
    await expect(page.locator('button[type="submit"]')).toBeEnabled();
  });
});

test.describe('Le build de production est servi sur les bons chemins', () => {
  // Un lien profond doit rendre SA page. Le 2026-08-08, une declaration de
  // prerendu posee au mauvais endroit faisait repondre 302 vers `/` a `/nis2`
  // et `/darkweb` : neuf tests e2e sont tombes d'un coup.
  for (const chemin of ['/', '/nis2', '/scan-gratuit', '/blog']) {
    test(`${chemin} rend sa propre page`, async ({ page }) => {
      const reponse = await page.goto(chemin, { waitUntil: 'domcontentloaded' });

      expect(reponse?.status()).toBe(200);
      expect(new URL(page.url()).pathname).toBe(chemin);
      await expect(page.locator('app-root')).not.toBeEmpty();
    });
  }

  test('une URL inconnue retombe sur l\'application, pas sur un 404 brut', async ({ page }) => {
    const reponse = await page.goto('/cette-page-n-existe-pas', { waitUntil: 'domcontentloaded' });

    expect(reponse?.status()).toBe(200);
    await expect(page.locator('app-root')).not.toBeEmpty();
  });
});
