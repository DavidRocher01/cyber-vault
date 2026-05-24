# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: phishing.spec.ts >> Phishing — détail campagne >> detail — lien retour "Mes campagnes" visible
- Location: e2e\phishing.spec.ts:201:7

# Error details

```
TimeoutError: page.waitForURL: Timeout 10000ms exceeded.
=========================== logs ===========================
waiting for navigation until "load"
============================================================
```

# Page snapshot

```yaml
- generic [ref=e2]:
  - generic [ref=e4]:
    - generic [ref=e5]:
      - link "CyberScan" [ref=e8] [cursor=pointer]:
        - /url: /cyberscan
        - img [ref=e9]: shield
        - generic [ref=e10]: CyberScan
      - generic [ref=e11]:
        - img [ref=e13]: shield
        - heading "Continuez à surveiller vos sites en temps réel" [level=2] [ref=e14]:
          - text: Continuez à surveiller
          - text: vos sites en temps réel
        - paragraph [ref=e15]: Détectez les vulnérabilités avant qu'elles ne vous coûtent cher.
        - generic [ref=e16]:
          - generic [ref=e17]:
            - img [ref=e19]: bar_chart
            - generic [ref=e20]: Tableau de bord centralisé pour tous vos sites
          - generic [ref=e21]:
            - img [ref=e23]: picture_as_pdf
            - generic [ref=e24]: Téléchargez vos rapports PDF à tout moment
          - generic [ref=e25]:
            - img [ref=e27]: history
            - generic [ref=e28]: Historique complet et export CSV de vos scans
        - generic [ref=e29]:
          - generic [ref=e30]:
            - paragraph [ref=e31]: 500+
            - paragraph [ref=e32]: sites scannés
          - generic [ref=e33]:
            - paragraph [ref=e34]: 12 000+
            - paragraph [ref=e35]: vulnérabilités détectées
          - generic [ref=e36]:
            - paragraph [ref=e37]: 99%
            - paragraph [ref=e38]: disponibilité
      - paragraph [ref=e39]: © 2025 CyberScan — Scans passifs et non intrusifs.
    - generic [ref=e41]:
      - heading "Connexion" [level=1] [ref=e42]
      - paragraph [ref=e43]: Content de vous revoir
      - generic [ref=e44]:
        - generic [ref=e45]:
          - generic [ref=e46]: Email
          - generic [ref=e47]:
            - textbox "vous@exemple.com" [ref=e48]: e2e_1779538048297_soney@test.com
            - img [ref=e49]: mail
        - generic [ref=e50]:
          - generic [ref=e51]: Mot de passe
          - generic [ref=e52]:
            - textbox "••••••••" [ref=e53]: StrongPass123!
            - button [ref=e54] [cursor=pointer]:
              - img [ref=e55]: visibility
        - link "Mot de passe oublié ?" [ref=e57] [cursor=pointer]:
          - /url: /auth/forgot-password
        - generic [ref=e58]:
          - generic [ref=e59]:
            - img [ref=e60]: error_outline
            - text: Erreur de connexion
          - button [ref=e61] [cursor=pointer]:
            - img [ref=e62]: close
        - button "Se connecter" [ref=e63] [cursor=pointer]:
          - text: Se connecter
          - img [ref=e64]: arrow_forward
      - generic [ref=e67]: ou
      - paragraph [ref=e69]:
        - text: Pas de compte ?
        - link "S'inscrire gratuitement" [ref=e70] [cursor=pointer]:
          - /url: /auth/register
  - generic [ref=e72]:
    - img [ref=e73]: cookie
    - generic [ref=e74]:
      - text: Cookies & confidentialité — Nous utilisons uniquement des cookies strictement nécessaires au fonctionnement du service (session, authentification). Aucun cookie publicitaire ou de tracking tiers.
      - link "Politique de confidentialité" [ref=e75] [cursor=pointer]:
        - /url: /cyberscan/politique-confidentialite
    - generic [ref=e76]:
      - button "Refuser" [ref=e77] [cursor=pointer]:
        - generic [ref=e78]: Refuser
      - button "Accepter" [ref=e81] [cursor=pointer]:
        - generic [ref=e82]: Accepter
```

# Test source

```ts
  1  | import { type Page } from '@playwright/test';
  2  | 
  3  | export const BASE_PASSWORD = 'StrongPass123!';
  4  | 
  5  | /** Register + login a fresh user, return their email. */
  6  | export async function createAndLogin(page: Page, email?: string): Promise<string> {
  7  |   const userEmail = email ?? `e2e_${Date.now()}_${Math.random().toString(36).slice(2, 7)}@test.com`;
  8  | 
  9  |   await page.goto('/auth/register');
  10 |   await page.locator('input[type="email"]').fill(userEmail);
  11 |   // Register has 2 password fields (password + confirmPassword)
  12 |   await page.locator('input[autocomplete="new-password"]').first().fill(BASE_PASSWORD);
  13 |   await page.locator('input[autocomplete="new-password"]').last().fill(BASE_PASSWORD);
  14 |   await page.getByRole('button', { name: /créer|s'inscrire/i }).click();
  15 |   await page.waitForURL(url => !url.pathname.includes('/auth/register'), { timeout: 25_000 });
  16 | 
  17 |   await page.goto('/auth/login');
  18 |   await page.locator('input[type="email"]').fill(userEmail);
  19 |   await page.locator('input[autocomplete="current-password"]').fill(BASE_PASSWORD);
  20 |   await page.getByRole('button', { name: /se connecter/i }).click();
  21 | 
  22 |   // Wait until redirected away from login
  23 |   await page.waitForURL(url => !url.pathname.includes('/auth/login'), { timeout: 10_000 });
  24 | 
  25 |   return userEmail;
  26 | }
  27 | 
  28 | /** Login only (user must already exist). */
  29 | export async function login(page: Page, email: string): Promise<void> {
  30 |   await page.goto('/auth/login');
  31 |   await page.locator('input[type="email"]').fill(email);
  32 |   await page.locator('input[autocomplete="current-password"]').fill(BASE_PASSWORD);
  33 |   await page.getByRole('button', { name: /se connecter/i }).click();
> 34 |   await page.waitForURL(url => !url.pathname.includes('/auth/login'), { timeout: 10_000 });
     |              ^ TimeoutError: page.waitForURL: Timeout 10000ms exceeded.
  35 | }
  36 | 
```