/**
 * LandingComponent — tests des méthodes utilitaires pures + non-régression données statiques.
 */
import { describe, it, expect, vi } from 'vitest';
import { signal } from '@angular/core';
import { of, throwError } from 'rxjs';
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { LandingComponent } from './landing.component';

const html = readFileSync(resolve(__dirname, './landing.component.html'), 'utf-8');

function make(): LandingComponent {
  return Object.create(LandingComponent.prototype) as LandingComponent;
}

const src = readFileSync(resolve(__dirname, './landing.data.ts'), 'utf-8');

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
  it('inclut le nombre de sites surveillés', () => {
    const plan: any = { max_sites: 3, scan_interval_days: 7, tier_level: 2 };
    expect(
      make()
        .getPlanFeatures(plan)
        .some(f => f.label.includes('3'))
    ).toBe(true);
  });

  it('affiche la fréquence de scan en clair (mensuelle)', () => {
    const plan: any = { max_sites: 1, scan_interval_days: 30, tier_level: 2 };
    expect(
      make()
        .getPlanFeatures(plan)
        .some(f => f.label.toLowerCase().includes('mensuelle'))
    ).toBe(true);
  });

  it('affiche "Scan à la demande" quand l\'intervalle est 0 (plan gratuit)', () => {
    const plan: any = { max_sites: 1, scan_interval_days: 0, tier_level: 1 };
    expect(
      make()
        .getPlanFeatures(plan)
        .some(f => f.label.includes('à la demande'))
    ).toBe(true);
  });

  it('inclut "Sécurité essentielle" avec un détail technique (tooltip)', () => {
    const plan: any = { max_sites: 1, scan_interval_days: 30, tier_level: 1 };
    const f = make()
      .getPlanFeatures(plan)
      .find(x => x.label === 'Sécurité essentielle');
    expect(f).toBeDefined();
    expect(f?.detail).toBeTruthy();
  });

  it('ajoute "Analyse avancée" si tier_level >= 3', () => {
    const plan: any = { max_sites: 5, scan_interval_days: 7, tier_level: 3 };
    expect(
      make()
        .getPlanFeatures(plan)
        .some(f => f.label.includes('avancée'))
    ).toBe(true);
  });

  it("n'ajoute pas l'analyse avancée si tier_level < 3", () => {
    const plan: any = { max_sites: 1, scan_interval_days: 30, tier_level: 2 };
    expect(
      make()
        .getPlanFeatures(plan)
        .some(f => f.label.includes('avancée'))
    ).toBe(false);
  });

  it('ajoute "Analyse experte" si tier_level >= 4', () => {
    const plan: any = { max_sites: 10, scan_interval_days: 7, tier_level: 4 };
    expect(
      make()
        .getPlanFeatures(plan)
        .some(f => f.label.includes('experte'))
    ).toBe(true);
  });

  it("n'ajoute pas l'analyse experte si tier_level < 4", () => {
    const plan: any = { max_sites: 5, scan_interval_days: 7, tier_level: 3 };
    expect(
      make()
        .getPlanFeatures(plan)
        .some(f => f.label.includes('experte'))
    ).toBe(false);
  });

  it('ne montre aucun jargon "Tier" à l\'utilisateur', () => {
    const plan: any = { max_sites: 10, scan_interval_days: 7, tier_level: 4 };
    expect(
      make()
        .getPlanFeatures(plan)
        .some(f => f.label.includes('Tier'))
    ).toBe(false);
  });

  it('retourne au moins 4 features pour un plan de base', () => {
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

// ── features (10 modules) ──────────────────────────────────────────────────────

describe('LandingComponent — features array (10 modules)', () => {
  it('contient exactement 10 features', () => {
    const featureBlock = src.match(/FEATURES\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    const count = (featureBlock.match(/icon:/g) ?? []).length;
    expect(count).toBe(10);
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

  it('contient "Sensibilisation NIS2"', () => {
    expect(src).toContain("'Sensibilisation NIS2'");
  });
});

// ── testimonials (6) ──────────────────────────────────────────────────────────

describe('LandingComponent — testimonials (7 témoignages)', () => {
  it('contient exactement 7 témoignages', () => {
    const block = src.match(/TESTIMONIALS\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    const count = (block.match(/name:/g) ?? []).length;
    expect(count).toBe(7);
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

  it('contient Isabelle K. (sensibilisation NIS2)', () => {
    expect(src).toContain("'Isabelle K.'");
  });

  it("chaque témoignage a un avatar d'une seule lettre majuscule", () => {
    const block = src.match(/TESTIMONIALS\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    const avatars = [...block.matchAll(/avatar:\s*'([A-Z])'/g)].map(m => m[1]);
    expect(avatars.length).toBe(7);
    avatars.forEach(a => expect(a).toMatch(/^[A-Z]$/));
  });
});

// ── faqs (10 questions) ───────────────────────────────────────────────────────

describe('LandingComponent — faqs (10 questions)', () => {
  it('contient exactement 10 FAQ', () => {
    const block = src.match(/FAQS\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
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
    const block = src.match(/FAQS\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    const qCount = (block.match(/\bq:/g) ?? []).length;
    const aCount = (block.match(/\ba:/g) ?? []).length;
    expect(qCount).toBe(aCount);
    expect(qCount).toBe(10);
  });
});

// ── auditOffers (4 offres) ────────────────────────────────────────────────────

describe('LandingComponent — auditOffers (4 offres)', () => {
  it("contient exactement 4 offres d'audit", () => {
    const block = src.match(/AUDIT_OFFERS\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    const count = (block.match(/name:/g) ?? []).length;
    expect(count).toBe(4);
  });

  it('contient l\'offre "Audit Flash" à 390 €', () => {
    expect(src).toContain("'Audit Flash'");
    expect(src).toContain("'390 €'");
  });

  it('contient l\'offre "App-Check" à 990 €', () => {
    expect(src).toContain("'App-Check'");
    expect(src).toContain("'990 €'");
  });

  it('contient l\'offre "Audit NIS2 / RGPD" à 1 290 €', () => {
    expect(src).toContain("'Audit NIS2 / RGPD'");
    expect(src).toContain("'1 290 €'");
  });

  it('contient l\'offre "Pentest léger" à 2 490 €', () => {
    expect(src).toContain("'Pentest léger'");
    expect(src).toContain("'2 490 €'");
  });

  it('une seule offre est featured (App-Check)', () => {
    const block = src.match(/AUDIT_OFFERS\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    const featured = (block.match(/featured:\s*true/g) ?? []).length;
    expect(featured).toBe(1);
  });

  it('chaque offre a un champ items non vide', () => {
    const block = src.match(/AUDIT_OFFERS\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    const itemsBlocks = (block.match(/items:\s*\[/g) ?? []).length;
    expect(itemsBlocks).toBe(4);
  });
});

// ── comparisonRows (18 lignes + colonne enterprise) ───────────────────────────

describe('LandingComponent — comparisonRows (18 lignes, colonne enterprise)', () => {
  it('contient exactement 18 lignes', () => {
    const block = src.match(/COMPARISON_ROWS\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    const count = (block.match(/label:/g) ?? []).length;
    expect(count).toBe(18);
  });

  it('chaque ligne a un champ enterprise', () => {
    const block = src.match(/COMPARISON_ROWS\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
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
    const block = src.match(/HOW_IT_WORKS\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
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
    expect(src).toContain("Rapport PDF + plan d'action");
  });

  it("les numéros d'étapes sont 01, 02, 03", () => {
    expect(src).toContain("'01'");
    expect(src).toContain("'02'");
    expect(src).toContain("'03'");
  });

  it('chaque étape a icon, title et desc', () => {
    const block = src.match(/HOW_IT_WORKS\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    expect((block.match(/icon:/g) ?? []).length).toBe(3);
    expect((block.match(/title:/g) ?? []).length).toBe(3);
    expect((block.match(/desc:/g) ?? []).length).toBe(3);
  });
});

// ── useCases (4 profils) ──────────────────────────────────────────────────────

describe("LandingComponent — useCases (4 cas d'usage)", () => {
  it("contient exactement 4 cas d'usage", () => {
    const block = src.match(/USE_CASES\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
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
    const block = src.match(/USE_CASES\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    expect((block.match(/\bicon:/g) ?? []).length).toBe(4);
    expect((block.match(/color:/g) ?? []).length).toBe(4);
    expect((block.match(/bg:/g) ?? []).length).toBe(4);
    expect((block.match(/points:/g) ?? []).length).toBe(4);
  });

  it('chaque profil a au moins 3 points', () => {
    const block = src.match(/USE_CASES\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
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
    const block = src.match(/CYBER_STATS\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
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

  it('la 4e stat concerne le prix Rocher Cybersécurité (14,90 €)', () => {
    expect(src).toContain("'14,90 €'");
  });

  it('la source IBM est référencée', () => {
    expect(src).toContain('IBM Cost of a Data Breach');
  });

  it('la source Mandiant est référencée', () => {
    expect(src).toContain('Mandiant');
  });

  it('chaque stat a value, label et source', () => {
    const block = src.match(/CYBER_STATS\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
    expect((block.match(/value:/g) ?? []).length).toBe(4);
    expect((block.match(/label:/g) ?? []).length).toBe(4);
    expect((block.match(/source:/g) ?? []).length).toBe(4);
  });
});

// ── Non-régression comportement ───────────────────────────────────────────────

const authModalSrc = readFileSync(
  resolve(__dirname, './components/auth-modal/auth-modal.component.ts'),
  'utf-8'
);
const landingSrc = readFileSync(resolve(__dirname, './landing.component.ts'), 'utf-8');

describe('LandingComponent — non-régression comportement', () => {
  it('[RÉGRESSION] login redirige vers /cyberscan (landing) et non /cyberscan/dashboard', () => {
    const loginFnMatch = authModalSrc.match(/submitLogin\(\)\s*\{[\s\S]+?^  \}/m);
    if (loginFnMatch) {
      expect(loginFnMatch[0]).toContain("'/'");
      expect(loginFnMatch[0]).not.toContain("'/dashboard'");
    }
    const totpFnMatch = authModalSrc.match(/submitLoginTotp\(\)\s*\{[\s\S]+?^  \}/m);
    if (totpFnMatch) {
      expect(totpFnMatch[0]).toContain("'/'");
      expect(totpFnMatch[0]).not.toContain("'/dashboard'");
    }
  });

  it('[RÉGRESSION] ngOnInit ne redirige pas les utilisateurs authentifiés', () => {
    const ngOnInitMatch = landingSrc.match(/ngOnInit\(\)\s*\{[\s\S]+?^  \}/m);
    if (ngOnInitMatch) {
      expect(ngOnInitMatch[0]).not.toContain("navigate(['/dashboard'])");
    }
  });

  it('[RÉGRESSION] inscription redirige vers /cyberscan/onboarding', () => {
    const registerFnMatch = authModalSrc.match(/submitRegister\(\)\s*\{[\s\S]+?^  \}/m);
    if (registerFnMatch) {
      expect(registerFnMatch[0]).toContain('/onboarding');
    }
  });

  it("[RÉGRESSION] le prix de l'App-Check est 990 € (sans HT dans le code)", () => {
    expect(src).toContain("'990 €'");
    expect(src).not.toContain("'990 € HT'");
  });

  it("[RÉGRESSION] l'architecture affiche 21 modules", () => {
    expect(src).toContain("'21 modules'");
  });

  it('[RÉGRESSION] email de contact est rochercybersecurite.com', () => {
    expect(landingSrc).toContain('rochercybersecurite.com');
  });

  it("[RÉGRESSION] l'Enterprise est sur devis (pas un prix fixe)", () => {
    expect(src).toContain("enterprise: 'Illimités'");
  });
});

// ── Navbar — liens pages publiques ───────────────────────────────────────────

describe('LandingComponent — navbar (liens pages publiques)', () => {
  it('contient un lien vers /cyberscan/blog dans la navbar', () => {
    expect(html).toContain('/blog');
  });

  it('[SUPPRIMÉ] scan-gratuit retiré de la navbar', () => {
    const navBlock = html.match(/<nav[\s\S]*?<\/nav>/)?.[0] ?? '';
    expect(navBlock).not.toContain('/scan-gratuit');
  });

  it('[RÉGRESSION] la navbar contient toujours Ressources', () => {
    expect(html).toContain('/ressources');
  });

  it('[RÉGRESSION] la navbar contient toujours Bonnes pratiques', () => {
    expect(html).toContain('/bonnes-pratiques');
  });

  it('[RÉGRESSION] la navbar contient toujours le lien Dashboard pour les connectés', () => {
    expect(html).toContain('/dashboard');
  });

  it('[RÉGRESSION] la navbar contient toujours le lien coffre-fort pour les connectés', () => {
    expect(html).toContain('/vault');
  });

  it('Blog est présent dans le nav', () => {
    const navBlock = html.match(/<nav[\s\S]*?<\/nav>/)?.[0] ?? '';
    expect(navBlock).toContain('/blog');
  });
});

// ── toggleFaq() ────────────────────────────────────────────────────────────────

describe('LandingComponent — toggleFaq()', () => {
  function makeComp(): LandingComponent {
    const c = make();
    (c as any).openFaqIndex = signal<number | null>(null);
    return c;
  }

  it('ouvre une FAQ fermée', () => {
    const c = makeComp();
    c.toggleFaq(2);
    expect(c.openFaqIndex()).toBe(2);
  });

  it('referme la FAQ si on reclique dessus', () => {
    const c = makeComp();
    c.toggleFaq(2);
    c.toggleFaq(2);
    expect(c.openFaqIndex()).toBeNull();
  });

  it('bascule vers une autre FAQ', () => {
    const c = makeComp();
    c.toggleFaq(1);
    c.toggleFaq(3);
    expect(c.openFaqIndex()).toBe(3);
  });

  it("ouvre la FAQ d'index 0", () => {
    const c = makeComp();
    c.toggleFaq(0);
    expect(c.openFaqIndex()).toBe(0);
  });
});

// ── getPlanFeatures() — branches sites (singulier / pluriel / illimité) ─────────

describe('LandingComponent — getPlanFeatures() sites', () => {
  it('affiche "Sites illimités" quand max_sites < 0 (plan gratuit)', () => {
    const plan: any = { max_sites: -1, scan_interval_days: 0, tier_level: 1 };
    expect(
      make()
        .getPlanFeatures(plan)
        .some(f => f.label === 'Sites illimités')
    ).toBe(true);
  });

  it('utilise le singulier pour 1 site (site surveillé)', () => {
    const plan: any = { max_sites: 1, scan_interval_days: 30, tier_level: 1 };
    const label = make()
      .getPlanFeatures(plan)
      .find(f => f.label.includes('site'))!.label;
    expect(label).toContain('1 site surveillé');
    expect(label).not.toContain('sites');
  });

  it('utilise le pluriel pour plusieurs sites (sites surveillés)', () => {
    const plan: any = { max_sites: 5, scan_interval_days: 7, tier_level: 1 };
    const label = make()
      .getPlanFeatures(plan)
      .find(f => f.label.includes('site'))!.label;
    expect(label).toContain('5 sites surveillés');
  });

  it('ajoute "Analyse de code (SAST/SCA)" si tier_level >= 2', () => {
    const plan: any = { max_sites: 3, scan_interval_days: 7, tier_level: 2 };
    expect(
      make()
        .getPlanFeatures(plan)
        .some(f => f.label.includes('SAST/SCA'))
    ).toBe(true);
  });

  it("n'ajoute pas l'analyse de code si tier_level < 2", () => {
    const plan: any = { max_sites: 1, scan_interval_days: 30, tier_level: 1 };
    expect(
      make()
        .getPlanFeatures(plan)
        .some(f => f.label.includes('SAST/SCA'))
    ).toBe(false);
  });

  it('ajoute la surveillance Dark Web à partir du tier_level 3', () => {
    const plan: any = { max_sites: 5, scan_interval_days: 7, tier_level: 3 };
    expect(
      make()
        .getPlanFeatures(plan)
        .some(f => f.label.includes('Dark Web'))
    ).toBe(true);
  });
});

// ── getters isLoggedIn / userInitials ──────────────────────────────────────────

describe('LandingComponent — isLoggedIn', () => {
  it('retourne true quand authentifié', () => {
    const c = make();
    (c as any).auth = { isAuthenticated: () => true };
    expect(c.isLoggedIn).toBe(true);
  });

  it('retourne false quand non authentifié', () => {
    const c = make();
    (c as any).auth = { isAuthenticated: () => false };
    expect(c.isLoggedIn).toBe(false);
  });
});

describe('LandingComponent — userInitials', () => {
  it('retourne les 2 premières lettres en majuscules', () => {
    const c = make();
    (c as any).auth = { getCurrentEmail: () => 'sophie@exemple.fr' };
    expect(c.userInitials).toBe('SO');
  });

  it('retourne une chaîne vide quand aucun email', () => {
    const c = make();
    (c as any).auth = { getCurrentEmail: () => null };
    expect(c.userInitials).toBe('');
  });
});

// ── logout() / openAuth() ──────────────────────────────────────────────────────

describe('LandingComponent — logout()', () => {
  it('délègue à auth.logout()', () => {
    const c = make();
    const logout = vi.fn();
    (c as any).auth = { logout };
    c.logout();
    expect(logout).toHaveBeenCalledOnce();
  });
});

describe('LandingComponent — openAuth()', () => {
  it('ouvre la modale en mode login', () => {
    const c = make();
    const open = vi.fn();
    (c as any).authModal = { open };
    c.openAuth('login');
    expect(open).toHaveBeenCalledWith('login');
  });

  it('ouvre la modale en mode register', () => {
    const c = make();
    const open = vi.fn();
    (c as any).authModal = { open };
    c.openAuth('register');
    expect(open).toHaveBeenCalledWith('register');
  });
});

// ── subscribe(plan) ────────────────────────────────────────────────────────────

describe('LandingComponent — subscribe()', () => {
  it("ouvre la modale d'inscription si non authentifié et ne lance pas de checkout", () => {
    const c = make();
    const open = vi.fn();
    const createCheckout = vi.fn();
    (c as any).auth = { isAuthenticated: () => false };
    (c as any).authModal = { open };
    (c as any).cyberscan = (c as any).billing = { createCheckout };
    c.subscribe({ id: 1 } as any);
    expect(open).toHaveBeenCalledWith('register');
    expect(createCheckout).not.toHaveBeenCalled();
  });

  it('lance le checkout et positionne checkoutLoading si authentifié', () => {
    const c = make();
    const createCheckout = vi.fn().mockReturnValue({ subscribe: vi.fn() });
    (c as any).auth = { isAuthenticated: () => true };
    (c as any).cyberscan = (c as any).billing = { createCheckout };
    c.subscribe({ id: 42 } as any);
    expect(createCheckout).toHaveBeenCalledWith(42);
    expect(c.checkoutLoading).toBe(42);
  });

  it("réinitialise checkoutLoading à null en cas d'erreur de checkout", () => {
    const c = make();
    (c as any).auth = { isAuthenticated: () => true };
    (c as any).cyberscan = (c as any).billing = {
      createCheckout: vi.fn().mockReturnValue(throwError(() => ({ status: 500 }))),
    };
    c.subscribe({ id: 7 } as any);
    expect(c.checkoutLoading).toBeNull();
  });
});

// ── subscribeNewsletter() ──────────────────────────────────────────────────────

describe('LandingComponent — subscribeNewsletter()', () => {
  function makeComp(invalid: boolean): LandingComponent {
    const c = make();
    (c as any).newsletterForm = {
      invalid,
      getRawValue: () => ({ email: 'test@exemple.fr' }),
    };
    c.newsletterLoading = false;
    c.newsletterSent = false;
    c.newsletterError = null;
    return c;
  }

  it("n'appelle pas le backend si le formulaire est invalide", () => {
    const c = makeComp(true);
    const post = vi.fn();
    (c as any).http = { post };
    c.subscribeNewsletter();
    expect(post).not.toHaveBeenCalled();
  });

  it('marque newsletterSent au succès', () => {
    const c = makeComp(false);
    (c as any).http = { post: vi.fn().mockReturnValue(of({})) };
    c.subscribeNewsletter();
    expect(c.newsletterSent).toBe(true);
    expect(c.newsletterLoading).toBe(false);
  });

  it('affiche un message dédié si déjà abonné (HTTP 409)', () => {
    const c = makeComp(false);
    (c as any).http = { post: vi.fn().mockReturnValue(throwError(() => ({ status: 409 }))) };
    c.subscribeNewsletter();
    expect(c.newsletterError).toContain('déjà abonné');
    expect(c.newsletterLoading).toBe(false);
  });

  it('affiche un message générique pour les autres erreurs', () => {
    const c = makeComp(false);
    (c as any).http = { post: vi.fn().mockReturnValue(throwError(() => ({ status: 500 }))) };
    c.subscribeNewsletter();
    expect(c.newsletterError).toContain('erreur');
    expect(c.newsletterError).not.toContain('déjà abonné');
  });
});

// ── scrollToPricing() ──────────────────────────────────────────────────────────

describe('LandingComponent — scrollToPricing()', () => {
  it('empêche le comportement par défaut et scrolle vers #pricing', () => {
    const c = make();
    const scrollIntoView = vi.fn();
    const getElementById = vi.fn().mockReturnValue({ scrollIntoView });
    (c as any).doc = { getElementById };
    const event = { preventDefault: vi.fn() } as any;
    c.scrollToPricing(event);
    expect(event.preventDefault).toHaveBeenCalledOnce();
    expect(getElementById).toHaveBeenCalledWith('pricing');
    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth' });
  });

  it('ne plante pas si la section pricing est absente', () => {
    const c = make();
    (c as any).doc = { getElementById: vi.fn().mockReturnValue(null) };
    const event = { preventDefault: vi.fn() } as any;
    expect(() => c.scrollToPricing(event)).not.toThrow();
    expect(event.preventDefault).toHaveBeenCalledOnce();
  });
});

// ── animateCounters() ──────────────────────────────────────────────────────────

describe('LandingComponent — animateCounters()', () => {
  it("incrémente chaque compteur jusqu'à sa cible", () => {
    vi.useFakeTimers();
    const c = make();
    (c as any).counters = [
      { target: 100, current: signal(0) },
      { target: 60, current: signal(0) },
    ];
    c.animateCounters();
    vi.advanceTimersByTime(30 * 61);
    vi.useRealTimers();
    expect((c as any).counters[0].current()).toBe(100);
    expect((c as any).counters[1].current()).toBe(60);
  });

  it('ne dépasse jamais la cible', () => {
    vi.useFakeTimers();
    const c = make();
    (c as any).counters = [{ target: 99, current: signal(0) }];
    c.animateCounters();
    vi.advanceTimersByTime(30 * 200);
    vi.useRealTimers();
    expect((c as any).counters[0].current()).toBe(99);
  });
});
