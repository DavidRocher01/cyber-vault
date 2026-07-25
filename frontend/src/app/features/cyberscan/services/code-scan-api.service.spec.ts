import { describe, it, expect, beforeEach, vi } from 'vitest';
import { of } from 'rxjs';
import { CodeScanApiService } from './code-scan-api.service';

const API = '/api/v1';

/**
 * CodeScanApiService uses Angular's inject() field initializer.
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
  const service = Object.create(CodeScanApiService.prototype) as CodeScanApiService;
  (service as any).http = http;
  // Reset in-memory caches so each test starts fresh
  (service as any)._plans$ = null;
  (service as any)._subscription$ = null;
  return { service, http };
}

describe('CodeScanApiService', () => {
  let service: CodeScanApiService;
  let http: any;

  beforeEach(() => {
    ({ service, http } = makeService());
  });

  // ── Plans ──────────────────────────────────────────────────────────────────

  // ── Sites ──────────────────────────────────────────────────────────────────

  // ── Scans ──────────────────────────────────────────────────────────────────

  // ── URL Scans ──────────────────────────────────────────────────────────────

  // ── Code Scans ─────────────────────────────────────────────────────────────

  it('triggerCodeScan() envoie POST /api/v1/code-scans avec repo_url', () => {
    http.post.mockReturnValue(of({ scan_id: 1, message: 'ok' }));
    service.triggerCodeScan('https://github.com/user/repo').subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/code-scans`, {
      repo_url: 'https://github.com/user/repo',
      github_token: null,
    });
  });

  it('triggerCodeScan() inclut le token github si fourni', () => {
    http.post.mockReturnValue(of({ scan_id: 2, message: 'ok' }));
    service.triggerCodeScan('https://github.com/user/repo', 'ghp_abc123').subscribe();
    const [, body] = http.post.mock.calls[0];
    expect(body.github_token).toBe('ghp_abc123');
  });

  it('triggerCodeScan() passe null comme token si non fourni', () => {
    http.post.mockReturnValue(of({ scan_id: 3, message: 'ok' }));
    service.triggerCodeScan('https://gitlab.com/org/proj').subscribe();
    const [, body] = http.post.mock.calls[0];
    expect(body.github_token).toBeNull();
  });

  it("getCodeScans() construit l'URL avec la pagination", () => {
    http.get.mockReturnValue(of({ items: [], total: 0, page: 2, per_page: 10, pages: 1 }));
    service.getCodeScans(2, 10).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/code-scans?page=2&per_page=10`);
  });

  it('getCodeScan() envoie GET /api/v1/code-scans/:id', () => {
    service.getCodeScan(5).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/code-scans/5`);
  });

  it('deleteCodeScan() envoie DELETE /api/v1/code-scans/:id', () => {
    service.deleteCodeScan(7).subscribe();
    expect(http.delete).toHaveBeenCalledWith(`${API}/code-scans/7`);
  });

  it('uploadCodeScan() envoie POST /api/v1/code-scans/upload avec FormData', () => {
    http.post.mockReturnValue(of({ scan_id: 3, message: 'ok' }));
    const file = new File(['content'], 'app.zip', { type: 'application/zip' });
    service.uploadCodeScan(file).subscribe();
    const [url, body] = http.post.mock.calls[0];
    expect(url).toBe(`${API}/code-scans/upload`);
    expect(body).toBeInstanceOf(FormData);
  });

  it('uploadCodeScan() inclut le fichier dans FormData', () => {
    http.post.mockReturnValue(of({ scan_id: 4, message: 'ok' }));
    const file = new File(['x'], 'test.zip');
    service.uploadCodeScan(file).subscribe();
    const [, formData] = http.post.mock.calls[0];
    expect((formData as FormData).get('file')).toBe(file);
  });
});
