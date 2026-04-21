/**
 * LandingComponent — tests des méthodes utilitaires pures + non-régression données statiques.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { LandingComponent } from './landing.component';

function make(): LandingComponent {
  return Object.create(LandingComponent.prototype) as LandingComponent;
}

const src = readFileSync(resolve(__dirname, './landing.component.ts'), 'utf-8');

// ── formatPrice() ─────────────────────────────────────────────────────────────

describe('LandingComponent — formatPrice()', () => {
  it('convertit les centimes en euros', () => {
    const result = make().formatPrice(900);
    expect(result).toContain('9');
    expect(result).toContain('€');
  });

  it('formate 2900 centimes', () => {
    expect(make().formatPrice(2900)).toContain('29');
  });

  it('formate 7900 centimes', () => {
    expect(make().formatPrice(7900)).toContain('79');
  });

  it('formate 0 centimes', () => {
    const result = make().formatPrice(0);
    expect(result).toContain('0');
    expect(result).toContain('€');
  });
});

// ── getPlanFeatures() ─────────────────────────────────────────────────────────

describe('LandingComponent — getPlanFeatures()', () => {
  it('inclut max_sites dans les features', () => {
    const plan: any = { max_sites: 3, scan_interval_days: 7, tier_level: 2 };
    expect(make().getPlanFeatures(plan).some(f => f.includes('3'))).toBe(true);
  });

  it('inclut scan_interval_days dans les features', () => {
    const plan: any = { max_sites: 1, scan_interval_days: 30, tier_level: 2 };
    expect(make().getPlanFeatures(plan).some(f => f.includes('30'))).toBe(true);
  });

  it('inclut "Rapport PDF" dans toutes les features', () => {
    const plan: any = { max_sites: 1, scan_interval_days: 30, tier_level: 1 };
    expect(make().getPlanFeatures(plan).some(f => f.includes('Rapport PDF'))).toBe(true);
  });

  it('ajoute les modules Tier 3 si tier_level >= 3', () => {
    const plan: any = { max_sites: 5, scan_interval_days: 7, tier_level: 3 };
    expect(make().getPlanFeatures(plan).some(f => f.includes('Tier 3'))).toBe(true);
  });

  it("n'ajoute pas les modules Tier 3 si tier_level < 3", () => {
    const plan: any = { max_sites: 1, scan_interval_days: 30, tier_level: 2 };
    expect(make().getPlanFeatures(plan).some(f => f.includes('Tier 3'))).toBe(false);
  });

  it('ajoute les modules Tier 4 si tier_level >= 4', () => {
    const plan: any = { max_sites: 10, scan_interval_days: 7, tier_level: 4 };
    expect(make().getPlanFeatures(plan).some(f => f.includes('Tier 4'))).toBe(true);
  });

  it("n'ajoute pas les modules Tier 4 si tier_level < 4", () => {
    const plan: any = { max_sites: 5, scan_interval_days: 7, tier_level: 3 };
    expect(make().getPlanFeatures(plan).some(f => f.includes('Tier 4'))).toBe(false);
  });

  it('retourne au moins 4 features pour un plan Tier 1', () => {
    const plan: any = { max_sites: 1, scan_interval_days: 30, tier_level: 1 };
    expect(make().getPlanFeatures(plan).length).toBeGreaterThanOrEqual(4);
  });
});

// ── getPlanBadge() ────────────────────────────────────────────────────────────

describe('LandingComponent — getPlanBadge()', () => {
  it('retourne "Populaire" pour le plan pro', () => {
    expect(make().getPlanBadge({ name: 'pro' } as any)).toBe('Populaire');
  });

  it('retourne "Pro" pour le plan business', () => {
    expect(make().getPlanBadge({ name: 'business' } as any)).toBe('Pro');
  });

  it('retourne une chaîne vide pour le plan starter', () => {
    expect(make().getPlanBadge({ name: 'starter' } as any)).toBe('');
  });

  it('retourne une chaîne vide pour un plan inconnu', () => {
    expect(make().getPlanBadge({ name: 'unknown' } as any)).toBe('');
  });
});

// ── features (9 modules) ──────────────────────────────────────────────────────

describe('LandingComponent — features array (9 modules)', () => {
  it('contient exactement 9 features', () => {
    const matches = src.match(/\{ icon:.*?title:.*?desc:.*?\}/gs) ?? [];
    const featureBlock = src.match(/features\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    const count = (featureBlock.match(/icon:/g) ?? []).length;
    expect(count).toBe(9);
  });

  it('contient "Analyse SSL/TLS"', () => {
    expect(src).toContain("'Analyse SSL/TLS'");
  });

  it('contient "Scanner URL"', () => {
    expect(src).toContain("'Scanner URL'");
  });

  it('contient "Scan de code"', () => {
    expect(src).toContain("'Scan de code'");
  });

  it('contient "Conformité NIS2 / ISO 27001"', () => {
    expect(src).toContain("'Conformité NIS2 / ISO 27001'");
  });

  it('contient "Threat Intelligence"', () => {
    expect(src).toContain("'Threat Intelligence'");
  });

  it('contient "Audit JWT"', () => {
    expect(src).toContain("'Audit JWT'");
  });
});

// ── testimonials (6) ──────────────────────────────────────────────────────────

describe('LandingComponent — testimonials (6 témoignages)', () => {
  it('contient exactement 6 témoignages', () => {
    const block = src.match(/testimonials\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    const count = (block.match(/name:/g) ?? []).length;
    expect(count).toBe(6);
  });

  it('contient Sophie M.', () => {
    expect(src).toContain("'Sophie M.'");
  });

  it('contient Marc D. (nouveau)', () => {
    expect(src).toContain("'Marc D.'");
  });

  it('contient Chloé V. (nouvelle)', () => {
    expect(src).toContain("'Chloé V.'");
  });

  it('contient Antoine P. (nouveau)', () => {
    expect(src).toContain("'Antoine P.'");
  });

  it('chaque témoignage a un avatar d\'une seule lettre majuscule', () => {
    const block = src.match(/testimonials\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    const avatars = [...block.matchAll(/avatar:\s*'([A-Z])'/g)].map(m => m[1]);
    expect(avatars.length).toBe(6);
    avatars.forEach(a => expect(a).toMatch(/^[A-Z]$/));
  });
});

// ── faqs (10 questions) ───────────────────────────────────────────────────────

describe('LandingComponent — faqs (10 questions)', () => {
  it('contient exactement 10 FAQ', () => {
    const block = src.match(/faqs\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    const count = (block.match(/q:/g) ?? []).length;
    expect(count).toBe(10);
  });

  it('contient une FAQ sur le scan de code', () => {
    expect(src).toContain('scan de code fonctionne');
  });

  it('contient une FAQ sur NIS2 / ISO 27001', () => {
    expect(src).toContain('NIS2 ou ISO 27001');
  });

  it('chaque FAQ a un champ q et un champ a', () => {
    const block = src.match(/faqs\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    const qCount = (block.match(/\bq:/g) ?? []).length;
    const aCount = (block.match(/\ba:/g) ?? []).length;
    expect(qCount).toBe(aCount);
    expect(qCount).toBe(10);
  });
});

// ── auditOffers (4 offres) ────────────────────────────────────────────────────

describe('LandingComponent — auditOffers (4 offres)', () => {
  it('contient exactement 4 offres d\'audit', () => {
    const block = src.match(/auditOffers\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    const count = (block.match(/name:/g) ?? []).length;
    expect(count).toBe(4);
  });

  it('contient l\'offre "Audit Flash" à 290 €', () => {
    expect(src).toContain("'Audit Flash'");
    expect(src).toContain("'290 €'");
  });

  it('contient l\'offre "Audit Standard" à 390 €', () => {
    expect(src).toContain("'Audit Standard'");
    expect(src).toContain("'390 €'");
  });

  it("contient l'offre \"Conformité NIS2 / RGPD\" à 890 €", () => {
    expect(src).toContain("'Conformité NIS2 / RGPD'");
    expect(src).toContain("'890 €'");
  });

  it('contient l\'offre "Audit Complet" sur devis', () => {
    expect(src).toContain("'Audit Complet'");
    expect(src).toContain("'Sur devis'");
  });

  it('une seule offre est featured (Audit Standard)', () => {
    const block = src.match(/auditOffers\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    const featured = (block.match(/featured:\s*true/g) ?? []).length;
    expect(featured).toBe(1);
  });

  it('chaque offre a un champ items non vide', () => {
    const block = src.match(/auditOffers\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    const itemsBlocks = (block.match(/items:\s*\[/g) ?? []).length;
    expect(itemsBlocks).toBe(4);
  });
});

// ── comparisonRows (16 lignes + colonne enterprise) ───────────────────────────

describe('LandingComponent — comparisonRows (16 lignes, colonne enterprise)', () => {
  it('contient exactement 16 lignes', () => {
    const block = src.match(/comparisonRows\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    const count = (block.match(/label:/g) ?? []).length;
    expect(count).toBe(16);
  });

  it('chaque ligne a un champ enterprise', () => {
    const block = src.match(/comparisonRows\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    const labelCount = (block.match(/label:/g) ?? []).length;
    const enterpriseCount = (block.match(/enterprise:/g) ?? []).length;
    expect(enterpriseCount).toBe(labelCount);
  });

  it('contient "Sites surveillés"', () => {
    expect(src).toContain("'Sites surveillés'");
  });

  it('contient "Accès API REST"', () => {
    expect(src).toContain("'Accès API REST'");
  });

  it('contient "Account manager dédié"', () => {
    expect(src).toContain("'Account manager dédié'");
  });

  it('contient "Webhooks & intégrations"', () => {
    expect(src).toContain("'Webhooks & intégrations'");
  });

  it('contient "Scan de code (SAST/SCA)"', () => {
    expect(src).toContain("'Scan de code (SAST/SCA)'");
  });

  it('contient "Alerte SSL expiration"', () => {
    expect(src).toContain("'Alerte SSL expiration'");
  });

  it('enterprise = "Illimités" pour les sites surveillés', () => {
    expect(src).toContain("enterprise: 'Illimités'");
  });

  it('enterprise = "Temps réel" pour la fréquence', () => {
    expect(src).toContain("enterprise: 'Temps réel'");
  });
});

// ── howItWorks (3 étapes) ─────────────────────────────────────────────────────

describe('LandingComponent — howItWorks (3 étapes)', () => {
  it('contient exactement 3 étapes', () => {
    const block = src.match(/howItWorks\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    const count = (block.match(/step:/g) ?? []).length;
    expect(count).toBe(3);
  });

  it("l'étape 1 concerne l'URL", () => {
    expect(src).toContain("'Entrez votre URL'");
  });

  it("l'étape 2 concerne l'analyse", () => {
    expect(src).toContain("'Analyse automatique'");
  });

  it("l'étape 3 concerne le rapport PDF", () => {
    expect(src).toContain("'Rapport PDF + plan d\\'action'");
  });

  it('les numéros d\'étapes sont 01, 02, 03', () => {
    expect(src).toContain("'01'");
    expect(src).toContain("'02'");
    expect(src).toContain("'03'");
  });

  it('chaque étape a icon, title et desc', () => {
    const block = src.match(/howItWorks\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    expect((block.match(/icon:/g) ?? []).length).toBe(3);
    expect((block.match(/title:/g) ?? []).length).toBe(3);
    expect((block.match(/desc:/g) ?? []).length).toBe(3);
  });
});

// ── useCases (4 profils) ──────────────────────────────────────────────────────

describe('LandingComponent — useCases (4 cas d\'usage)', () => {
  it('contient exactement 4 cas d\'usage', () => {
    const block = src.match(/useCases\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    const count = (block.match(/title:/g) ?? []).length;
    expect(count).toBe(4);
  });

  it('contient le profil "Startups & SaaS"', () => {
    expect(src).toContain("'Startups & SaaS'");
  });

  it('contient le profil "Agences web"', () => {
    expect(src).toContain("'Agences web'");
  });

  it('contient le profil "PME & ETI"', () => {
    expect(src).toContain("'PME & ETI'");
  });

  it('contient le profil "E-commerce"', () => {
    expect(src).toContain("'E-commerce'");
  });

  it('chaque profil a icon, color, bg, title, desc et points', () => {
    const block = src.match(/useCases\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    expect((block.match(/\bicon:/g) ?? []).length).toBe(4);
    expect((block.match(/color:/g) ?? []).length).toBe(4);
    expect((block.match(/bg:/g) ?? []).length).toBe(4);
    expect((block.match(/points:/g) ?? []).length).toBe(4);
  });

  it('chaque profil a au moins 3 points', () => {
    const block = src.match(/useCases\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    const pointsBlocks = [...block.matchAll(/points:\s*\[([\s\S]*?)\]/g)];
    pointsBlocks.forEach(match => {
      const count = (match[1].match(/'/g) ?? []).length / 2;
      expect(count).toBeGreaterThanOrEqual(3);
    });
  });
});

// ── cyberStats (4 statistiques) ───────────────────────────────────────────────

describe('LandingComponent — cyberStats (4 statistiques)', () => {
  it('contient exactement 4 statistiques', () => {
    const block = src.match(/cyberStats\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    const count = (block.match(/value:/g) ?? []).length;
    expect(count).toBe(4);
  });

  it('contient la stat IBM sur le coût moyen (4,88 M$)', () => {
    expect(src).toContain("'4,88 M\$'");
  });

  it('contient la stat Mandiant sur le délai de détection (194 jours)', () => {
    expect(src).toContain("'194 jours'");
  });

  it('contient la stat Verizon sur les erreurs humaines (82 %)', () => {
    expect(src).toContain("'82 %'");
  });

  it('la 4e stat concerne le prix CyberScan (9,90 €)', () => {
    expect(src).toContain("'9,90 €'");
  });

  it('la source IBM est référencée', () => {
    expect(src).toContain('IBM Cost of a Data Breach');
  });

  it('la source Mandiant est référencée', () => {
    expect(src).toContain('Mandiant');
  });

  it('chaque stat a value, label et source', () => {
    const block = src.match(/cyberStats\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    expect((block.match(/value:/g) ?? []).length).toBe(4);
    expect((block.match(/label:/g) ?? []).length).toBe(4);
    expect((block.match(/source:/g) ?? []).length).toBe(4);
  });
});

// ── Non-régression comportement ───────────────────────────────────────────────

describe('LandingComponent — non-régression comportement', () => {
  it('[RÉGRESSION] login redirige vers /cyberscan (landing) et non /cyberscan/dashboard', () => {
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

  it('[RÉGRESSION] ngOnInit ne redirige pas les utilisateurs authentifiés', () => {
    const ngOnInitMatch = src.match(/ngOnInit\(\)\s*\{[\s\S]+?^  \}/m);
    if (ngOnInitMatch) {
      expect(ngOnInitMatch[0]).not.toContain("navigate(['/cyberscan/dashboard'])");
    }
  });

  it('[RÉGRESSION] inscription redirige vers /cyberscan/onboarding', () => {
    const registerFnMatch = src.match(/submitRegister\(\)\s*\{[\s\S]+?^  \}/m);
    if (registerFnMatch) {
      expect(registerFnMatch[0]).toContain('/cyberscan/onboarding');
    }
  });

  it('[RÉGRESSION] le prix de l\'Audit Standard est 390 € (sans HT dans le code)', () => {
    expect(src).toContain("'390 €'");
    expect(src).not.toContain("'390 € HT'");
  });

  it('[RÉGRESSION] l\'architecture affiche 21 modules', () => {
    expect(src).toContain("'21 modules'");
  });

  it('[RÉGRESSION] email de contact est cyberscanapp.com', () => {
    expect(src).toContain('cyberscanapp.com');
  });

  it('[RÉGRESSION] l\'Enterprise est sur devis (pas un prix fixe)', () => {
    expect(src).not.toContain("'Enterprise': '");
    expect(src).toContain("enterprise: 'Illimités'");
  });
});
