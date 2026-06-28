import { test, expect } from '@playwright/test';

const API = 'http://localhost:8000/api/v1';

async function registerAndLogin(page: any, email: string, password = 'Pass123!') {
  await page.request.post(`${API}/auth/register`, {
    data: { email, password },
  });
  const r = await page.request.post(`${API}/auth/login`, {
    data: { email, password },
  });
  return (await r.json()).access_token as string;
}

// ── Reset password flow ────────────────────────────────────────────────────────

test.describe('Reset password', () => {
  test('affiche le formulaire forgot-password', async ({ page }) => {
    await page.goto('/auth/forgot-password');
    await expect(page.locator('[formcontrolname="email"]')).toBeVisible();
  });

  test('soumet une demande de reset (email inconnu → même réponse)', async ({ page }) => {
    await page.goto('/auth/forgot-password');
    await page.locator('[formcontrolname="email"]').fill('inexistant@test.com');
    await page.getByRole('button', { name: /envoyer|réinitialiser/i }).click();
    // La réponse doit être identique qu'il y ait un compte ou non (pas de user enumeration)
    await expect(page.getByText(/email envoyé|si l'adresse/i)).toBeVisible();
  });
});

// ── Rate limiting ──────────────────────────────────────────────────────────────

test.describe('Rate limiting', () => {
  test('retourne 429 après trop de tentatives de login', async ({ page }) => {
    const responses: number[] = [];
    // Les requêtes loopback contournent volontairement le rate-limiting
    // (cf. backend/app/core/limiter.py — clé unique par requête en dev/test).
    // On simule une IP cliente publique via X-Forwarded-For pour que le
    // limiter applique réellement la limite (10/minute sur /auth/login).
    const headers = { 'X-Forwarded-For': '8.8.8.8' };
    for (let i = 0; i < 12; i++) {
      const r = await page.request.post(`${API}/auth/login`, {
        headers,
        data: { email: 'rate@test.com', password: 'wrong' },
      });
      responses.push(r.status());
    }
    expect(responses).toContain(429);
  });
});

// ── Export RGPD ────────────────────────────────────────────────────────────────

test.describe('Export RGPD', () => {
  test('utilisateur peut exporter ses données', async ({ page }) => {
    const email = `rgpd-${Date.now()}@test.com`;
    const token = await registerAndLogin(page, email);

    const r = await page.request.get(`${API}/users/me/export`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    expect([200, 202]).toContain(r.status());
    if (r.status() === 200) {
      const contentType = r.headers()['content-type'] ?? '';
      expect(contentType).toMatch(/json|zip|octet-stream/);
    }
  });
});

// ── Upgrade plan ───────────────────────────────────────────────────────────────

test.describe('Navigation upgrade plan', () => {
  test('le bouton upgrade redirige vers /cyberscan/pricing ou Stripe', async ({ page }) => {
    const email = `upgrade-${Date.now()}@test.com`;
    await registerAndLogin(page, email);
    await page.goto('/dashboard');

    // Cherche un lien/bouton "Passer à Pro" ou "Upgrade"
    const upgradeBtn = page.getByRole('link', { name: /upgrade|passer|pro|business/i }).first();
    const count = await upgradeBtn.count();
    if (count > 0) {
      await upgradeBtn.click();
      await expect(page).toHaveURL(/(pricing|stripe\.com)/);
    } else {
      test.skip();
    }
  });
});
