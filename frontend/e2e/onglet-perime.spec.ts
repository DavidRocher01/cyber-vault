import { test, expect, Page } from '@playwright/test';

import { createAndLogin } from './helpers';

/**
 * L'ONGLET RESTÉ OUVERT PENDANT UN DÉPLOIEMENT.
 *
 * CE DÉFAUT A ÉTÉ VU EN PRODUCTION LE 2026-08-07, et par personne d'autre qu'un
 * humain qui cliquait. Le mécanisme :
 *
 *   1. le déploiement fait `aws s3 sync --delete` — les fichiers dont
 *      l'empreinte a changé sont SUPPRIMÉS ;
 *   2. les pages sont chargées à la demande (`loadComponent`) ;
 *   3. un onglet ouvert avant la bascule demande des morceaux qui n'existent
 *      plus ;
 *   4. sans gestion de `ChunkLoadError`, le routeur annule la navigation en
 *      silence — le clic paraît simplement mort.
 *
 * POURQUOI AUCUNE RECETTE NE POUVAIT L'ATTRAPER. La recette
 * post-mise-en-production part toujours d'une session NEUVE : elle charge
 * l'`index.html` courant, donc les bonnes empreintes, et ne voit jamais le
 * problème. Il faut un onglet chargé AVANT la bascule — un état qu'on ne peut
 * pas observer après coup. On ne l'observe donc pas : ON LE SIMULE.
 *
 * DEUX ERREURS COMMISES EN ÉCRIVANT CE FICHIER, gardées ici parce qu'elles
 * disent comment le test doit être lu :
 *
 * 1. La première version appelait `page.goto()`. C'est une navigation COMPLÈTE :
 *    l'application se recharge, et si ses morceaux sont bloqués elle ne démarre
 *    jamais — aucun gestionnaire n'existe alors pour réagir. Le test échouait en
 *    accusant le correctif. Le vrai scénario est un CLIC dans une application
 *    DÉJÀ CHARGÉE.
 *
 * 2. La deuxième cliquait une carte du tableau de bord, invisible pour un compte
 *    neuf — toute cette section est derrière `@if (sites().length > 0)`, et un
 *    compte sans site est de toute façon renvoyé vers `/onboarding`. Un des deux
 *    tests PASSAIT alors À VIDE : son clic ne trouvait rien, l'échec était avalé,
 *    et le marqueur venait d'ailleurs.
 *
 * D'où la forme retenue : on vérifie que le lien EXISTE avant de couper quoi que
 * ce soit. Un lien absent doit faire échouer le test bruyamment, jamais le faire
 * passer par accident.
 */

const MARQUEUR = 'rechargement-module-manquant';

/** Le logo de marque, présent sur toutes les pages, pointe vers `/` — une route
 *  paresseuse. C'est le seul lien interne dont la présence ne dépend ni du plan,
 *  ni des données du compte, ni de l'écran où l'on se trouve. */
const LIEN = 'a[href="/"]';

/** Coupe l'accès aux morceaux pas encore téléchargés — l'état exact d'un onglet
 *  ouvert pendant une bascule. 403 est ce que S3 répond pour un objet supprimé. */
async function couperLesMorceaux(page: Page): Promise<void> {
  await page.route('**/chunk-*.js', route => route.fulfill({ status: 403, body: '' }));
}

async function marqueur(page: Page): Promise<string | null> {
  return page.evaluate(k => sessionStorage.getItem(k), MARQUEUR).catch(() => null);
}

/** Le clic est INTERROMPU par le rechargement qu'on attend, et Playwright le
 *  signale en expirant. C'est le résultat recherché : on ignore l'issue du clic
 *  et on juge sur la trace laissée. La visibilité ayant été vérifiée juste
 *  avant, ce `catch` ne peut plus masquer un lien absent. */
async function cliquerSansAttendre(page: Page): Promise<void> {
  await page
    .locator(LIEN)
    .first()
    .click({ timeout: 5000 })
    .catch(() => {});
}

test.describe('Onglet périmé par un déploiement', () => {
  test('un clic vers une page absente du bundle recharge, au lieu de rester mort', async ({
    page,
  }) => {
    await createAndLogin(page);
    // L'application est chargée et rendue : c'est l'onglet resté ouvert.
    await expect(page.locator(LIEN).first()).toBeVisible();

    await couperLesMorceaux(page);
    await cliquerSansAttendre(page);

    await expect
      .poll(() => marqueur(page), {
        message: 'aucun rechargement : le clic serait resté mort',
        timeout: 20_000,
      })
      .toBe('1');
  });

  test('NE BOUCLE PAS quand le morceau reste introuvable', async ({ page }) => {
    // LE RISQUE INVERSE, et il est pire que le défaut d'origine : si le morceau
    // manque pour une autre raison qu'un bundle périmé, recharger à chaque fois
    // enfermerait l'utilisateur dans une page qui clignote indéfiniment.
    await createAndLogin(page);
    await expect(page.locator(LIEN).first()).toBeVisible();

    await couperLesMorceaux(page);
    await cliquerSansAttendre(page);
    await expect.poll(() => marqueur(page), { timeout: 20_000 }).toBe('1');

    // Le garde-fou survit au rechargement : plus aucun ne doit se produire.
    let apres = 0;
    page.on('framenavigated', frame => {
      if (frame === page.mainFrame()) apres += 1;
    });
    await page.waitForTimeout(5000);

    expect(apres, 'la page se recharge en boucle').toBeLessThanOrEqual(1);
  });

  test('une erreur applicative ordinaire ne déclenche aucun rechargement', async ({ page }) => {
    // Le gestionnaire ne doit pas être un attrape-tout : avaler les autres
    // erreurs priverait la console des pannes réelles.
    await createAndLogin(page);

    await page.evaluate(() => {
      window.dispatchEvent(
        new ErrorEvent('error', { error: new Error('Cannot read properties of undefined') })
      );
    });
    await page.waitForTimeout(1500);

    expect(await marqueur(page), 'une erreur ordinaire a déclenché un rechargement').toBeNull();
  });
});
