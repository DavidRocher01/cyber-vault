import { describe, it, expect, beforeEach, vi } from 'vitest';
import { AdminAuthService } from './admin-auth.service';

function make(storedKey?: string): AdminAuthService {
  if (storedKey) {
    sessionStorage.setItem('admin_key', storedKey);
  } else {
    sessionStorage.removeItem('admin_key');
  }
  const httpMock = { get: vi.fn() };
  return new AdminAuthService(httpMock as any);
}

describe('AdminAuthService — constructor', () => {
  beforeEach(() => sessionStorage.clear());

  it('démarre non authentifié sans clé stockée', () => {
    const svc = make();
    expect(svc.authenticated()).toBe(false);
    expect(svc.adminKey()).toBe('');
  });

  it('restaure l\'état depuis sessionStorage si une clé est présente', () => {
    const svc = make('my-saved-key');
    expect(svc.authenticated()).toBe(true);
    expect(svc.adminKey()).toBe('my-saved-key');
  });
});

describe('AdminAuthService — login()', () => {
  beforeEach(() => sessionStorage.clear());

  it('active authenticated et stocke la clé', () => {
    const svc = make();
    svc.login('secret-key');
    expect(svc.authenticated()).toBe(true);
    expect(svc.adminKey()).toBe('secret-key');
  });

  it('persiste la clé dans sessionStorage', () => {
    const svc = make();
    svc.login('persist-me');
    expect(sessionStorage.getItem('admin_key')).toBe('persist-me');
  });
});

describe('AdminAuthService — logout()', () => {
  beforeEach(() => sessionStorage.clear());

  it('désactive authenticated et vide la clé', () => {
    const svc = make('some-key');
    svc.logout();
    expect(svc.authenticated()).toBe(false);
    expect(svc.adminKey()).toBe('');
  });

  it('supprime la clé de sessionStorage', () => {
    const svc = make('some-key');
    svc.logout();
    expect(sessionStorage.getItem('admin_key')).toBeNull();
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
    sessionStorage.removeItem('admin_key');
    const svc = new AdminAuthService(httpMock as any);
    svc.verify('my-key');
    expect(httpMock.get).toHaveBeenCalledWith(
      '/api/v1/admin/stats',
      expect.objectContaining({ headers: expect.anything() }),
    );
  });
});
