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

  it('[RÉGRESSION] redirect 2FA vers /cyberscan (pas /cyberscan/dashboard)', () => {
    // submitLoginTotp() doit naviguer vers /cyberscan, pas le dashboard
    expect(src).toContain("navigate(['/cyberscan']");
    // S'assurer que le seul navigate dans submitLoginTotp pointe vers /cyberscan
    const totpFnMatch = src.match(/submitLoginTotp\(\)[^}]+}/s);
    if (totpFnMatch) {
      expect(totpFnMatch[0]).not.toContain('/cyberscan/dashboard');
    }
  });
});
