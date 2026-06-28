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
