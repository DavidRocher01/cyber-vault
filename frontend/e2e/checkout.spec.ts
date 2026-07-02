import { test, expect } from '@playwright/test';
import { createAndLogin } from './helpers';

/**
 * E2E — Initiation du parcours d'abonnement (checkout).
 *
 * On ne peut pas compléter un vrai paiement Stripe en E2E, donc on teste
 * jusqu'à la CRÉATION de la session de checkout : un utilisateur connecté va sur
 * la page d'onboarding, sélectionne un plan payant, et l'app doit émettre une
 * requête POST /api/v1/subscriptions/checkout/{planId} puis suivre l'URL renvoyée.
 *
 * Robustesse CI : Stripe peut ne pas être configuré côté backend. On INTERCEPTE
 * donc toutes les requêtes réseau concernées (page.route + waitForRequest) et on
 * fournit nous-mêmes des réponses déterministes. Le test n'atteint jamais un vrai
 * backend ni checkout.stripe.com — il vérifie que l'app DÉCLENCHE le checkout
 * avec le bon plan, ce qui est l'invariant réel du parcours d'abonnement.
 */

// Deux plans payants factices — le composant onboarding attend cette forme (interface Plan).
const PLANS = [
  {
    id: 1,
    name: 'essentiel',
    display_name: 'Essentiel',
    price_eur: 1900,
    max_sites: 1,
    scan_interval_days: 30,
    tier_level: 1,
    stripe_price_id: 'price_essentiel',
  },
  {
    id: 42,
    name: 'pro',
    display_name: 'Pro',
    price_eur: 4900,
    max_sites: 5,
    scan_interval_days: 7,
    tier_level: 3,
    stripe_price_id: 'price_pro',
  },
];

/**
 * Installe les stubs réseau communs à tous les tests :
 *  - GET /api/v1/plans           -> liste de plans factices (indépendant de la DB)
 *  - GET /api/v1/subscriptions/me -> null (pas d'abonnement => on reste à l'étape 1)
 * Le stub du checkout est propre à chaque test (URL de retour variable).
 */
async function stubPlansAndSubscription(page: import('@playwright/test').Page) {
  await page.route('**/api/v1/plans', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(PLANS),
    })
  );
  await page.route('**/api/v1/subscriptions/me', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: 'null',
    })
  );
}

test.describe('Parcours abonnement — initiation du checkout', () => {
  test.describe.configure({ mode: 'serial' });

  test('émet le checkout avec le bon plan et suit une URL de retour interne', async ({ page }) => {
    await stubPlansAndSubscription(page);

    // Le checkout renvoie une URL RELATIVE : le composant fait router.navigateByUrl(url).
    // On évite ainsi toute vraie redirection externe (Stripe) tout en exerçant le flux complet.
    let checkoutBody: unknown = null;
    await page.route('**/api/v1/subscriptions/checkout/*', async route => {
      checkoutBody = route.request().postDataJSON?.() ?? route.request().postData();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ checkout_url: '/dashboard?checkout=success' }),
      });
    });

    await createAndLogin(page);
    await page.goto('/onboarding');

    // Étape 1 : la liste des plans (stubés) doit s'afficher.
    await expect(page.getByRole('heading', { name: /choisissez votre plan/i })).toBeVisible();
    const proPlanBtn = page.getByRole('button').filter({ hasText: 'Pro' });
    await expect(proPlanBtn).toBeVisible();

    // On arme l'écoute de la requête AVANT le clic pour ne pas la rater.
    const checkoutReq = page.waitForRequest(
      req =>
        req.method() === 'POST' && /\/api\/v1\/subscriptions\/checkout\/\d+$/.test(req.url())
    );

    await proPlanBtn.click();

    const req = await checkoutReq;
    // INVARIANT CLÉ : le checkout est déclenché pour le plan payant sélectionné (id=42, "Pro").
    expect(req.url()).toMatch(/\/api\/v1\/subscriptions\/checkout\/42$/);
    expect(req.method()).toBe('POST');
    // Le corps est un POST vide {} côté service — on vérifie juste qu'il n'y a pas d'erreur de sérialisation.
    expect(checkoutBody === null || typeof checkoutBody === 'object' || checkoutBody === '{}').toBeTruthy();

    // L'app suit l'URL de retour interne => navigation vers /dashboard.
    await page.waitForURL(/\/dashboard/, { timeout: 15_000 });
  });

  test('déclenche une redirection externe quand le checkout renvoie une URL Stripe', async ({
    page,
  }) => {
    await stubPlansAndSubscription(page);

    // Le checkout renvoie une URL checkout.stripe.com : le composant fait
    // window.location.href = url. On INTERCEPTE la navigation vers Stripe pour
    // NE PAS quitter vers le vrai site (déterminisme + pas d'accès réseau externe),
    // tout en prouvant que l'app a bien tenté la redirection de paiement.
    await page.route('**/api/v1/subscriptions/checkout/*', route =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          checkout_url: 'https://checkout.stripe.com/c/pay/cs_test_e2e_abc123',
        }),
      })
    );

    let stripeNavAttempted = false;
    // Sert une page vide à la place du vrai domaine Stripe si le navigateur tente d'y aller.
    await page.route('https://checkout.stripe.com/**', route => {
      stripeNavAttempted = true;
      return route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: '<html><body>stripe-stub</body></html>',
      });
    });

    await createAndLogin(page);
    await page.goto('/onboarding');

    await expect(page.getByRole('heading', { name: /choisissez votre plan/i })).toBeVisible();

    const checkoutReq = page.waitForRequest(
      req => req.method() === 'POST' && /\/subscriptions\/checkout\/\d+$/.test(req.url())
    );

    await page.getByRole('button').filter({ hasText: 'Essentiel' }).click();

    const req = await checkoutReq;
    // Le premier plan payant (id=1) est bien celui pour lequel le checkout est créé.
    expect(req.url()).toMatch(/\/api\/v1\/subscriptions\/checkout\/1$/);

    // L'app doit tenter d'atteindre checkout.stripe.com (redirection de paiement).
    await page.waitForURL(/checkout\.stripe\.com/, { timeout: 15_000 });
    expect(stripeNavAttempted).toBe(true);
  });

  test('ne redirige pas et reste utilisable si le checkout échoue (backend Stripe absent)', async ({
    page,
  }) => {
    await stubPlansAndSubscription(page);

    // Cas CI réaliste : Stripe non configuré => l'endpoint renvoie une erreur 500.
    // Le composant fait error: () => checkoutLoading.set(false) : pas de crash, pas de redirection.
    await page.route('**/api/v1/subscriptions/checkout/*', route =>
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Stripe not configured' }),
      })
    );

    await createAndLogin(page);
    await page.goto('/onboarding');

    await expect(page.getByRole('heading', { name: /choisissez votre plan/i })).toBeVisible();

    const checkoutReq = page.waitForRequest(
      req => req.method() === 'POST' && /\/subscriptions\/checkout\/\d+$/.test(req.url())
    );

    await page.getByRole('button').filter({ hasText: 'Pro' }).click();
    await checkoutReq; // la requête part bien, même si elle échoue ensuite

    // Invariant d'erreur : on reste sur l'onboarding (aucune navigation vers dashboard/Stripe).
    await expect(page.getByRole('heading', { name: /choisissez votre plan/i })).toBeVisible();
    expect(new URL(page.url()).pathname).toContain('/onboarding');
  });
});
