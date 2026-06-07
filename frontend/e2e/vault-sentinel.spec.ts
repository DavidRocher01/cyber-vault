/**
 * D3 — Test sentinel zero-knowledge vault.
 * Vérifie qu'aucune donnée sensible du vault ne traverse l'API en clair.
 * Les requêtes vers /api/v1/vault doivent contenir uniquement des blobs chiffrés (base64 opaque).
 */
import { test, expect } from '@playwright/test';

const API = 'http://localhost:8000/api/v1';

const SENTINEL_TITLE = 'CANARY_TITLE_DO_NOT_LEAK_2026';
const SENTINEL_USERNAME = 'CANARY_USER_DO_NOT_LEAK';
const SENTINEL_URL = 'https://canary.do-not-leak.internal';
const SENTINEL_NOTES = 'CANARY_NOTE_DO_NOT_LEAK_2026';
const SENTINEL_PASSWORD = 'CANARY_PWD_DO_NOT_LEAK_2026';

async function registerAndGetToken(page: any, email: string): Promise<string> {
  await page.request.post(`${API}/auth/register`, {
    data: { email, password: 'Pass123!' },
  });
  const r = await page.request.post(`${API}/auth/login`, {
    data: { email, password: 'Pass123!' },
  });
  const body = await r.json();
  return body.access_token;
}

test('aucun champ vault en clair ne traverse l\'API', async ({ page }) => {
  const email = `sentinel-${Date.now()}@test.com`;
  const requestBodies: string[] = [];

  // Intercept all requests to /vault
  page.on('request', req => {
    if (req.url().includes('/api/v1/vault') && req.method() !== 'GET') {
      requestBodies.push(req.postData() ?? '');
    }
  });

  // Register + login via API to obtain a session token + crypto salt
  await page.request.post(`${API}/auth/register`, {
    data: { email, password: 'Pass123!' },
  });
  const loginRes = await page.request.post(`${API}/auth/login`, {
    data: { email, password: 'Pass123!' },
  });
  const { access_token, crypto_salt } = await loginRes.json();

  // Propage la session dans le navigateur pour que authGuard laisse passer /vault.
  // AuthService lit cv_token (sessionStorage), cv_email (localStorage),
  // cv_crypto_salt (sessionStorage). Sans ça, /vault redirige vers le login.
  await page.addInitScript(
    ({ token, salt, userEmail }) => {
      sessionStorage.setItem('cv_token', token);
      if (salt) sessionStorage.setItem('cv_crypto_salt', salt);
      localStorage.setItem('cv_email', userEmail);
      // Évite que la bannière cookies (fixed bottom, z-50) ne recouvre le
      // bouton submit du formulaire et n'intercepte le clic (cf. helpers.ts).
      localStorage.setItem('cyberscan_cookie_consent', 'accepted');
    },
    { token: access_token, salt: crypto_salt, userEmail: email },
  );

  // /vault est verrouillé (aucune clé en mémoire) → cryptoGuard redirige vers l'unlock
  await page.goto('/vault');
  await page.locator('[formcontrolname="masterPassword"]').fill('MySecureMaster#99');
  await page.getByRole('button', { name: /déverrouiller|unlock/i }).click();
  await page.waitForURL('**/vault');

  // Create a vault item with sentinel values via UI
  await page.getByRole('button', { name: /nouvelle entrée|nouveau|ajouter/i }).first().click();
  const form = page.locator('form');
  await form.locator('[formcontrolname="title"]').fill(SENTINEL_TITLE);
  await form.locator('[formcontrolname="username"]').fill(SENTINEL_USERNAME);
  await form.locator('[formcontrolname="password_encrypted"]').fill(SENTINEL_PASSWORD);

  const urlInput = form.locator('[formcontrolname="url"]');
  if (await urlInput.count() > 0) await urlInput.fill(SENTINEL_URL);

  const notesInput = form.locator('[formcontrolname="notes"]');
  if (await notesInput.count() > 0) await notesInput.fill(SENTINEL_NOTES);

  // Le bouton submit affiche "Ajouter" (création) ou "Enregistrer les modifications" (édition)
  await form.getByRole('button', { name: /ajouter|enregistrer|sauvegarder|save/i }).click();
  await page.waitForTimeout(500);

  // Assert no sentinel value appears in any vault API request body
  for (const body of requestBodies) {
    expect(body, 'title sent in plaintext').not.toContain(SENTINEL_TITLE);
    expect(body, 'username sent in plaintext').not.toContain(SENTINEL_USERNAME);
    expect(body, 'url sent in plaintext').not.toContain(SENTINEL_URL);
    expect(body, 'notes sent in plaintext').not.toContain(SENTINEL_NOTES);
    expect(body, 'password sent in plaintext').not.toContain(SENTINEL_PASSWORD);
  }

  // Make sure at least one vault request was intercepted
  expect(requestBodies.length, 'No vault POST/PATCH intercepted — test may not have worked').toBeGreaterThan(0);
});

test('les champs chiffrés retournés sont des blobs base64 opaques', async ({ page }) => {
  const email = `sentinel2-${Date.now()}@test.com`;
  const token = await registerAndGetToken(page, email);

  // Create an item directly via API with encrypted fields
  const encryptedTitle = 'ZXhhbXBsZUVuY3J5cHRlZEJhc2U2NFNPX09QQVFVRQ=='; // fake base64 blob

  const r = await page.request.post(`${API}/vault/`, {
    headers: { Authorization: `Bearer ${token}` },
    // Zero-knowledge strict : aucun champ en clair accepté, uniquement *_encrypted
    data: {
      password_encrypted: 'enc_pwd',
      title_encrypted: encryptedTitle,
    },
  });
  expect(r.status()).toBe(201);
  const item = await r.json();

  // The server must return the encrypted blob unchanged
  expect(item.title_encrypted).toBe(encryptedTitle);
  // The server must NOT decrypt or modify the blob
  expect(item.title_encrypted).not.toBe(SENTINEL_TITLE);
});
