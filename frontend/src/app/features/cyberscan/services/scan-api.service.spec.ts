import { describe, it, expect, beforeEach, vi } from 'vitest';
import { of } from 'rxjs';
import { ScanApiService } from './scan-api.service';

const API = '/api/v1';

/**
 * ScanApiService uses Angular's inject() field initializer.
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
  const service = Object.create(ScanApiService.prototype) as ScanApiService;
  (service as any).http = http;
  // Reset in-memory caches so each test starts fresh
  (service as any)._plans$ = null;
  (service as any)._subscription$ = null;
  return { service, http };
}

describe('ScanApiService', () => {
  let service: ScanApiService;
  let http: any;

  beforeEach(() => {
    ({ service, http } = makeService());
  });

  // ── Plans ──────────────────────────────────────────────────────────────────

  // ── Sites ──────────────────────────────────────────────────────────────────

  // ── Scans ──────────────────────────────────────────────────────────────────

  it('triggerScan() envoie POST /api/v1/scans/trigger/:id', () => {
    http.post.mockReturnValue(of({ scan_id: 1, message: 'ok' }));
    service.triggerScan(5).subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/scans/trigger/5`, {});
  });

  it("getSiteScans() construit l'URL avec la pagination", () => {
    http.get.mockReturnValue(of({ items: [], total: 0, page: 2, per_page: 5, pages: 1 }));
    service.getSiteScans(10, 2, 5).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/scans/site/10?page=2&per_page=5`);
  });

  it('getSiteScans() utilise page=1, per_page=10 par défaut', () => {
    http.get.mockReturnValue(of({ items: [], total: 0, page: 1, per_page: 10, pages: 1 }));
    service.getSiteScans(3).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/scans/site/3?page=1&per_page=10`);
  });

  it('getScan() envoie GET /api/v1/scans/:id', () => {
    service.getScan(42).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/scans/42`);
  });

  it("downloadPdf() retourne l'URL sans appel HTTP", () => {
    expect(service.downloadPdf(3)).toBe(`${API}/scans/3/pdf`);
    expect(http.get).not.toHaveBeenCalled();
  });

  it('downloadRemediationBlob() appelle GET avec responseType blob', () => {
    http.get.mockReturnValue(of(new Blob()));
    service.downloadRemediationBlob(3, 'nginx').subscribe();
    expect(http.get).toHaveBeenCalledWith(
      `${API}/scans/3/remediation/nginx`,
      expect.objectContaining({ responseType: 'blob' })
    );
  });

  // ── Blob downloads ────────────────────────────────────────────────────────

  it('downloadPdfBlob() envoie GET /api/v1/scans/:id/pdf avec responseType blob', () => {
    const blob = new Blob(['PDF']);
    http.get.mockReturnValue(of(blob));
    service.downloadPdfBlob(5).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/scans/5/pdf`, { responseType: 'blob' });
  });
});
