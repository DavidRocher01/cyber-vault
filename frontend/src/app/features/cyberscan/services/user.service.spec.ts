/**
 * UserService — tests des appels HTTP.
 * Même pattern que cyberscan.service.spec.ts (Object.create + mock http).
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { of } from 'rxjs';
import { UserService } from './user.service';

const API = '/api/v1';

function makeService(httpOverrides: Partial<{ get: any; post: any; put: any; delete: any }> = {}) {
  const http = {
    get: vi.fn().mockReturnValue(of({})),
    post: vi.fn().mockReturnValue(of({})),
    put: vi.fn().mockReturnValue(of({})),
    delete: vi.fn().mockReturnValue(of(null)),
    ...httpOverrides,
  };
  const service = Object.create(UserService.prototype) as UserService;
  (service as any).http = http;
  return { service, http };
}

describe('UserService', () => {
  let service: UserService;
  let http: any;

  beforeEach(() => {
    ({ service, http } = makeService());
  });

  // ── getProfile ───────────────────────────────────────────────────────────────

  it('getProfile() envoie GET /api/v1/users/me', () => {
    service.getProfile().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/users/me`);
  });

  it('getProfile() retourne les données utilisateur', () => {
    const user = { id: 1, email: 'u@test.com', is_active: true, totp_enabled: false };
    http.get.mockReturnValue(of(user));
    let result: any;
    service.getProfile().subscribe(r => (result = r));
    expect(result).toEqual(user);
  });

  // ── updateEmail ──────────────────────────────────────────────────────────────

  it('updateEmail() envoie PUT /api/v1/users/me/email', () => {
    http.put.mockReturnValue(of({ email: 'new@test.com' }));
    service.updateEmail('new@test.com', 'password123').subscribe();
    expect(http.put).toHaveBeenCalledWith(`${API}/users/me/email`, {
      email: 'new@test.com',
      current_password: 'password123',
    });
  });

  it('updateEmail() retourne le profil mis à jour', () => {
    const updated = { id: 1, email: 'new@test.com', is_active: true, totp_enabled: false };
    http.put.mockReturnValue(of(updated));
    let result: any;
    service.updateEmail('new@test.com', 'pass').subscribe(r => (result = r));
    expect(result.email).toBe('new@test.com');
  });

  // ── updatePassword ───────────────────────────────────────────────────────────

  it('updatePassword() envoie PUT /api/v1/users/me/password', () => {
    http.put.mockReturnValue(of(undefined));
    service.updatePassword('oldPass', 'newPass').subscribe();
    expect(http.put).toHaveBeenCalledWith(`${API}/users/me/password`, {
      current_password: 'oldPass',
      new_password: 'newPass',
    });
  });

  // ── setup2FA ─────────────────────────────────────────────────────────────────

  it('setup2FA() envoie POST /api/v1/users/me/2fa/setup', () => {
    http.post.mockReturnValue(of({ qr_code_b64: 'abc', secret: 'XYZ' }));
    service.setup2FA().subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/users/me/2fa/setup`, {});
  });

  it('setup2FA() retourne qr_code_b64 et secret', () => {
    const setup = { qr_code_b64: 'base64==', secret: 'JBSWY3DPEHPK3PXP' };
    http.post.mockReturnValue(of(setup));
    let result: any;
    service.setup2FA().subscribe(r => (result = r));
    expect(result.qr_code_b64).toBe('base64==');
    expect(result.secret).toBe('JBSWY3DPEHPK3PXP');
  });

  // ── enable2FA ────────────────────────────────────────────────────────────────

  it('enable2FA() envoie POST /api/v1/users/me/2fa/enable avec le code', () => {
    http.post.mockReturnValue(of({ totp_enabled: true }));
    service.enable2FA('123456').subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/users/me/2fa/enable`, { code: '123456' });
  });

  it('enable2FA() retourne le profil avec totp_enabled', () => {
    const profile = { id: 1, email: 'u@test.com', is_active: true, totp_enabled: true };
    http.post.mockReturnValue(of(profile));
    let result: any;
    service.enable2FA('123456').subscribe(r => (result = r));
    expect(result.totp_enabled).toBe(true);
  });

  // ── disable2FA ───────────────────────────────────────────────────────────────

  it('disable2FA() envoie POST /api/v1/users/me/2fa/disable', () => {
    http.post.mockReturnValue(of({ totp_enabled: false }));
    service.disable2FA('mypassword', '654321').subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/users/me/2fa/disable`, {
      password: 'mypassword',
      code: '654321',
    });
  });

  it('disable2FA() retourne le profil avec totp_enabled false', () => {
    const profile = { id: 1, email: 'u@test.com', is_active: true, totp_enabled: false };
    http.post.mockReturnValue(of(profile));
    let result: any;
    service.disable2FA('pass', '000000').subscribe(r => (result = r));
    expect(result.totp_enabled).toBe(false);
  });

  // ── exportMyData ─────────────────────────────────────────────────────────────

  it('exportMyData() retourne l\'URL sans appel HTTP', () => {
    expect(service.exportMyData()).toBe(`${API}/users/me/export`);
    expect(http.get).not.toHaveBeenCalled();
  });

  // ── deleteAccount ─────────────────────────────────────────────────────────────

  it('deleteAccount() envoie DELETE /api/v1/users/me avec le mot de passe', () => {
    http.delete.mockReturnValue(of(null));
    service.deleteAccount('mypassword').subscribe();
    expect(http.delete).toHaveBeenCalledWith(`${API}/users/me`, { body: { password: 'mypassword' } });
  });

  // ── getNotificationPreferences ───────────────────────────────────────────────

  it('getNotificationPreferences() envoie GET /api/v1/users/me/notification-preferences', () => {
    service.getNotificationPreferences().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/users/me/notification-preferences`);
  });

  it('getNotificationPreferences() retourne les préférences', () => {
    const prefs = { notif_scan_done: true, notif_scan_critical: true, notif_url_scan_done: false, notif_code_scan_done: true };
    http.get.mockReturnValue(of(prefs));
    let result: any;
    service.getNotificationPreferences().subscribe(r => (result = r));
    expect(result).toEqual(prefs);
  });

  // ── updateNotificationPreferences ────────────────────────────────────────────

  it('updateNotificationPreferences() envoie PUT /api/v1/users/me/notification-preferences', () => {
    const prefs = { notif_scan_done: false, notif_scan_critical: true, notif_url_scan_done: false, notif_code_scan_done: true };
    http.put.mockReturnValue(of(prefs));
    service.updateNotificationPreferences(prefs).subscribe();
    expect(http.put).toHaveBeenCalledWith(`${API}/users/me/notification-preferences`, prefs);
  });

  it('updateNotificationPreferences() retourne les préférences mises à jour', () => {
    const prefs = { notif_scan_done: false, notif_scan_critical: false, notif_url_scan_done: true, notif_code_scan_done: true };
    http.put.mockReturnValue(of(prefs));
    let result: any;
    service.updateNotificationPreferences(prefs).subscribe(r => (result = r));
    expect(result.notif_scan_done).toBe(false);
    expect(result.notif_url_scan_done).toBe(true);
  });
});
