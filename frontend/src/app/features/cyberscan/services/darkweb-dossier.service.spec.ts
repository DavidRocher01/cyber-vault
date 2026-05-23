import { describe, it, expect, vi } from 'vitest';
import { of } from 'rxjs';
import { DarkwebDossierService } from './darkweb-dossier.service';

const API = '/api/v1/darkweb-dossier';

function makeService(httpOverrides: Partial<{ get: any; post: any; delete: any }> = {}) {
  const http = {
    get: vi.fn().mockReturnValue(of({})),
    post: vi.fn().mockReturnValue(of({})),
    delete: vi.fn().mockReturnValue(of(undefined)),
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
  it('retourne l\'URL correcte', () => {
    const { service } = makeService();
    expect(service.getPdfUrl(42)).toBe(`${API}/42/pdf`);
  });

  it('fonctionne pour l\'id 1', () => {
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
    const json = JSON.stringify([{ name: 'LinkedIn', domain: 'linkedin.com', breach_date: '2021-06-22', pwn_count: 700000000, data_classes: ['Emails'], is_sensitive: false }]);
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
    const json = JSON.stringify([{ name: 'LinkedIn', count: 4 }, { name: 'Adobe', count: 2 }]);
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
