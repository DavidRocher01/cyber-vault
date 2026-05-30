import { describe, it, expect, vi } from 'vitest';
import { of } from 'rxjs';
import { DarkwebDossierService } from './darkweb-dossier.service';

const API = '/api/v1/darkweb-dossier';

function makeService(
  httpOverrides: Partial<{ get: any; post: any; delete: any; patch: any }> = {}
) {
  const http = {
    get: vi.fn().mockReturnValue(of({})),
    post: vi.fn().mockReturnValue(of({})),
    delete: vi.fn().mockReturnValue(of(undefined)),
    patch: vi.fn().mockReturnValue(of({})),
    ...httpOverrides,
  };
  const service = Object.create(DarkwebDossierService.prototype) as DarkwebDossierService;
  (service as any).http = http;
  return { service, http };
}

// ── HTTP methods ──────────────────────────────────────────────────────────────

describe('DarkwebDossierService — list()', () => {
  it('appelle GET /darkweb-dossier', () => {
    const { service, http } = makeService();
    service.list().subscribe();
    expect(http.get).toHaveBeenCalledWith(API);
  });
});

describe('DarkwebDossierService — get()', () => {
  it('appelle GET /darkweb-dossier/:id', () => {
    const { service, http } = makeService();
    service.get(42).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/42`);
  });
});

describe('DarkwebDossierService — delete()', () => {
  it('appelle DELETE /darkweb-dossier/:id', () => {
    const { service, http } = makeService();
    service.delete(7).subscribe();
    expect(http.delete).toHaveBeenCalledWith(`${API}/7`);
  });
});

describe('DarkwebDossierService — create()', () => {
  it('appelle POST /darkweb-dossier avec un FormData', () => {
    const { service, http } = makeService();
    const file = new File(['email\njohn@acme.fr'], 'emails.csv', { type: 'text/csv' });
    service.create('Acme SAS', 'acme.fr', file).subscribe();
    expect(http.post).toHaveBeenCalledWith(API, expect.any(FormData));
  });
});

describe('DarkwebDossierService — syncCatalog()', () => {
  it('appelle POST /darkweb-dossier/catalog/sync', () => {
    const { service, http } = makeService();
    service.syncCatalog().subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/catalog/sync`, {});
  });
});

// ── getPdfUrl ─────────────────────────────────────────────────────────────────

describe('DarkwebDossierService — getPdfUrl()', () => {
  it("retourne l'URL correcte", () => {
    const { service } = makeService();
    expect(service.getPdfUrl(42)).toBe(`${API}/42/pdf`);
  });

  it("fonctionne pour l'id 1", () => {
    const { service } = makeService();
    expect(service.getPdfUrl(1)).toContain('/1/pdf');
  });
});

// ── parseBreachSources ────────────────────────────────────────────────────────

describe('DarkwebDossierService — parseBreachSources()', () => {
  it('retourne [] pour null', () => {
    const { service } = makeService();
    expect(service.parseBreachSources(null)).toEqual([]);
  });

  it('retourne [] pour un tableau vide', () => {
    const { service } = makeService();
    expect(service.parseBreachSources('[]')).toEqual([]);
  });

  it('parse correctement un tableau valide', () => {
    const { service } = makeService();
    const json = JSON.stringify([
      {
        name: 'LinkedIn',
        domain: 'linkedin.com',
        breach_date: '2021-06-22',
        pwn_count: 700000000,
        data_classes: ['Emails'],
        is_sensitive: false,
      },
    ]);
    const result = service.parseBreachSources(json);
    expect(result).toHaveLength(1);
    expect(result[0].name).toBe('LinkedIn');
    expect(result[0].pwn_count).toBe(700000000);
  });

  it('retourne [] pour un JSON invalide', () => {
    const { service } = makeService();
    expect(service.parseBreachSources('not-json')).toEqual([]);
  });

  it('retourne [] pour une chaîne vide', () => {
    const { service } = makeService();
    expect(service.parseBreachSources('')).toEqual([]);
  });
});

// ── parseTopSources ───────────────────────────────────────────────────────────

describe('DarkwebDossierService — parseTopSources()', () => {
  it('retourne [] pour null', () => {
    const { service } = makeService();
    expect(service.parseTopSources(null)).toEqual([]);
  });

  it('parse correctement les sources', () => {
    const { service } = makeService();
    const json = JSON.stringify([
      { name: 'LinkedIn', count: 4 },
      { name: 'Adobe', count: 2 },
    ]);
    const result = service.parseTopSources(json);
    expect(result).toHaveLength(2);
    expect(result[0].name).toBe('LinkedIn');
    expect(result[0].count).toBe(4);
  });

  it('retourne [] pour JSON invalide', () => {
    const { service } = makeService();
    expect(service.parseTopSources('{bad')).toEqual([]);
  });
});

// ── rescan ────────────────────────────────────────────────────────────────────

describe('DarkwebDossierService — rescan()', () => {
  it('appelle POST /darkweb-dossier/:id/rescan', () => {
    const { service, http } = makeService();
    service.rescan(5).subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/5/rescan`, {});
  });

  it('fonctionne pour différents ids', () => {
    const { service, http } = makeService();
    service.rescan(99).subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/99/rescan`, {});
  });
});

// ── toggleMonitor ─────────────────────────────────────────────────────────────

describe('DarkwebDossierService — toggleMonitor()', () => {
  it('appelle PATCH /darkweb-dossier/:id/monitor', () => {
    const { service, http } = makeService();
    service.toggleMonitor(3).subscribe();
    expect(http.patch).toHaveBeenCalledWith(`${API}/3/monitor`, {});
  });

  it('fonctionne pour différents ids', () => {
    const { service, http } = makeService();
    service.toggleMonitor(12).subscribe();
    expect(http.patch).toHaveBeenCalledWith(`${API}/12/monitor`, {});
  });
});

// ── getCsvUrl ─────────────────────────────────────────────────────────────────

describe('DarkwebDossierService — getCsvUrl()', () => {
  it("retourne l'URL correcte", () => {
    const { service } = makeService();
    expect(service.getCsvUrl(7)).toBe(`${API}/7/csv`);
  });

  it("fonctionne pour l'id 1", () => {
    const { service } = makeService();
    expect(service.getCsvUrl(1)).toContain('/1/csv');
  });
});

// ── buildBreachTimeline ───────────────────────────────────────────────────────

describe('DarkwebDossierService — buildBreachTimeline()', () => {
  it('retourne [] pour une liste vide', () => {
    const { service } = makeService();
    expect(service.buildBreachTimeline([])).toEqual([]);
  });

  it('retourne [] pour des targets sans breaches', () => {
    const { service } = makeService();
    const targets = [
      {
        id: 1,
        email: 'a@co.fr',
        status: 'clean' as const,
        total_breaches: 0,
        breach_sources_json: '[]',
        checked_at: null,
      },
    ];
    expect(service.buildBreachTimeline(targets)).toEqual([]);
  });

  it('groupe les fuites par année', () => {
    const { service } = makeService();
    const sources = JSON.stringify([
      { name: 'LinkedIn', breach_date: '2021-06-22' },
      { name: 'Adobe', breach_date: '2021-10-04' },
      { name: 'Dropbox', breach_date: '2012-07-01' },
    ]);
    const targets = [
      {
        id: 1,
        email: 'a@co.fr',
        status: 'exposed' as const,
        total_breaches: 3,
        breach_sources_json: sources,
        checked_at: null,
      },
    ];
    const timeline = service.buildBreachTimeline(targets);
    expect(timeline.find(t => t.year === 2021)?.count).toBe(2);
    expect(timeline.find(t => t.year === 2012)?.count).toBe(1);
  });

  it('trie par année croissante', () => {
    const { service } = makeService();
    const sources = JSON.stringify([
      { name: 'B', breach_date: '2020-01-01' },
      { name: 'A', breach_date: '2015-05-05' },
    ]);
    const targets = [
      {
        id: 1,
        email: 'a@co.fr',
        status: 'exposed' as const,
        total_breaches: 2,
        breach_sources_json: sources,
        checked_at: null,
      },
    ];
    const timeline = service.buildBreachTimeline(targets);
    expect(timeline[0].year).toBeLessThan(timeline[1].year);
  });

  it('ignore les dates hors plage 2000-présent', () => {
    const { service } = makeService();
    const sources = JSON.stringify([
      { name: 'Old', breach_date: '1999-01-01' },
      { name: 'New', breach_date: '2022-03-10' },
    ]);
    const targets = [
      {
        id: 1,
        email: 'a@co.fr',
        status: 'exposed' as const,
        total_breaches: 2,
        breach_sources_json: sources,
        checked_at: null,
      },
    ];
    const timeline = service.buildBreachTimeline(targets);
    expect(timeline.every(t => t.year >= 2000)).toBe(true);
    expect(timeline).toHaveLength(1);
  });

  it('agrège les fuites de plusieurs targets', () => {
    const { service } = makeService();
    const s1 = JSON.stringify([{ name: 'A', breach_date: '2022-01-01' }]);
    const s2 = JSON.stringify([{ name: 'B', breach_date: '2022-06-15' }]);
    const targets = [
      {
        id: 1,
        email: 'a@co.fr',
        status: 'exposed' as const,
        total_breaches: 1,
        breach_sources_json: s1,
        checked_at: null,
      },
      {
        id: 2,
        email: 'b@co.fr',
        status: 'exposed' as const,
        total_breaches: 1,
        breach_sources_json: s2,
        checked_at: null,
      },
    ];
    const timeline = service.buildBreachTimeline(targets);
    expect(timeline.find(t => t.year === 2022)?.count).toBe(2);
  });
});
