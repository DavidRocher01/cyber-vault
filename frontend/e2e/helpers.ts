import { Page } from '@playwright/test';

const PASSWORD = 'StrongPass123!';

// Transient proxy "socket hang up" errors can occur under test load.
// Retry up to 3 times with a short back-off before letting the test fail.
async function withRetry<T>(fn: () => Promise<T>, retries = 2, delayMs = 800): Promise<T> {
  let lastErr: unknown;
  for (let i = 0; i <= retries; i++) {
    try {
      return await fn();
    } catch (e) {
      lastErr = e;
      if (i < retries) await new Promise(r => setTimeout(r, delayMs));
    }
  }
  throw lastErr;
}

export async function createAndLogin(page: Page): Promise<string> {
  await page.addInitScript(() => localStorage.setItem('cyberscan_cookie_consent', 'accepted'));

  return withRetry(async () => {
    const email = `e2e_${Date.now()}_${Math.random().toString(36).slice(2, 7)}@test.com`;
    await page.goto('/auth/register');
    await page.locator('[formcontrolname="email"]').fill(email);
    await page.locator('[formcontrolname="password"]').fill(PASSWORD);
    await page.locator('[formcontrolname="confirmPassword"]').fill(PASSWORD);
    await page.getByRole('button', { name: /créer mon compte/i }).click();
    await page.waitForURL((url) => !url.pathname.startsWith('/auth'), { waitUntil: 'commit', timeout: 15_000 });
    return email;
  });
}

export async function login(page: Page, email: string): Promise<void> {
  await page.addInitScript(() => localStorage.setItem('cyberscan_cookie_consent', 'accepted'));

  await withRetry(async () => {
    await page.goto('/auth/login');
    await page.locator('[formcontrolname="email"]').fill(email);
    await page.locator('[formcontrolname="password"]').fill(PASSWORD);
    await page.getByRole('button', { name: /se connecter/i }).click();
    await page.waitForURL((url) => !url.pathname.startsWith('/auth'), { waitUntil: 'commit', timeout: 15_000 });
  });
}

/**
 * Octroie a l'utilisateur connecte un abonnement ACTIF du plan donne, via le checkout
 * DEV_MODE (sans Stripe — actif quand APP_ENV=development, cas de la CI E2E).
 * Necessaire pour tester les features gatees par tier (dark web = Pro, etc.).
 * La page doit etre authentifiee (token cv_token present en sessionStorage).
 */
export async function upgradeToPlan(
  page: Page,
  planName: 'starter' | 'pro' | 'business'
): Promise<void> {
  const token = await page.evaluate(() => sessionStorage.getItem('cv_token'));
  if (!token) throw new Error('Token cv_token introuvable — utilisateur non connecte');

  const plansRes = await page.request.get('/api/v1/plans');
  if (!plansRes.ok()) throw new Error(`GET /api/v1/plans a echoue: ${plansRes.status()}`);
  const plans: Array<{ id: number; name: string }> = await plansRes.json();
  const plan = plans.find((p) => p.name === planName);
  if (!plan) throw new Error(`Plan "${planName}" introuvable dans /api/v1/plans`);

  const res = await page.request.post(`/api/v1/subscriptions/checkout/${plan.id}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok()) throw new Error(`Checkout ${planName} a echoue: ${res.status()}`);
}
