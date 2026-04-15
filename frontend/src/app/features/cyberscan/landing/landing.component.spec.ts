/**
 * LandingComponent — tests des méthodes utilitaires pures + non-régression.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { LandingComponent } from './landing.component';

function make(): LandingComponent {
  return Object.create(LandingComponent.prototype) as LandingComponent;
}

describe('LandingComponent — formatPrice()', () => {
  it('convertit les centimes en euros', () => {
    const result = make().formatPrice(900);
    expect(result).toContain('9');
    expect(result).toContain('€');
  });

  it('formate 2900 centimes', () => {
    const result = make().formatPrice(2900);
    expect(result).toContain('29');
  });

  it('formate 7900 centimes', () => {
    const result = make().formatPrice(7900);
    expect(result).toContain('79');
  });
});

describe('LandingComponent — getPlanFeatures()', () => {
  it('inclut max_sites dans les features', () => {
    const plan: any = { max_sites: 3, scan_interval_days: 7, tier_level: 2 };
    const features = make().getPlanFeatures(plan);
    expect(features.some(f => f.includes('3'))).toBe(true);
  });

  it('inclut scan_interval_days dans les features', () => {
    const plan: any = { max_sites: 1, scan_interval_days: 30, tier_level: 2 };
    const features = make().getPlanFeatures(plan);
    expect(features.some(f => f.includes('30'))).toBe(true);
  });

  it('ajoute les modules Tier 3 si tier_level >= 3', () => {
    const plan: any = { max_sites: 5, scan_interval_days: 7, tier_level: 3 };
    const features = make().getPlanFeatures(plan);
    expect(features.some(f => f.includes('Tier 3'))).toBe(true);
  });

  it('n\'ajoute pas les modules Tier 3 si tier_level < 3', () => {
    const plan: any = { max_sites: 1, scan_interval_days: 30, tier_level: 2 };
    const features = make().getPlanFeatures(plan);
    expect(features.some(f => f.includes('Tier 3'))).toBe(false);
  });

  it('ajoute les modules Tier 4 si tier_level >= 4', () => {
    const plan: any = { max_sites: 10, scan_interval_days: 7, tier_level: 4 };
    const features = make().getPlanFeatures(plan);
    expect(features.some(f => f.includes('Tier 4'))).toBe(true);
  });
});

// ── Non-régression : données statiques critiques ──────────────────────────────
// Ces tests lisent le source TypeScript pour détecter toute modification
// accidentelle des valeurs affichées aux utilisateurs.

describe('LandingComponent — non-régression données statiques', () => {
  const src = readFileSync(
    resolve(__dirname, './landing.component.ts'),
    'utf-8',
  );

  it('[RÉGRESSION] prix Audit Standard = 390 € HT (pas 890 €)', () => {
    expect(src).toContain("'390 € HT'");
    expect(src).not.toContain("'890 €'");
  });

  it('[RÉGRESSION] nombre de modules = 21 (pas 19)', () => {
    expect(src).toContain("'21 modules'");
    expect(src).not.toContain("'19 modules'");
  });

  it('[RÉGRESSION] login redirige vers /cyberscan (landing) et non /cyberscan/dashboard', () => {
    // submitLogin() et submitLoginTotp() doivent naviguer vers /cyberscan après connexion
    const loginFnMatch = src.match(/submitLogin\(\)\s*\{[\s\S]+?^  \}/m);
    if (loginFnMatch) {
      expect(loginFnMatch[0]).toContain("'/cyberscan'");
      expect(loginFnMatch[0]).not.toContain("'/cyberscan/dashboard'");
    }
    const totpFnMatch = src.match(/submitLoginTotp\(\)\s*\{[\s\S]+?^  \}/m);
    if (totpFnMatch) {
      expect(totpFnMatch[0]).toContain("'/cyberscan'");
      expect(totpFnMatch[0]).not.toContain("'/cyberscan/dashboard'");
    }
  });

  it('[RÉGRESSION] ngOnInit ne redirige pas les utilisateurs authentifiés (landing accessible)', () => {
    // La landing doit être accessible même quand l\'utilisateur est connecté
    const ngOnInitMatch = src.match(/ngOnInit\(\)\s*\{[\s\S]+?^  \}/m);
    if (ngOnInitMatch) {
      expect(ngOnInitMatch[0]).not.toContain("navigate(['/cyberscan/dashboard'])");
    }
  });

  it('[RÉGRESSION] inscription redirige vers /cyberscan/onboarding (pas la landing)', () => {
    // submitRegister() doit naviguer vers /cyberscan/onboarding
    const registerFnMatch = src.match(/submitRegister\(\)\s*\{[\s\S]+?^  \}/m);
    if (registerFnMatch) {
      expect(registerFnMatch[0]).toContain('/cyberscan/onboarding');
    }
  });
});
