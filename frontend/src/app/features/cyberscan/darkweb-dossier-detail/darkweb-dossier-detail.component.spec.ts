import { describe, it, expect, vi } from 'vitest';
import { signal } from '@angular/core';
import { DarkwebDossierDetailComponent } from './darkweb-dossier-detail.component';
import { DarkwebDossierService, DossierDetail, DossierTarget } from '../services/darkweb-dossier.service';

function make(): DarkwebDossierDetailComponent {
  const comp = Object.create(DarkwebDossierDetailComponent.prototype) as DarkwebDossierDetailComponent;
  (comp as any).dossier = signal<DossierDetail | null>(null);
  (comp as any).loading = signal(false);
  (comp as any).downloadingPdf = signal(false);
  (comp as any).service = {
    parseBreachSources: DarkwebDossierService.prototype.parseBreachSources,
    parseTopSources: DarkwebDossierService.prototype.parseTopSources,
    getPdfUrl: vi.fn().mockReturnValue('/api/v1/darkweb-dossier/1/pdf'),
  };
  return comp;
}

function dossier(overrides: Partial<DossierDetail> = {}): DossierDetail {
  return {
    id: 1, company_name: 'Acme SAS', domain: 'acme.fr',
    status: 'completed', total_emails: 10, exposed_emails: 3,
    total_breach_instances: 7, risk_score: 30,
    top_sources_json: JSON.stringify([{ name: 'LinkedIn', count: 3 }]),
    error_message: null, created_at: '2024-01-01T00:00:00Z',
    started_at: null, finished_at: null, targets: [],
    ...overrides,
  };
}

function target(overrides: Partial<DossierTarget> = {}): DossierTarget {
  return {
    id: 1, email: 'alice@acme.fr', status: 'exposed', total_breaches: 2,
    breach_sources_json: JSON.stringify([{ name: 'LinkedIn', domain: 'linkedin.com', breach_date: '2021-06-22', pwn_count: 700000000, data_classes: ['Emails'], is_sensitive: false }]),
    checked_at: '2024-01-01T10:00:00Z',
    ...overrides,
  };
}

// ── riskColor ─────────────────────────────────────────────────────────────────

describe('DarkwebDossierDetailComponent — riskColor()', () => {
  it('gray pour null', () => expect(make().riskColor(null)).toContain('gray'));
  it('red pour score >= 50', () => expect(make().riskColor(50)).toContain('red'));
  it('red pour score = 100', () => expect(make().riskColor(100)).toContain('red'));
  it('yellow pour score entre 20 et 49', () => expect(make().riskColor(20)).toContain('yellow'));
  it('yellow pour score = 35', () => expect(make().riskColor(35)).toContain('yellow'));
  it('green pour score < 20', () => expect(make().riskColor(10)).toContain('green'));
  it('green pour score = 0', () => expect(make().riskColor(0)).toContain('green'));
});

// ── riskLabel ────────────────────────────────────────────────────────────────

describe('DarkwebDossierDetailComponent — riskLabel()', () => {
  it('retourne "Non calculé" pour null', () => expect(make().riskLabel(null)).toBe('Non calculé'));
  it('retourne "Risque élevé" pour >= 50', () => expect(make().riskLabel(50)).toBe('Risque élevé'));
  it('retourne "Risque élevé" pour 100', () => expect(make().riskLabel(100)).toBe('Risque élevé'));
  it('retourne "Risque modéré" pour 20', () => expect(make().riskLabel(20)).toBe('Risque modéré'));
  it('retourne "Risque modéré" pour 49', () => expect(make().riskLabel(49)).toBe('Risque modéré'));
  it('retourne "Risque faible" pour 0', () => expect(make().riskLabel(0)).toBe('Risque faible'));
  it('retourne "Risque faible" pour 19', () => expect(make().riskLabel(19)).toBe('Risque faible'));
});

// ── breachCountColor ─────────────────────────────────────────────────────────

describe('DarkwebDossierDetailComponent — breachCountColor()', () => {
  it('red pour count >= 3', () => expect(make().breachCountColor(3)).toContain('red'));
  it('red pour count = 10', () => expect(make().breachCountColor(10)).toContain('red'));
  it('yellow pour count = 1', () => expect(make().breachCountColor(1)).toContain('yellow'));
  it('yellow pour count = 2', () => expect(make().breachCountColor(2)).toContain('yellow'));
  it('green pour count = 0', () => expect(make().breachCountColor(0)).toContain('green'));
});

// ── statusLabel ───────────────────────────────────────────────────────────────

describe('DarkwebDossierDetailComponent — statusLabel()', () => {
  it('retourne "En attente" pour pending', () => expect(make().statusLabel('pending')).toBe('En attente'));
  it('retourne "Analyse en cours" pour processing', () => expect(make().statusLabel('processing')).toBe('Analyse en cours'));
  it('retourne "Terminé" pour completed', () => expect(make().statusLabel('completed')).toBe('Terminé'));
  it('retourne "Erreur" pour failed', () => expect(make().statusLabel('failed')).toBe('Erreur'));
  it('retourne la valeur brute pour un statut inconnu', () => expect(make().statusLabel('unknown')).toBe('unknown'));
});

// ── formatDate ────────────────────────────────────────────────────────────────

describe('DarkwebDossierDetailComponent — formatDate()', () => {
  it('retourne "—" pour null', () => expect(make().formatDate(null)).toBe('—'));
  it('retourne une date formatée contenant l\'année', () => {
    const result = make().formatDate('2024-03-15T10:00:00Z');
    expect(result).toContain('2024');
  });
});

// ── formatPwnCount ────────────────────────────────────────────────────────────

describe('DarkwebDossierDetailComponent — formatPwnCount()', () => {
  it('retourne "—" pour 0', () => expect(make().formatPwnCount(0)).toBe('—'));
  it('retourne la valeur pour < 1000', () => expect(make().formatPwnCount(999)).toBe('999'));
  it('retourne "1K" pour 1000', () => expect(make().formatPwnCount(1000)).toBe('1K'));
  it('retourne "700K" pour 700000', () => expect(make().formatPwnCount(700000)).toBe('700K'));
  it('retourne "1.5M" pour 1500000', () => expect(make().formatPwnCount(1500000)).toBe('1.5M'));
});

// ── exposedTargets / cleanTargets ─────────────────────────────────────────────

describe('DarkwebDossierDetailComponent — exposedTargets() / cleanTargets()', () => {
  it('exposedTargets retourne uniquement les targets exposées', () => {
    const comp = make();
    const targets = [
      target({ status: 'exposed' }),
      target({ id: 2, email: 'b@acme.fr', status: 'clean', total_breaches: 0 }),
      target({ id: 3, email: 'c@acme.fr', status: 'exposed' }),
    ];
    (comp as any).dossier.set(dossier({ targets }));
    expect(comp.exposedTargets()).toHaveLength(2);
    expect(comp.exposedTargets().every(t => t.status === 'exposed')).toBe(true);
  });

  it('cleanTargets retourne uniquement les targets saines', () => {
    const comp = make();
    const targets = [
      target({ status: 'exposed' }),
      target({ id: 2, email: 'b@acme.fr', status: 'clean', total_breaches: 0 }),
    ];
    (comp as any).dossier.set(dossier({ targets }));
    expect(comp.cleanTargets()).toHaveLength(1);
    expect(comp.cleanTargets()[0].email).toBe('b@acme.fr');
  });

  it('retourne [] si dossier est null', () => {
    const comp = make();
    expect(comp.exposedTargets()).toEqual([]);
    expect(comp.cleanTargets()).toEqual([]);
  });
});

// ── getBreaches ───────────────────────────────────────────────────────────────

describe('DarkwebDossierDetailComponent — getBreaches()', () => {
  it('parse les sources correctement', () => {
    const t = target();
    const breaches = make().getBreaches(t);
    expect(breaches).toHaveLength(1);
    expect(breaches[0].name).toBe('LinkedIn');
  });

  it('retourne [] pour un target sans sources', () => {
    const t = target({ breach_sources_json: null });
    expect(make().getBreaches(t)).toEqual([]);
  });
});

// ── getTopSources ─────────────────────────────────────────────────────────────

describe('DarkwebDossierDetailComponent — getTopSources()', () => {
  it('parse les top sources depuis le dossier', () => {
    const comp = make();
    (comp as any).dossier.set(dossier());
    const sources = comp.getTopSources();
    expect(sources).toHaveLength(1);
    expect(sources[0].name).toBe('LinkedIn');
    expect(sources[0].count).toBe(3);
  });

  it('retourne [] si dossier est null', () => {
    expect(make().getTopSources()).toEqual([]);
  });
});
