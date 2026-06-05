import { describe, it, expect, beforeEach, vi } from 'vitest';
import { of } from 'rxjs';
import { AuthService } from './auth.service';

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: any;
  let routerMock: any;

  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    httpMock = { post: vi.fn() };
    routerMock = { navigate: vi.fn() };
    service = new AuthService(httpMock, routerMock, 'browser');
  });

  it('getToken() retourne null avant connexion', () => {
    expect(service.getToken()).toBeNull();
  });

  it('isAuthenticated() retourne false sans token', () => {
    expect(service.isAuthenticated()).toBe(false);
  });

  it('login() stocke access_token et email (refresh_token dans cookie httpOnly)', () => {
    httpMock.post.mockReturnValue(of({ access_token: 'acc123', token_type: 'bearer' }));
    service.login('user@test.com', 'pass').subscribe();
    expect(service.getToken()).toBe('acc123');
    expect(service.getCurrentEmail()).toBe('user@test.com');
    expect(service.isAuthenticated()).toBe(true);
  });

  it('logout() vide le storage', () => {
    sessionStorage.setItem('cv_token', 'x');
    localStorage.setItem('cv_email', 'a@b.com');
    httpMock.post.mockReturnValue(of({}));
    service.logout();
    expect(service.getToken()).toBeNull();
    expect(service.getCurrentEmail()).toBeNull();
  });

  it('logout() redirige vers /cyberscan', () => {
    httpMock.post.mockReturnValue(of({}));
    service.logout();
    expect(routerMock.navigate).toHaveBeenCalledWith(['/cyberscan']);
  });

  it('logout() redirige vers /cyberscan même sans token en mémoire', () => {
    httpMock.post.mockReturnValue(of({}));
    service.logout();
    expect(routerMock.navigate).toHaveBeenCalledWith(['/cyberscan']);
  });

  it('logout() appelle POST /auth/logout avec withCredentials', () => {
    httpMock.post.mockReturnValue(of({}));
    service.logout();
    expect(httpMock.post).toHaveBeenCalledWith(
      expect.stringContaining('/auth/logout'),
      {},
      { withCredentials: true }
    );
  });
});
