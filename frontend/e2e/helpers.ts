import { type Page } from '@playwright/test';

export const BASE_PASSWORD = 'StrongPass123!';

/** Register + login a fresh user, return their email. */
export async function createAndLogin(page: Page, email?: string): Promise<string> {
  const userEmail = email ?? `e2e_${Date.now()}_${Math.random().toString(36).slice(2, 7)}@test.com`;

  await page.goto('/auth/register');
  await page.locator('input[type="email"]').fill(userEmail);
  // Register has 2 password fields (password + confirmPassword)
  await page.locator('input[autocomplete="new-password"]').first().fill(BASE_PASSWORD);
  await page.locator('input[autocomplete="new-password"]').last().fill(BASE_PASSWORD);
  await page.getByRole('button', { name: /créer|s'inscrire/i }).click();
  await page.waitForURL(url => !url.pathname.includes('/auth/register'), { timeout: 25_000 });

  await page.goto('/auth/login');
  await page.locator('input[type="email"]').fill(userEmail);
  await page.locator('input[autocomplete="current-password"]').fill(BASE_PASSWORD);
  await page.getByRole('button', { name: /se connecter/i }).click();

  // Wait until redirected away from login
  await page.waitForURL(url => !url.pathname.includes('/auth/login'), { timeout: 10_000 });

  return userEmail;
}

/** Login only (user must already exist). */
export async function login(page: Page, email: string): Promise<void> {
  await page.goto('/auth/login');
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[autocomplete="current-password"]').fill(BASE_PASSWORD);
  await page.getByRole('button', { name: /se connecter/i }).click();
  await page.waitForURL(url => !url.pathname.includes('/auth/login'), { timeout: 10_000 });
}
