# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: phishing.spec.ts >> Phishing — liste des campagnes >> page campaigns — chargement et titre
- Location: e2e\phishing.spec.ts:101:7

# Error details

```
TimeoutError: page.waitForURL: Timeout 15000ms exceeded.
=========================== logs ===========================
waiting for navigation until "commit"
============================================================
```

# Page snapshot

```yaml
- generic [ref=e4]:
  - generic [ref=e5]:
    - link "CyberScan" [ref=e8] [cursor=pointer]:
      - /url: /cyberscan
      - img [ref=e9]: shield
      - generic [ref=e10]: CyberScan
    - generic [ref=e11]:
      - img [ref=e13]: security
      - heading "Votre premier scan en moins de 2 minutes" [level=2] [ref=e14]:
        - text: Votre premier scan en
        - text: moins de 2 minutes
      - paragraph [ref=e15]: Créez votre compte gratuitement et découvrez les vulnérabilités de votre site.
      - generic [ref=e16]:
        - generic [ref=e17]:
          - img [ref=e19]: security
          - generic [ref=e20]: Scan SSL, headers HTTP, CVE — non intrusif
        - generic [ref=e21]:
          - img [ref=e23]: picture_as_pdf
          - generic [ref=e24]: Rapport PDF complet après chaque scan
        - generic [ref=e25]:
          - img [ref=e27]: notifications_active
          - generic [ref=e28]: Alerte email si vulnérabilité critique détectée
        - generic [ref=e29]:
          - img [ref=e31]: lock
          - generic [ref=e32]: Vos données ne quittent jamais nos serveurs
      - generic [ref=e33]:
        - generic [ref=e34]:
          - paragraph [ref=e35]: Gratuit
          - paragraph [ref=e36]: sans CB requise
        - generic [ref=e37]:
          - paragraph [ref=e38]: 2 min
          - paragraph [ref=e39]: pour le premier scan
        - generic [ref=e40]:
          - paragraph [ref=e41]: 19 modules
          - paragraph [ref=e42]: d'analyse
    - paragraph [ref=e43]: © 2025 CyberScan — Scans passifs et non intrusifs.
  - generic [ref=e45]:
    - heading "Créer un compte" [level=1] [ref=e46]
    - paragraph [ref=e47]: Pas de carte bancaire requise
    - generic [ref=e48]:
      - generic [ref=e49]:
        - generic [ref=e50]: Email
        - generic [ref=e51]:
          - textbox "vous@exemple.com" [ref=e52]: e2e_1779946820061_ofo5f@test.com
          - img [ref=e53]: mail
      - generic [ref=e54]:
        - generic [ref=e55]: Mot de passe
        - generic [ref=e56]:
          - textbox "••••••••" [ref=e57]: StrongPass123!
          - button [ref=e58] [cursor=pointer]:
            - img [ref=e59]: visibility
        - paragraph [ref=e65]: Très fort
      - generic [ref=e66]:
        - generic [ref=e67]: Confirmer le mot de passe
        - generic [ref=e68]:
          - textbox "••••••••" [ref=e69]: StrongPass123!
          - img [ref=e70]: lock
      - generic [ref=e71]:
        - img [ref=e72]: error_outline
        - text: Erreur inscription
      - button "Créer mon compte" [ref=e73] [cursor=pointer]:
        - text: Créer mon compte
        - img [ref=e74]: arrow_forward
    - generic [ref=e77]: ou
    - paragraph [ref=e79]:
      - text: Déjà un compte ?
      - link "Se connecter" [ref=e80] [cursor=pointer]:
        - /url: /auth/login
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
  25 |     await page.goto('/auth/register');
  26 |     await page.locator('[formcontrolname="email"]').fill(email);
  27 |     await page.locator('[formcontrolname="password"]').fill(PASSWORD);
  28 |     await page.locator('[formcontrolname="confirmPassword"]').fill(PASSWORD);
  29 |     await page.getByRole('button', { name: /créer mon compte/i }).click();
> 30 |     await page.waitForURL(/\/cyberscan/, { waitUntil: 'commit', timeout: 15_000 });
     |                ^ TimeoutError: page.waitForURL: Timeout 15000ms exceeded.
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
