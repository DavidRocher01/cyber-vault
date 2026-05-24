# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: phishing.spec.ts >> Phishing — édition campagne >> edit — bouton Lancer désactivé (sans scénario ni cibles)
- Location: e2e\phishing.spec.ts:273:7

# Error details

```
TimeoutError: page.waitForURL: Timeout 25000ms exceeded.
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
            - textbox "vous@exemple.com" [ref=e52]: e2e_1779538158710_n29ga@test.com
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
  - generic [ref=e82]:
    - img [ref=e83]: cookie
    - generic [ref=e84]:
      - text: Cookies & confidentialité — Nous utilisons uniquement des cookies strictement nécessaires au fonctionnement du service (session, authentification). Aucun cookie publicitaire ou de tracking tiers.
      - link "Politique de confidentialité" [ref=e85] [cursor=pointer]:
        - /url: /cyberscan/politique-confidentialite
    - generic [ref=e86]:
      - button "Refuser" [ref=e87] [cursor=pointer]:
        - generic [ref=e88]: Refuser
      - button "Accepter" [ref=e91] [cursor=pointer]:
        - generic [ref=e92]: Accepter
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
> 15 |   await page.waitForURL(url => !url.pathname.includes('/auth/register'), { timeout: 25_000 });
     |              ^ TimeoutError: page.waitForURL: Timeout 25000ms exceeded.
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
  34 |   await page.waitForURL(url => !url.pathname.includes('/auth/login'), { timeout: 10_000 });
  35 | }
  36 | 
```