import { Page } from '@playwright/test';

const PASSWORD = 'StrongPass123!';
const MASTER = 'MasterPass456!';

export async function createAndLogin(page: Page): Promise<string> {
  const email = `e2e_${Date.now()}_${Math.random().toString(36).slice(2, 7)}@test.com`;

  await page.goto('/auth/register');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Mot de passe').fill(PASSWORD);
  await page.getByRole('button', { name: /s'inscrire/i }).click();

  await page.goto('/auth/login');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Mot de passe').fill(PASSWORD);
  await page.getByRole('button', { name: /se connecter/i }).click();

  await page.waitForURL('**/auth/master-password');
  await page.getByLabel('Mot de passe maître').fill(MASTER);
  await page.getByRole('button', { name: /déverrouiller/i }).click();
  await page.waitForURL('**/cyberscan/**');

  return email;
}

export async function login(page: Page, email: string): Promise<void> {
  await page.goto('/auth/login');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Mot de passe').fill(PASSWORD);
  await page.getByRole('button', { name: /se connecter/i }).click();

  await page.waitForURL('**/auth/master-password');
  await page.getByLabel('Mot de passe maître').fill(MASTER);
  await page.getByRole('button', { name: /déverrouiller/i }).click();
  await page.waitForURL('**/cyberscan/**');
}
