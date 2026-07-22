import { describe, it, expect, beforeEach, vi } from 'vitest';
import { of } from 'rxjs';
import { SiteApiService } from './site-api.service';

const API = '/api/v1';

/**
 * SiteApiService uses Angular's inject() field initializer.
 * We bypass DI by creating an instance via Object.create and manually
 * assigning the http dependency — same pattern used for constructor injection.
 */
function makeService(httpOverrides: Partial<{ get: any; post: any; put: any; delete: any }> = {}) {
  const http = {
    get: vi.fn().mockReturnValue(of({})),
    post: vi.fn().mockReturnValue(of({})),
    put: vi.fn().mockReturnValue(of({})),
    delete: vi.fn().mockReturnValue(of(null)),
    ...httpOverrides,
  };
  const service = Object.create(SiteApiService.prototype) as SiteApiService;
  (service as any).http = http;
  // Reset in-memory caches so each test starts fresh
  (service as any)._plans$ = null;
  (service as any)._subscription$ = null;
  return { service, http };
}

describe('SiteApiService', () => {
  let service: SiteApiService;
  let http: any;

  beforeEach(() => {
    ({ service, http } = makeService());
  });

  // ── Plans ──────────────────────────────────────────────────────────────────

  // ── Sites ──────────────────────────────────────────────────────────────────

  it('getMySites() envoie GET /api/v1/sites', () => {
    http.get.mockReturnValue(of([]));
    service.getMySites().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/sites`);
  });

  it('createSite() envoie POST /api/v1/sites avec le body', () => {
    const data = { url: 'https://example.com', name: 'Mon site' };
    http.post.mockReturnValue(of({ id: 1, ...data }));
    service.createSite(data).subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/sites`, data);
  });

  it('createSite() retourne le site créé', () => {
    const data = { url: 'https://example.com', name: 'Mon site' };
    http.post.mockReturnValue(of({ id: 7, ...data, is_active: true, created_at: '' }));
    let result: any;
    service.createSite(data).subscribe(r => (result = r));
    expect(result.id).toBe(7);
  });

  it('deleteSite() envoie DELETE /api/v1/sites/:id', () => {
    service.deleteSite(7).subscribe();
    expect(http.delete).toHaveBeenCalledWith(`${API}/sites/7`);
  });
});

describe('CyberscanService — vérification de domaine (H2b)', () => {
  it('getSiteDomainStatus appelle GET /sites/:id/domain', () => {
    const { service, http } = makeService();
    service.getSiteDomainStatus(7).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/sites/7/domain`);
  });

  it('requestSiteDomainVerify appelle POST /sites/:id/domain/verify', () => {
    const { service, http } = makeService();
    service.requestSiteDomainVerify(7).subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/sites/7/domain/verify`, {});
  });

  it('checkSiteDomainVerify appelle POST /sites/:id/domain/verify/check', () => {
    const { service, http } = makeService();
    service.checkSiteDomainVerify(7).subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/sites/7/domain/verify/check`, {});
  });
});
