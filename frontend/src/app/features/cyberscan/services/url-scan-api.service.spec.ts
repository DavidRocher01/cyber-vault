import { describe, it, expect, beforeEach, vi } from 'vitest';
import { of } from 'rxjs';
import { UrlScanApiService } from './url-scan-api.service';

const API = '/api/v1';

/**
 * UrlScanApiService uses Angular's inject() field initializer.
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
  const service = Object.create(UrlScanApiService.prototype) as UrlScanApiService;
  (service as any).http = http;
  // Reset in-memory caches so each test starts fresh
  (service as any)._plans$ = null;
  (service as any)._subscription$ = null;
  return { service, http };
}

describe('UrlScanApiService', () => {
  let service: UrlScanApiService;
  let http: any;

  beforeEach(() => {
    ({ service, http } = makeService());
  });

  // ── Plans ──────────────────────────────────────────────────────────────────

  // ── Sites ──────────────────────────────────────────────────────────────────

  // ── Scans ──────────────────────────────────────────────────────────────────

  // ── URL Scans ──────────────────────────────────────────────────────────────

  it("triggerUrlScan() envoie POST /api/v1/url-scans avec l'url", () => {
    http.post.mockReturnValue(of({}));
    service.triggerUrlScan('https://evil.com').subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/url-scans`, { url: 'https://evil.com' });
  });

  it("getUrlScans() construit l'URL avec la pagination", () => {
    http.get.mockReturnValue(of({ items: [], total: 0, page: 3, per_page: 15, pages: 1 }));
    service.getUrlScans(3, 15).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/url-scans?page=3&per_page=15`);
  });

  it('getUrlScan() envoie GET /api/v1/url-scans/:id', () => {
    service.getUrlScan(99).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/url-scans/99`);
  });

  it('deleteUrlScan() envoie DELETE /api/v1/url-scans/:id', () => {
    service.deleteUrlScan(12).subscribe();
    expect(http.delete).toHaveBeenCalledWith(`${API}/url-scans/12`);
  });

  it('downloadUrlScanPdfBlob() envoie GET /api/v1/url-scans/:id/pdf avec responseType blob', () => {
    const blob = new Blob(['PDF']);
    http.get.mockReturnValue(of(blob));
    service.downloadUrlScanPdfBlob(12).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/url-scans/12/pdf`, { responseType: 'blob' });
  });
});
