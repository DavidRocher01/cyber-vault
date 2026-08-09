import { test, expect, Page } from '@playwright/test';

import { EXCLUES, ecransAtteignables } from './couverture-routes';

/**
 * Recette UI post-prod — parcours critiques en navigateur reel contre le site
 * DEPLOYE. Objectif : detecter ce que la recette API ne voit pas (bundle JS
 * casse, routing SPA HS, mauvaise base URL d'API cote front).
 *
 * Robustesse volontaire : on verifie que ca REND et que l'auth aboutit, sans
 * s'accrocher a des details fragiles — un echec ici provoque un rollback ECS.
 */

const EMAIL = process.env.RECETTE_EMAIL || '';
const PASSWORD = process.env.RECETTE_PASSWORD || '';
const hasCanary = Boolean(EMAIL && PASSWORD);

async function acceptCookies(page: Page): Promise<void> {
  await page.addInitScript(() => localStorage.setItem('cyberscan_cookie_consent', 'accepted'));
}

async function loginCanary(page: Page): Promise<void> {
  await acceptCookies(page);
  await page.goto('/auth/login');
  await page.locator('[formcontrolname="email"]').fill(EMAIL);
  await page.locator('[formcontrolname="password"]').fill(PASSWORD);
  await page.getByRole('button', { name: /se connecter/i }).click();
  await page.waitForURL(url => !url.pathname.startsWith('/auth'), { timeout: 20_000 });
}

test.describe('Recette prod — parcours critiques UI', () => {
  test('la vitrine se charge et Angular rend le contenu', async ({ page }) => {
    const resp = await page.goto('/');
    expect(resp && resp.status(), 'la home doit repondre <400').toBeLessThan(400);
    await expect(page).toHaveTitle(/cyber|s[eé]curit/i);
    // Le bundle Angular a execute et hydrate du contenu (pas une page blanche/erreur).
    await expect(page.locator('body')).toContainText(/s[eé]curit[eé]/i);
  });

  test('connexion canari via UI puis espace authentifie', async ({ page }) => {
    test.skip(!hasCanary, 'RECETTE_EMAIL / RECETTE_PASSWORD absents');
    await loginCanary(page);
    const token = await page.evaluate(() => sessionStorage.getItem('cv_token'));
    expect(token, 'token cv_token absent apres login = auth front cassee').toBeTruthy();
  });

  // LA LISTE DES ECRANS EST DERIVEE DU FICHIER DE ROUTES, pas ecrite a la main.
  //
  // Elle l'etait jusqu'au 2026-08-08, et couvrait 3 ecrans sur 43. Le lot NIS2 a
  // livre deux pages entieres — dont l'une cassee en production — sans que la
  // recette n'en verifie aucune. Rien ne signalait l'absence : une liste ecrite
  // a la main ne proteste jamais de ce qu'elle ne contient pas.
  const ECRANS = ecransAtteignables();
  const A_VISITER = ECRANS.filter(r => !(r in EXCLUES));

  test('la liste des ecrans couverts suit le fichier de routes', () => {
    // CE TEST EST LE FILET, et il vaut autant que la visite elle-meme : il
    // echoue le jour ou quelqu'un ajoute un ecran sans le couvrir ni justifier
    // son absence. C'est exactement ce qui a manque pour NIS2 et ISO.
    expect(
      ECRANS.length,
      'aucune route lue — le fichier de routes a-t-il change de forme ?'
    ).toBeGreaterThan(20);

    // Une exclusion sans route correspondante est un reste a nettoyer.
    const orphelines = Object.keys(EXCLUES).filter(r => !ECRANS.includes(r));
    expect(
      orphelines,
      `exclusions sans route correspondante : ${orphelines.join(', ')}`
    ).toHaveLength(0);

    expect(
      A_VISITER.length,
      'presque tout est exclu — la recette ne verifierait plus grand-chose'
    ).toBeGreaterThan(15);
  });

  // UNE SEULE CONNEXION POUR TOUS LES ECRANS. Un test par page aurait multiplie
  // les connexions et allonge d'autant la porte de rollback, qui bloque la mise
  // en production. On parcourt donc en serie et on COLLECTE : le message final
  // nomme toutes les pages en defaut, pas seulement la premiere.
  test('tous les ecrans rendent apres connexion', async ({ page }) => {
    test.skip(!hasCanary, 'RECETTE_EMAIL / RECETTE_PASSWORD absents');
    test.setTimeout(180_000);

    await loginCanary(page);
    const defauts: string[] = [];

    for (const chemin of A_VISITER) {
      const erreurs: string[] = [];
      const capter = (e: Error) => erreurs.push(String(e));
      page.on('pageerror', capter);
      try {
        await page.goto(chemin, { waitUntil: 'domcontentloaded' });
        // On ne doit PAS avoir ete renvoye vers /auth : le composant s'est
        // charge et la garde a laisse passer.
        const url = new URL(page.url());
        if (url.pathname.startsWith('/auth')) {
          defauts.push(`${chemin} → renvoye vers ${url.pathname}`);
        }
        // Un titre vide trahit un composant qui n'a jamais fini de charger.
        if (!(await page.title())) defauts.push(`${chemin} → sans titre`);
        if (erreurs.length) defauts.push(`${chemin} → ${erreurs.join(' | ').slice(0, 160)}`);
      } catch (e) {
        defauts.push(`${chemin} → ${String(e).slice(0, 160)}`);
      } finally {
        page.off('pageerror', capter);
      }
    }

    expect(defauts, `ecrans en defaut : ${defauts.join(' ; ')}`).toHaveLength(0);
  });
});
