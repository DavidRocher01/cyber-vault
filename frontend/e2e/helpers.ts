import { Page } from '@playwright/test';

export const PASSWORD = 'StrongPass123!';

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

/** Lit le token d'acces de l'utilisateur connecte (sessionStorage). */
async function authHeader(page: Page): Promise<{ Authorization: string }> {
  const token = await page.evaluate(() => sessionStorage.getItem('cv_token'));
  if (!token) throw new Error('Token cv_token introuvable — utilisateur non connecte');
  return { Authorization: `Bearer ${token}` };
}

/**
 * Active le role consultant RSSI sur le compte connecte, via l'endpoint DEV_MODE
 * `/dev/become-consultant` (sans clef admin — indisponible en E2E). Miroir de
 * upgradeToPlan : affordance de test active seulement en APP_ENV=development.
 */
export async function becomeConsultant(page: Page): Promise<void> {
  const res = await page.request.post('/api/v1/dev/become-consultant', {
    headers: await authHeader(page),
  });
  if (!res.ok()) throw new Error(`become-consultant a echoue: ${res.status()}`);
}

/**
 * Cree un client RSSI (API) rattache au consultant connecte, puis l'invite au portail.
 * Retourne l'id du client et le CHEMIN d'activation (token brut expose par l'invite en
 * DEV_MODE, sinon irrecuperable car hache en base).
 */
export async function createClientAndInvite(
  page: Page,
  clientEmail: string,
  clientName = 'Client E2E'
): Promise<{ clientId: number; activationPath: string }> {
  const headers = await authHeader(page);

  const created = await page.request.post('/api/v1/rssi/clients', {
    headers,
    data: { name: clientName, email: clientEmail, formula: 'essentiel' },
  });
  if (!created.ok()) throw new Error(`Creation client a echoue: ${created.status()}`);
  const clientId = (await created.json()).id as number;

  const invited = await page.request.post(`/api/v1/rssi/clients/${clientId}/invite`, { headers });
  if (!invited.ok()) throw new Error(`Invitation a echoue: ${invited.status()}`);
  const inviteUrl = (await invited.json()).invite_url as string | undefined;
  if (!inviteUrl) throw new Error('invite_url absent — DEV_MODE requis cote backend');

  // URL absolue (FRONTEND_URL) -> chemin relatif utilisable avec baseURL Playwright.
  const activationPath = inviteUrl.replace(/^https?:\/\/[^/]+/, '');
  return { clientId, activationPath };
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
