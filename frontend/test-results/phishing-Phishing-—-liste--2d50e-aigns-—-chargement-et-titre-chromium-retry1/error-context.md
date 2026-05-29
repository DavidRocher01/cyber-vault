# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: phishing.spec.ts >> Phishing — liste des campagnes >> page campaigns — chargement et titre
- Location: e2e\phishing.spec.ts:101:7

# Error details

```
Error: page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:4200/auth/register
Call log:
  - navigating to "http://localhost:4200/auth/register", waiting until "load"

```

# Test source

```ts
  1  | import { Page } from '@playwright/test';
  2  |
  3  | const PASSWORD = 'StrongPass123!';
  4  |
  5  | // Transient proxy "socket hang up" errors can occur under test load.
  6  | // Retry up to 3 times with a short back-off before letting the test fail.
  7  | async function withRetry<T>(fn: () => Promise<T>, retries = 2, delayMs = 800): Promise<T> {
  8  |   let lastErr: unknown;
  9  |   for (let i = 0; i <= retries; i++) {
  10 |     try {
  11 |       return await fn();
  12 |     } catch (e) {
  13 |       lastErr = e;
  14 |       if (i < retries) await new Promise(r => setTimeout(r, delayMs));
  15 |     }
  16 |   }
  17 |   throw lastErr;
  18 | }
  19 |
  20 | export async function createAndLogin(page: Page): Promise<string> {
  21 |   await page.addInitScript(() => localStorage.setItem('cyberscan_cookie_consent', 'accepted'));
  22 |
  23 |   return withRetry(async () => {
  24 |     const email = `e2e_${Date.now()}_${Math.random().toString(36).slice(2, 7)}@test.com`;
> 25 |     await page.goto('/auth/register');
     |                ^ Error: page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:4200/auth/register
  26 |     await page.locator('[formcontrolname="email"]').fill(email);
  27 |     await page.locator('[formcontrolname="password"]').fill(PASSWORD);
  28 |     await page.locator('[formcontrolname="confirmPassword"]').fill(PASSWORD);
  29 |     await page.getByRole('button', { name: /créer mon compte/i }).click();
  30 |     await page.waitForURL(/\/cyberscan/, { waitUntil: 'commit', timeout: 15_000 });
  31 |     return email;
  32 |   });
  33 | }
  34 |
  35 | export async function login(page: Page, email: string): Promise<void> {
  36 |   await page.addInitScript(() => localStorage.setItem('cyberscan_cookie_consent', 'accepted'));
  37 |
  38 |   await withRetry(async () => {
  39 |     await page.goto('/auth/login');
  40 |     await page.locator('[formcontrolname="email"]').fill(email);
  41 |     await page.locator('[formcontrolname="password"]').fill(PASSWORD);
  42 |     await page.getByRole('button', { name: /se connecter/i }).click();
  43 |     await page.waitForURL(/\/cyberscan/, { waitUntil: 'commit', timeout: 15_000 });
  44 |   });
  45 | }
  46 |
```
