import { Page } from '@playwright/test';

const PASSWORD = 'StrongPass123!';

export async function createAndLogin(page: Page): Promise<string> {
  const email = `e2e_${Date.now()}_${Math.random().toString(36).slice(2, 7)}@test.com`;

  await page.goto('/auth/register');
  await page.locator('[formcontrolname="email"]').fill(email);
  await page.locator('[formcontrolname="password"]').fill(PASSWORD);
  await page.locator('[formcontrolname="confirmPassword"]').fill(PASSWORD);
  await page.getByRole('button', { name: /créer mon compte/i }).click();
  await page.waitForURL(/\/cyberscan/, { waitUntil: 'commit' });

  return email;
}

export async function login(page: Page, email: string): Promise<void> {
  await page.goto('/auth/login');
  await page.locator('[formcontrolname="email"]').fill(email);
  await page.locator('[formcontrolname="password"]').fill(PASSWORD);
  await page.getByRole('button', { name: /se connecter/i }).click();
  await page.waitForURL(/\/cyberscan/, { waitUntil: 'commit' });
}
