import { describe, it, expect, beforeEach, vi } from 'vitest';
import { AdminAuthService } from './admin-auth.service';

function make(): AdminAuthService {
  const httpMock = { get: vi.fn() };
  return new AdminAuthService(httpMock as any);
}

describe('AdminAuthService — constructor', () => {
  beforeEach(() => sessionStorage.clear());

  it('démarre non authentifié', () => {
    const svc = make();
    expect(svc.authenticated()).toBe(false);
    expect(svc.adminKey()).toBe('');
  });

  it("ne lit AUCUN storage (pas de restauration d'une clé persistée — S6)", () => {
    // Une clé laissée par une ancienne version ne doit PLUS être reprise.
    sessionStorage.setItem('admin_key', 'legacy-key');
    const svc = make();
    expect(svc.authenticated()).toBe(false);
    expect(svc.adminKey()).toBe('');
  });
});

describe('AdminAuthService — login()', () => {
  beforeEach(() => sessionStorage.clear());

  it('active authenticated et pose la clé en mémoire', () => {
    const svc = make();
    svc.login('secret-key');
    expect(svc.authenticated()).toBe(true);
    expect(svc.adminKey()).toBe('secret-key');
  });

  it('ne persiste JAMAIS la clé dans un storage (S6 — pas de secret au repos)', () => {
    const svc = make();
    svc.login('persist-me');
    expect(sessionStorage.getItem('admin_key')).toBeNull();
    expect(localStorage.getItem('admin_key')).toBeNull();
  });

  it('la clé ne survit pas à une nouvelle instance (re-saisie par session)', () => {
    make().login('ephemeral');
    // Nouvelle instance = rechargement complet simulé → état vierge.
    const fresh = make();
    expect(fresh.authenticated()).toBe(false);
    expect(fresh.adminKey()).toBe('');
  });
});

describe('AdminAuthService — logout()', () => {
  beforeEach(() => sessionStorage.clear());

  it('désactive authenticated et vide la clé', () => {
    const svc = make();
    svc.login('some-key');
    svc.logout();
    expect(svc.authenticated()).toBe(false);
    expect(svc.adminKey()).toBe('');
  });
});

describe('AdminAuthService — headers()', () => {
  beforeEach(() => sessionStorage.clear());

  it('retourne un HttpHeaders avec X-Admin-Key', () => {
    const svc = make();
    svc.login('test-key');
    const h = svc.headers();
    expect(h.get('X-Admin-Key')).toBe('test-key');
  });

  it('X-Admin-Key est vide avant login', () => {
    const svc = make();
    expect(svc.headers().get('X-Admin-Key')).toBe('');
  });
});

describe('AdminAuthService — verify()', () => {
  beforeEach(() => sessionStorage.clear());

  it('appelle GET /api/v1/admin/stats avec la clé fournie', () => {
    const httpMock = { get: vi.fn().mockReturnValue({ subscribe: vi.fn() }) };
    const svc = new AdminAuthService(httpMock as any);
    svc.verify('my-key');
    expect(httpMock.get).toHaveBeenCalledWith(
      '/api/v1/admin/stats',
      expect.objectContaining({ headers: expect.anything() })
    );
  });
});
