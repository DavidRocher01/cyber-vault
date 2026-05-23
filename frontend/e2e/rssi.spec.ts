import { test, expect } from '@playwright/test';
import { createAndLogin } from './helpers';

/**
 * E2E tests pour le module RSSI Externalisé.
 * Note: le rôle `is_rssi_consultant` est requis pour certaines actions.
 * Ces tests vérifient la navigation et les pages accessibles à tout utilisateur authentifié.
 */

test.describe('RSSI — page consultant', () => {
  test('page consultant — accessible et titre visible', async ({ page }) => {
    await createAndLogin(page);
    await page.goto('/cyberscan/consultant');
    await expect(page).toHaveURL(/\/cyberscan\/consultant/);
    await expect(page.getByRole('heading').first()).toBeVisible();
  });

  test('consultant — redirige vers login si non authentifié', async ({ page }) => {
    await page.goto('/cyberscan/consultant');
    await expect(page).toHaveURL(/\/auth\/login/);
  });
});

test.describe('RSSI — gestion clients', () => {
  test('page client detail — 404 ou redirection pour client inexistant', async ({ page }) => {
    await createAndLogin(page);
    await page.goto('/cyberscan/consultant/clients/99999');
    // Wait for either a redirect or an error message (API call is async)
    await Promise.race([
      page.waitForURL(url => !url.pathname.includes('/clients/99999'), { timeout: 8_000 }),
      page.getByText(/introuvable|not found|404|erreur/i).waitFor({ timeout: 8_000 }),
    ]).catch(() => {});
    const isError = await page.getByText(/introuvable|not found|404|erreur/i).isVisible().catch(() => false);
    const isRedirected = !page.url().includes('/clients/99999');
    expect(isError || isRedirected).toBeTruthy();
  });
});
