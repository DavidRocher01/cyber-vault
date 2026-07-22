import { describe, it, expect, vi } from 'vitest';
import { signal } from '@angular/core';
import { of, throwError } from 'rxjs';
import { DarkwebDossierDetailComponent } from './darkweb-dossier-detail.component';
import {
  DarkwebDossierService,
  DossierDetail,
  DossierTarget,
} from '../services/darkweb-dossier.service';

function make(): DarkwebDossierDetailComponent {
  const comp = Object.create(
    DarkwebDossierDetailComponent.prototype
  ) as DarkwebDossierDetailComponent;
  (comp as any).dossier = signal<DossierDetail | null>(null);
  (comp as any).loading = signal(false);
  (comp as any).downloadingPdf = signal(false);
  (comp as any).service = {
    parseBreachSources: DarkwebDossierService.prototype.parseBreachSources,
    parseTopSources: DarkwebDossierService.prototype.parseTopSources,
    buildBreachTimeline: DarkwebDossierService.prototype.buildBreachTimeline,
    getPdfUrl: vi.fn().mockReturnValue('/api/v1/darkweb-dossier/1/pdf'),
  };
  return comp;
}

function dossier(overrides: Partial<DossierDetail> = {}): DossierDetail {
  return {
    id: 1,
    company_name: 'Acme SAS',
    domain: 'acme.fr',
    status: 'completed',
    total_emails: 10,
    exposed_emails: 3,
    total_breach_instances: 7,
    checked_count: 10,
    unverified_count: 0,
    risk_score: 30,
    severity_score: 45,
    monitor_active: false,
    last_monitored_at: null,
    next_monitor_at: null,
    top_sources_json: JSON.stringify([{ name: 'LinkedIn', count: 3 }]),
    error_message: null,
    created_at: '2024-01-01T00:00:00Z',
    started_at: null,
    finished_at: null,
    targets: [],
    ...overrides,
  };
}

function target(overrides: Partial<DossierTarget> = {}): DossierTarget {
  return {
    id: 1,
    email: 'alice@acme.fr',
    status: 'exposed',
    check_status: 'exposed',
    total_breaches: 2,
    breach_sources_json: JSON.stringify([
      {
        name: 'LinkedIn',
        domain: 'linkedin.com',
        breach_date: '2021-06-22',
        pwn_count: 700000000,
        data_classes: ['Emails'],
        is_sensitive: false,
      },
    ]),
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
  it('retourne "En attente" pour pending', () =>
    expect(make().statusLabel('pending')).toBe('En attente'));
  it('retourne "Analyse en cours" pour processing', () =>
    expect(make().statusLabel('processing')).toBe('Analyse en cours'));
  it('retourne "Terminé" pour completed', () =>
    expect(make().statusLabel('completed')).toBe('Terminé'));
  it('retourne "Erreur" pour failed', () => expect(make().statusLabel('failed')).toBe('Erreur'));
  it('retourne la valeur brute pour un statut inconnu', () =>
    expect(make().statusLabel('unknown')).toBe('unknown'));
});

// ── formatDate ────────────────────────────────────────────────────────────────

describe('DarkwebDossierDetailComponent — formatDate()', () => {
  it('retourne "—" pour null', () => expect(make().formatDate(null)).toBe('—'));
  it("retourne une date formatée contenant l'année", () => {
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

// ── severityColor ─────────────────────────────────────────────────────────────

describe('DarkwebDossierDetailComponent — severityColor()', () => {
  it('gray pour null', () => expect(make().severityColor(null)).toContain('gray'));
  it('red pour score >= 60', () => expect(make().severityColor(60)).toContain('red'));
  it('red pour score = 100', () => expect(make().severityColor(100)).toContain('red'));
  it('orange pour score entre 30 et 59', () =>
    expect(make().severityColor(30)).toContain('orange'));
  it('orange pour score = 59', () => expect(make().severityColor(59)).toContain('orange'));
  it('yellow pour score < 30', () => expect(make().severityColor(29)).toContain('yellow'));
  it('yellow pour score = 0', () => expect(make().severityColor(0)).toContain('yellow'));
});

// ── severityLabel ─────────────────────────────────────────────────────────────

describe('DarkwebDossierDetailComponent — severityLabel()', () => {
  it('retourne "Non calculé" pour null', () =>
    expect(make().severityLabel(null)).toBe('Non calculé'));
  it('retourne "Données critiques exposées" pour >= 60', () =>
    expect(make().severityLabel(60)).toBe('Données critiques exposées'));
  it('retourne "Données critiques exposées" pour 100', () =>
    expect(make().severityLabel(100)).toBe('Données critiques exposées'));
  it('retourne "Données sensibles exposées" pour 30', () =>
    expect(make().severityLabel(30)).toBe('Données sensibles exposées'));
  it('retourne "Données sensibles exposées" pour 59', () =>
    expect(make().severityLabel(59)).toBe('Données sensibles exposées'));
  it('retourne "Données peu sensibles" pour 0', () =>
    expect(make().severityLabel(0)).toBe('Données peu sensibles'));
  it('retourne "Données peu sensibles" pour 29', () =>
    expect(make().severityLabel(29)).toBe('Données peu sensibles'));
});

// ── riskBorderColor ───────────────────────────────────────────────────────────

describe('DarkwebDossierDetailComponent — riskBorderColor()', () => {
  it('gris pour null', () => expect(make().riskBorderColor(null)).toContain('gray'));
  it('rouge pour score >= 50', () => expect(make().riskBorderColor(50)).toContain('red'));
  it('rouge pour score = 100', () => expect(make().riskBorderColor(100)).toContain('red'));
  it('jaune pour score entre 20 et 49', () =>
    expect(make().riskBorderColor(20)).toContain('yellow'));
  it('vert pour score < 20', () => expect(make().riskBorderColor(10)).toContain('green'));
  it('vert pour score = 0', () => expect(make().riskBorderColor(0)).toContain('green'));
});

// ── getBreachTimeline ─────────────────────────────────────────────────────────

describe('DarkwebDossierDetailComponent — getBreachTimeline()', () => {
  it('retourne [] si dossier est null', () => {
    expect(make().getBreachTimeline()).toEqual([]);
  });

  it('retourne [] si aucun target', () => {
    const comp = make();
    (comp as any).dossier.set(dossier({ targets: [] }));
    expect(comp.getBreachTimeline()).toEqual([]);
  });

  it('retourne le timeline pour des targets avec fuites', () => {
    const comp = make();
    const sources = JSON.stringify([
      { name: 'LinkedIn', breach_date: '2021-06-22' },
      { name: 'Adobe', breach_date: '2019-10-04' },
    ]);
    const targets = [target({ breach_sources_json: sources, total_breaches: 2 })];
    (comp as any).dossier.set(dossier({ targets }));
    const timeline = comp.getBreachTimeline();
    expect(timeline.length).toBeGreaterThan(0);
    expect(timeline.some(t => t.year === 2021)).toBe(true);
    expect(timeline.some(t => t.year === 2019)).toBe(true);
  });

  it('est trié par année croissante', () => {
    const comp = make();
    const sources = JSON.stringify([
      { name: 'B', breach_date: '2023-01-01' },
      { name: 'A', breach_date: '2018-05-05' },
    ]);
    const targets = [target({ breach_sources_json: sources, total_breaches: 2 })];
    (comp as any).dossier.set(dossier({ targets }));
    const timeline = comp.getBreachTimeline();
    for (let i = 1; i < timeline.length; i++) {
      expect(timeline[i].year).toBeGreaterThan(timeline[i - 1].year);
    }
  });
});

// ── getBreachTimelineMax ──────────────────────────────────────────────────────

describe('DarkwebDossierDetailComponent — getBreachTimelineMax()', () => {
  it('retourne 1 pour une liste vide (évite division par zéro)', () => {
    expect(make().getBreachTimelineMax([])).toBe(1);
  });

  it('retourne le count max parmi les entrées', () => {
    const timeline = [
      { year: 2019, count: 2 },
      { year: 2021, count: 7 },
      { year: 2022, count: 4 },
    ];
    expect(make().getBreachTimelineMax(timeline)).toBe(7);
  });

  it('fonctionne avec une seule entrée', () => {
    expect(make().getBreachTimelineMax([{ year: 2020, count: 3 }])).toBe(3);
  });

  it('retourne 1 si tous les counts sont 0', () => {
    const timeline = [{ year: 2021, count: 0 }];
    expect(make().getBreachTimelineMax(timeline)).toBe(1);
  });
});

// ── unverifiedTargets ─────────────────────────────────────────────────────────

describe('DarkwebDossierDetailComponent — unverifiedTargets()', () => {
  it('retourne uniquement les targets en erreur', () => {
    const comp = make();
    const targets = [
      target({ status: 'exposed' }),
      target({
        id: 2,
        email: 'b@acme.fr',
        status: 'error',
        check_status: 'rate_limited',
        total_breaches: 0,
        breach_sources_json: null,
      }),
      target({
        id: 3,
        email: 'c@acme.fr',
        status: 'error',
        check_status: 'api_error',
        total_breaches: 0,
        breach_sources_json: null,
      }),
      target({
        id: 4,
        email: 'd@acme.fr',
        status: 'clean',
        check_status: 'verified_clean',
        total_breaches: 0,
        breach_sources_json: null,
      }),
    ];
    (comp as any).dossier.set(dossier({ targets }));
    const result = comp.unverifiedTargets();
    expect(result).toHaveLength(2);
    expect(result.every(t => t.status === 'error')).toBe(true);
  });

  it('retourne [] si dossier est null', () => {
    expect(make().unverifiedTargets()).toEqual([]);
  });

  it('retourne [] si aucune cible en erreur', () => {
    const comp = make();
    (comp as any).dossier.set(
      dossier({
        targets: [
          target(),
          target({
            id: 2,
            email: 'b@acme.fr',
            status: 'clean',
            check_status: 'verified_clean',
            total_breaches: 0,
            breach_sources_json: null,
          }),
        ],
      })
    );
    expect(comp.unverifiedTargets()).toEqual([]);
  });
});

// ── progressPercent ───────────────────────────────────────────────────────────

describe('DarkwebDossierDetailComponent — progressPercent()', () => {
  it('retourne 0 si dossier est null', () => {
    expect(make().progressPercent()).toBe(0);
  });

  it('retourne 0 si total_emails = 0', () => {
    const comp = make();
    (comp as any).dossier.set(dossier({ total_emails: 0, checked_count: 0 }));
    expect(comp.progressPercent()).toBe(0);
  });

  it('retourne 50 pour 5/10 vérifiés', () => {
    const comp = make();
    (comp as any).dossier.set(dossier({ total_emails: 10, checked_count: 5 }));
    expect(comp.progressPercent()).toBe(50);
  });

  it('retourne 100 quand tout est vérifié', () => {
    const comp = make();
    (comp as any).dossier.set(dossier({ total_emails: 8, checked_count: 8 }));
    expect(comp.progressPercent()).toBe(100);
  });

  it('arrondit correctement', () => {
    const comp = make();
    (comp as any).dossier.set(dossier({ total_emails: 3, checked_count: 1 }));
    expect(comp.progressPercent()).toBe(33);
  });
});

// ── checkStatusLabel ──────────────────────────────────────────────────────────

describe('DarkwebDossierDetailComponent — checkStatusLabel()', () => {
  it('retourne "Vérifié sain" pour verified_clean', () =>
    expect(make().checkStatusLabel('verified_clean')).toBe('Vérifié sain'));
  it('retourne "Exposé" pour exposed', () =>
    expect(make().checkStatusLabel('exposed')).toBe('Exposé'));
  it('retourne "Rate limit" pour rate_limited', () =>
    expect(make().checkStatusLabel('rate_limited')).toBe('Rate limit'));
  it('retourne "Erreur API" pour api_error', () =>
    expect(make().checkStatusLabel('api_error')).toBe('Erreur API'));
  it('retourne "En attente" pour pending', () =>
    expect(make().checkStatusLabel('pending')).toBe('En attente'));
  it('retourne "En attente" pour valeur inconnue', () =>
    expect(make().checkStatusLabel('other')).toBe('En attente'));
});

// ── checkStatusClass ──────────────────────────────────────────────────────────

describe('DarkwebDossierDetailComponent — checkStatusClass()', () => {
  it('contient green pour verified_clean', () =>
    expect(make().checkStatusClass('verified_clean')).toContain('green'));
  it('contient red pour exposed', () =>
    expect(make().checkStatusClass('exposed')).toContain('red'));
  it('contient orange pour rate_limited', () =>
    expect(make().checkStatusClass('rate_limited')).toContain('orange'));
  it('contient yellow pour api_error', () =>
    expect(make().checkStatusClass('api_error')).toContain('yellow'));
  it('contient gray pour pending', () =>
    expect(make().checkStatusClass('pending')).toContain('gray'));
});

// ── rescan ────────────────────────────────────────────────────────────────────

describe('DarkwebDossierDetailComponent — rescan()', () => {
  function makeRescan() {
    const comp = make();
    (comp as any).rescanning = signal(false);
    (comp as any).pollInterval = 1; // évite de créer un vrai setInterval dans startPolling
    (comp as any).snack = { open: vi.fn() };
    return comp;
  }

  it('ne fait rien si dossier est null', () => {
    const comp = makeRescan();
    (comp as any).service.rescan = vi.fn();
    comp.rescan();
    expect((comp as any).service.rescan).not.toHaveBeenCalled();
    expect((comp as any).rescanning()).toBe(false);
  });

  it('ne relance pas si un rescan est déjà en cours', () => {
    const comp = makeRescan();
    (comp as any).dossier.set(dossier({ id: 5 }));
    (comp as any).rescanning.set(true);
    (comp as any).service.rescan = vi.fn();
    comp.rescan();
    expect((comp as any).service.rescan).not.toHaveBeenCalled();
  });

  it('cas nominal : appelle le service, met à jour le dossier et affiche un snack', () => {
    const comp = makeRescan();
    (comp as any).dossier.set(dossier({ id: 5, status: 'completed' }));
    const updated = dossier({ id: 5, status: 'processing' });
    (comp as any).service.rescan = vi.fn().mockReturnValue(of(updated));
    comp.rescan();
    expect((comp as any).service.rescan).toHaveBeenCalledWith(5);
    expect(comp.dossier()?.status).toBe('processing');
    expect((comp as any).rescanning()).toBe(true);
    expect((comp as any).snack.open).toHaveBeenCalled();
  });

  it('cas erreur : réinitialise rescanning et affiche le détail de l’erreur', () => {
    const comp = makeRescan();
    (comp as any).dossier.set(dossier({ id: 5 }));
    (comp as any).service.rescan = vi
      .fn()
      .mockReturnValue(throwError(() => ({ error: { detail: 'Trop de rescans' } })));
    comp.rescan();
    expect((comp as any).rescanning()).toBe(false);
    expect((comp as any).snack.open).toHaveBeenCalledWith(
      'Trop de rescans',
      'Fermer',
      expect.anything()
    );
  });

  it('cas erreur sans détail : affiche un message générique', () => {
    const comp = makeRescan();
    (comp as any).dossier.set(dossier({ id: 5 }));
    (comp as any).service.rescan = vi.fn().mockReturnValue(throwError(() => ({})));
    comp.rescan();
    expect((comp as any).rescanning()).toBe(false);
    expect((comp as any).snack.open).toHaveBeenCalledWith(
      'Erreur lors du rescan',
      'Fermer',
      expect.anything()
    );
  });
});

// ── toggleMonitor ─────────────────────────────────────────────────────────────

describe('DarkwebDossierDetailComponent — toggleMonitor()', () => {
  function makeToggle() {
    const comp = make();
    (comp as any).togglingMonitor = signal(false);
    (comp as any).snack = { open: vi.fn() };
    return comp;
  }

  it('ne fait rien si dossier est null', () => {
    const comp = makeToggle();
    (comp as any).service.toggleMonitor = vi.fn();
    comp.toggleMonitor();
    expect((comp as any).service.toggleMonitor).not.toHaveBeenCalled();
  });

  it('ne fait rien si un toggle est déjà en cours', () => {
    const comp = makeToggle();
    (comp as any).dossier.set(dossier({ id: 3 }));
    (comp as any).togglingMonitor.set(true);
    (comp as any).service.toggleMonitor = vi.fn();
    comp.toggleMonitor();
    expect((comp as any).service.toggleMonitor).not.toHaveBeenCalled();
  });

  it('cas nominal (activation) : met à jour le dossier et affiche un snack', () => {
    const comp = makeToggle();
    (comp as any).dossier.set(dossier({ id: 3, monitor_active: false }));
    (comp as any).service.toggleMonitor = vi
      .fn()
      .mockReturnValue(of({ monitor_active: true, next_monitor_at: '2024-02-01T00:00:00Z' }));
    comp.toggleMonitor();
    expect((comp as any).service.toggleMonitor).toHaveBeenCalledWith(3);
    expect(comp.dossier()?.monitor_active).toBe(true);
    expect(comp.dossier()?.next_monitor_at).toBe('2024-02-01T00:00:00Z');
    expect((comp as any).togglingMonitor()).toBe(false);
    expect((comp as any).snack.open).toHaveBeenCalled();
  });

  it('cas nominal (désactivation) : monitor_active repasse à false', () => {
    const comp = makeToggle();
    (comp as any).dossier.set(dossier({ id: 3, monitor_active: true }));
    (comp as any).service.toggleMonitor = vi
      .fn()
      .mockReturnValue(of({ monitor_active: false, next_monitor_at: null }));
    comp.toggleMonitor();
    expect(comp.dossier()?.monitor_active).toBe(false);
    expect(comp.dossier()?.next_monitor_at).toBeNull();
  });

  it('cas erreur : réinitialise togglingMonitor et affiche un snack', () => {
    const comp = makeToggle();
    (comp as any).dossier.set(dossier({ id: 3 }));
    (comp as any).service.toggleMonitor = vi.fn().mockReturnValue(throwError(() => ({})));
    comp.toggleMonitor();
    expect((comp as any).togglingMonitor()).toBe(false);
    expect((comp as any).snack.open).toHaveBeenCalledWith(
      'Erreur lors du changement de monitoring',
      'Fermer',
      expect.anything()
    );
  });
});
