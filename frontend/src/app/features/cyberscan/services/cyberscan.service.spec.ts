import { describe, it, expect, beforeEach, vi } from 'vitest';
import { of } from 'rxjs';
import { CyberscanService } from './cyberscan.service';

const API = '/api/v1';

/**
 * CyberscanService uses Angular's inject() field initializer.
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
  const service = Object.create(CyberscanService.prototype) as CyberscanService;
  (service as any).http = http;
  // Reset in-memory caches so each test starts fresh
  (service as any)._plans$ = null;
  (service as any)._subscription$ = null;
  return { service, http };
}

describe('CyberscanService', () => {
  let service: CyberscanService;
  let http: any;

  beforeEach(() => {
    ({ service, http } = makeService());
  });

  // ── Plans ──────────────────────────────────────────────────────────────────

  it('getPlans() envoie GET /api/v1/plans', () => {
    http.get.mockReturnValue(of([]));
    service.getPlans().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/plans`);
  });

  it('getPlans() retourne les données du serveur', () => {
    const plans = [{ id: 1, name: 'starter' }];
    http.get.mockReturnValue(of(plans));
    let result: any;
    service.getPlans().subscribe(r => (result = r));
    expect(result).toEqual(plans);
  });

  it('getPlans() émet exactement un appel HTTP', () => {
    http.get.mockReturnValue(of([]));
    service.getPlans().subscribe();
    expect(http.get).toHaveBeenCalledTimes(1);
  });

  // ── Subscriptions ──────────────────────────────────────────────────────────

  it('getMySubscription() envoie GET /api/v1/subscriptions/me', () => {
    service.getMySubscription().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/subscriptions/me`);
  });

  it('createCheckout() envoie POST /api/v1/subscriptions/checkout/:id', () => {
    http.post.mockReturnValue(of({ checkout_url: 'https://stripe.com' }));
    service.createCheckout(3).subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/subscriptions/checkout/3`, {});
  });

  it('createCheckout() retourne l\'url de checkout', () => {
    http.post.mockReturnValue(of({ checkout_url: 'https://stripe.com/x' }));
    let result: any;
    service.createCheckout(5).subscribe(r => (result = r));
    expect(result.checkout_url).toBe('https://stripe.com/x');
  });

  it('getBillingPortal() envoie GET /api/v1/subscriptions/portal', () => {
    http.get.mockReturnValue(of({ checkout_url: '/dashboard' }));
    service.getBillingPortal().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/subscriptions/portal`);
  });

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

  // ── Scans ──────────────────────────────────────────────────────────────────

  it('triggerScan() envoie POST /api/v1/scans/trigger/:id', () => {
    http.post.mockReturnValue(of({ scan_id: 1, message: 'ok' }));
    service.triggerScan(5).subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/scans/trigger/5`, {});
  });

  it('getSiteScans() construit l\'URL avec la pagination', () => {
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

  it('downloadPdf() retourne l\'URL sans appel HTTP', () => {
    expect(service.downloadPdf(3)).toBe(`${API}/scans/3/pdf`);
    expect(http.get).not.toHaveBeenCalled();
  });

  it('downloadRemediation() retourne l\'URL correcte', () => {
    expect(service.downloadRemediation(3, 'nginx')).toBe(`${API}/scans/3/remediation/nginx`);
  });

  it('exportCsv() retourne l\'URL correcte', () => {
    expect(service.exportCsv(8)).toBe(`${API}/scans/site/8/export`);
  });

  // ── URL Scans ──────────────────────────────────────────────────────────────

  it('triggerUrlScan() envoie POST /api/v1/url-scans avec l\'url', () => {
    http.post.mockReturnValue(of({}));
    service.triggerUrlScan('https://evil.com').subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/url-scans`, { url: 'https://evil.com' });
  });

  it('getUrlScans() construit l\'URL avec la pagination', () => {
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

  it('getCodeScans() construit l\'URL avec la pagination', () => {
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

  // ── Notifications ──────────────────────────────────────────────────────────

  it('getNotifications() envoie GET /api/v1/notifications', () => {
    http.get.mockReturnValue(of({ items: [], unread_count: 0 }));
    service.getNotifications().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/notifications`);
  });

  it('getNotifications() retourne unread_count correct', () => {
    http.get.mockReturnValue(of({ items: [{}], unread_count: 5 }));
    let result: any;
    service.getNotifications().subscribe(r => (result = r));
    expect(result.unread_count).toBe(5);
  });

  it('markNotificationRead() envoie POST /api/v1/notifications/:id/read', () => {
    http.post.mockReturnValue(of({}));
    service.markNotificationRead(10).subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/notifications/10/read`, {});
  });

  it('markAllNotificationsRead() envoie POST /api/v1/notifications/read-all', () => {
    http.post.mockReturnValue(of(null));
    service.markAllNotificationsRead().subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/notifications/read-all`, {});
  });

  it('deleteNotification() envoie DELETE /api/v1/notifications/:id', () => {
    service.deleteNotification(3).subscribe();
    expect(http.delete).toHaveBeenCalledWith(`${API}/notifications/3`);
  });

  // ── NIS2 ──────────────────────────────────────────────────────────────────

  it('getNis2Assessment() envoie GET /api/v1/nis2/me', () => {
    http.get.mockReturnValue(of({ score: 0, items: {}, categories: [] }));
    service.getNis2Assessment().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/nis2/me`);
  });

  it('getNis2Assessment() retourne les données du serveur', () => {
    const data = { score: 75, items: { rssi: 'compliant' }, categories: [] };
    http.get.mockReturnValue(of(data));
    let result: any;
    service.getNis2Assessment().subscribe(r => (result = r));
    expect(result.score).toBe(75);
    expect(result.items.rssi).toBe('compliant');
  });

  it('saveNis2Assessment() envoie PUT /api/v1/nis2/me avec { items }', () => {
    const items = { rssi: 'compliant', policy: 'partial' };
    http.put.mockReturnValue(of({ score: 75, items }));
    service.saveNis2Assessment(items).subscribe();
    expect(http.put).toHaveBeenCalledWith(`${API}/nis2/me`, { items });
  });

  it('saveNis2Assessment() retourne la réponse avec le score', () => {
    const items = { rssi: 'compliant' };
    http.put.mockReturnValue(of({ score: 100, items }));
    let result: any;
    service.saveNis2Assessment(items).subscribe(r => (result = r));
    expect(result.score).toBe(100);
  });

  it('saveNis2Assessment() envoie exactement un PUT', () => {
    http.put.mockReturnValue(of({}));
    service.saveNis2Assessment({}).subscribe();
    expect(http.put).toHaveBeenCalledTimes(1);
  });

  it('downloadNis2PdfBlob() envoie GET /api/v1/nis2/me/pdf avec responseType blob', () => {
    const blob = new Blob(['PDF'], { type: 'application/pdf' });
    http.get.mockReturnValue(of(blob));
    service.downloadNis2PdfBlob().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/nis2/me/pdf`, { responseType: 'blob' });
  });

  it('downloadNis2PdfBlob() retourne un Blob', () => {
    const blob = new Blob(['PDF'], { type: 'application/pdf' });
    http.get.mockReturnValue(of(blob));
    let result: any;
    service.downloadNis2PdfBlob().subscribe(r => (result = r));
    expect(result).toBe(blob);
  });

  // ── Blob downloads ────────────────────────────────────────────────────────

  it('downloadPdfBlob() envoie GET /api/v1/scans/:id/pdf avec responseType blob', () => {
    const blob = new Blob(['PDF']);
    http.get.mockReturnValue(of(blob));
    service.downloadPdfBlob(5).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/scans/5/pdf`, { responseType: 'blob' });
  });

  it('downloadUrlScanPdfBlob() envoie GET /api/v1/url-scans/:id/pdf avec responseType blob', () => {
    const blob = new Blob(['PDF']);
    http.get.mockReturnValue(of(blob));
    service.downloadUrlScanPdfBlob(12).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/url-scans/12/pdf`, { responseType: 'blob' });
  });

  // ── Cache — Plans ──────────────────────────────────────────────────────────

  it('getPlans() ne fait qu\'un seul appel HTTP pour deux souscriptions', () => {
    http.get.mockReturnValue(of([]));
    service.getPlans().subscribe();
    service.getPlans().subscribe();
    expect(http.get).toHaveBeenCalledTimes(1);
  });

  it('getPlans() émet la même valeur aux deux abonnés', () => {
    const plans = [{ id: 1, name: 'starter' }];
    http.get.mockReturnValue(of(plans));
    const results: any[] = [];
    service.getPlans().subscribe(r => results.push(r));
    service.getPlans().subscribe(r => results.push(r));
    expect(results).toHaveLength(2);
    expect(results[0]).toEqual(results[1]);
  });

  // ── Cache — Subscription ──────────────────────────────────────────────────

  it('getMySubscription() ne fait qu\'un seul appel HTTP pour deux souscriptions', () => {
    http.get.mockReturnValue(of(null));
    service.getMySubscription().subscribe();
    service.getMySubscription().subscribe();
    expect(http.get).toHaveBeenCalledTimes(1);
  });

  it('getMySubscription(refresh=true) force un nouvel appel HTTP', () => {
    http.get.mockReturnValue(of(null));
    service.getMySubscription().subscribe();
    service.getMySubscription(true).subscribe();
    expect(http.get).toHaveBeenCalledTimes(2);
  });

  it('invalidateSubscriptionCache() force un nouvel appel au prochain getMySubscription()', () => {
    http.get.mockReturnValue(of(null));
    service.getMySubscription().subscribe(); // premier appel → HTTP
    service.invalidateSubscriptionCache();
    service.getMySubscription().subscribe(); // après invalidation → nouvel HTTP
    expect(http.get).toHaveBeenCalledTimes(2);
  });

  it('invalidateSubscriptionCache() n\'effectue pas d\'appel HTTP en lui-même', () => {
    service.invalidateSubscriptionCache();
    expect(http.get).not.toHaveBeenCalled();
    expect(http.post).not.toHaveBeenCalled();
  });
});
