import { describe, it, expect, beforeEach, vi } from 'vitest';
import { of } from 'rxjs';
import { AuthService } from './auth.service';

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: any;
  let routerMock: any;

  beforeEach(() => {
    localStorage.clear();
    httpMock = { post: vi.fn() };
    routerMock = { navigate: vi.fn() };
    service = new AuthService(httpMock, routerMock);
  });

  it('getToken() retourne null avant connexion', () => {
    expect(service.getToken()).toBeNull();
  });

  it('isAuthenticated() retourne false sans token', () => {
    expect(service.isAuthenticated()).toBe(false);
  });

  it('login() stocke access_token, refresh_token et email', () => {
    httpMock.post.mockReturnValue(
      of({ access_token: 'acc123', refresh_token: 'ref456', token_type: 'bearer' })
    );
    service.login('user@test.com', 'pass').subscribe();
    expect(service.getToken()).toBe('acc123');
    expect(service.getRefreshToken()).toBe('ref456');
    expect(service.getCurrentEmail()).toBe('user@test.com');
    expect(service.isAuthenticated()).toBe(true);
  });

  it('logout() vide le localStorage', () => {
    localStorage.setItem('cv_token', 'x');
    localStorage.setItem('cv_refresh', 'y');
    localStorage.setItem('cv_email', 'a@b.com');
    httpMock.post.mockReturnValue(of({}));
    service.logout();
    expect(service.getToken()).toBeNull();
    expect(service.getRefreshToken()).toBeNull();
    expect(service.getCurrentEmail()).toBeNull();
  });

  it('logout() redirige vers /cyberscan', () => {
    httpMock.post.mockReturnValue(of({}));
    service.logout();
    expect(routerMock.navigate).toHaveBeenCalledWith(['/cyberscan']);
  });

  it('logout() redirige vers /cyberscan même sans refresh token', () => {
    service.logout();
    expect(routerMock.navigate).toHaveBeenCalledWith(['/cyberscan']);
  });

  it('logout() appelle POST /auth/logout si un refresh token existe', () => {
    localStorage.setItem('cv_refresh', 'ref999');
    httpMock.post.mockReturnValue(of({}));
    service.logout();
    expect(httpMock.post).toHaveBeenCalledWith(
      expect.stringContaining('/auth/logout'),
      expect.objectContaining({ refresh_token: 'ref999' })
    );
  });
});
