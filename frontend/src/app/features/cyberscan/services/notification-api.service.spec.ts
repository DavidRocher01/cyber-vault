import { describe, it, expect, beforeEach, vi } from 'vitest';
import { of } from 'rxjs';
import { NotificationApiService } from './notification-api.service';

const API = '/api/v1';

/**
 * NotificationApiService uses Angular's inject() field initializer.
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
  const service = Object.create(NotificationApiService.prototype) as NotificationApiService;
  (service as any).http = http;
  // Reset in-memory caches so each test starts fresh
  (service as any)._plans$ = null;
  (service as any)._subscription$ = null;
  return { service, http };
}

describe('NotificationApiService', () => {
  let service: NotificationApiService;
  let http: any;

  beforeEach(() => {
    ({ service, http } = makeService());
  });

  // ── Plans ──────────────────────────────────────────────────────────────────

  // ── Sites ──────────────────────────────────────────────────────────────────

  // ── Scans ──────────────────────────────────────────────────────────────────

  // ── URL Scans ──────────────────────────────────────────────────────────────

  // ── Code Scans ─────────────────────────────────────────────────────────────

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
});
