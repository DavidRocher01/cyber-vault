import { describe, it, expect, beforeEach, vi } from 'vitest';
import { of, throwError } from 'rxjs';
import { AuthService } from './auth.service';

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: any;
  let routerMock: any;

  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    httpMock = { post: vi.fn(), get: vi.fn() };
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
    expect(routerMock.navigate).toHaveBeenCalledWith(['/']);
  });

  it('logout() redirige vers /cyberscan même sans token en mémoire', () => {
    httpMock.post.mockReturnValue(of({}));
    service.logout();
    expect(routerMock.navigate).toHaveBeenCalledWith(['/']);
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

  // --- login() : branches non couvertes ---

  it('login() envoie totp_code dans le body quand fourni', () => {
    httpMock.post.mockReturnValue(of({ access_token: 'a', token_type: 'bearer' }));
    service.login('user@test.com', 'pass', '123456').subscribe();
    expect(httpMock.post).toHaveBeenCalledWith(
      expect.stringContaining('/auth/login'),
      { email: 'user@test.com', password: 'pass', totp_code: '123456' },
      { withCredentials: true }
    );
  });

  it("login() sans totpCode n'inclut pas totp_code dans le body", () => {
    httpMock.post.mockReturnValue(of({ access_token: 'a', token_type: 'bearer' }));
    service.login('user@test.com', 'pass').subscribe();
    expect(httpMock.post).toHaveBeenCalledWith(
      expect.stringContaining('/auth/login'),
      { email: 'user@test.com', password: 'pass' },
      { withCredentials: true }
    );
  });

  it('login() stocke le crypto_salt quand présent', () => {
    httpMock.post.mockReturnValue(
      of({ access_token: 'acc', token_type: 'bearer', crypto_salt: 'salt42' })
    );
    service.login('user@test.com', 'pass').subscribe();
    expect(service.getCryptoSalt()).toBe('salt42');
  });

  it('login() ne stocke pas de crypto_salt quand null', () => {
    httpMock.post.mockReturnValue(
      of({ access_token: 'acc', token_type: 'bearer', crypto_salt: null })
    );
    service.login('user@test.com', 'pass').subscribe();
    expect(service.getCryptoSalt()).toBeNull();
  });

  it('login() 2FA requis : ne stocke ni token ni email', () => {
    httpMock.post.mockReturnValue(of({ requires_2fa: true }));
    service.login('user@test.com', 'pass').subscribe();
    expect(service.getToken()).toBeNull();
    expect(service.getCurrentEmail()).toBeNull();
    expect(service.isAuthenticated()).toBe(false);
  });

  it("login() propage l'erreur serveur sans rien stocker", () => {
    httpMock.post.mockReturnValue(throwError(() => new Error('401')));
    let errored = false;
    service.login('user@test.com', 'bad').subscribe({ error: () => (errored = true) });
    expect(errored).toBe(true);
    expect(service.getToken()).toBeNull();
    expect(service.getCurrentEmail()).toBeNull();
  });

  // --- register() ---

  it('register() poste email + password sur /auth/register', () => {
    httpMock.post.mockReturnValue(of({ id: 1 }));
    let result: any;
    service.register('new@test.com', 'pw').subscribe(r => (result = r));
    expect(httpMock.post).toHaveBeenCalledWith(expect.stringContaining('/auth/register'), {
      email: 'new@test.com',
      password: 'pw',
    });
    expect(result).toEqual({ id: 1 });
  });

  it("register() propage l'erreur serveur", () => {
    httpMock.post.mockReturnValue(throwError(() => new Error('409')));
    let errored = false;
    service.register('dup@test.com', 'pw').subscribe({ error: () => (errored = true) });
    expect(errored).toBe(true);
  });

  // --- me() ---

  it('me() interroge /users/me avec withCredentials', () => {
    const user = { id: 1, email: 'a@b.com', is_active: true };
    httpMock.get.mockReturnValue(of(user));
    let result: any;
    service.me().subscribe(r => (result = r));
    expect(httpMock.get).toHaveBeenCalledWith(expect.stringContaining('/users/me'), {
      withCredentials: true,
    });
    expect(result).toEqual(user);
  });

  // --- refresh() ---

  it('refresh() stocke le nouvel access_token', () => {
    httpMock.post.mockReturnValue(of({ access_token: 'fresh', token_type: 'bearer' }));
    service.refresh().subscribe();
    expect(service.getToken()).toBe('fresh');
    expect(httpMock.post).toHaveBeenCalledWith(
      expect.stringContaining('/auth/refresh'),
      {},
      { withCredentials: true }
    );
  });

  it('refresh() stocke le crypto_salt quand présent', () => {
    httpMock.post.mockReturnValue(
      of({ access_token: 'fresh', token_type: 'bearer', crypto_salt: 'newsalt' })
    );
    service.refresh().subscribe();
    expect(service.getCryptoSalt()).toBe('newsalt');
  });

  it('refresh() ne touche pas au crypto_salt quand absent', () => {
    sessionStorage.setItem('cv_crypto_salt', 'ancien');
    httpMock.post.mockReturnValue(of({ access_token: 'fresh', token_type: 'bearer' }));
    service.refresh().subscribe();
    expect(service.getCryptoSalt()).toBe('ancien');
  });

  it("refresh() propage l'erreur sans écraser le token existant", () => {
    sessionStorage.setItem('cv_token', 'ancien');
    httpMock.post.mockReturnValue(throwError(() => new Error('401')));
    let errored = false;
    service.refresh().subscribe({ error: () => (errored = true) });
    expect(errored).toBe(true);
    expect(service.getToken()).toBe('ancien');
  });

  // --- logout() : robustesse ---

  it('logout() vide aussi le crypto_salt', () => {
    sessionStorage.setItem('cv_crypto_salt', 's');
    httpMock.post.mockReturnValue(of({}));
    service.logout();
    expect(service.getCryptoSalt()).toBeNull();
  });

  it('logout() nettoie le storage et redirige même si le POST échoue', () => {
    sessionStorage.setItem('cv_token', 'x');
    sessionStorage.setItem('cv_crypto_salt', 's');
    localStorage.setItem('cv_email', 'a@b.com');
    httpMock.post.mockReturnValue(throwError(() => new Error('500')));
    service.logout();
    expect(service.getToken()).toBeNull();
    expect(service.getCryptoSalt()).toBeNull();
    expect(service.getCurrentEmail()).toBeNull();
    expect(routerMock.navigate).toHaveBeenCalledWith(['/']);
  });

  // --- getters ---

  it('getCryptoSalt() retourne null par défaut', () => {
    expect(service.getCryptoSalt()).toBeNull();
  });

  // --- SSR : platformId serveur -> noopStorage ---

  it('utilise le noopStorage côté serveur (pas de persistance)', () => {
    const ssr = new AuthService(httpMock, routerMock, 'server');
    httpMock.post.mockReturnValue(
      of({ access_token: 'acc', token_type: 'bearer', crypto_salt: 's' })
    );
    ssr.login('a@b.com', 'pw').subscribe();
    expect(ssr.getToken()).toBeNull();
    expect(ssr.getCurrentEmail()).toBeNull();
    expect(ssr.getCryptoSalt()).toBeNull();
    expect(ssr.isAuthenticated()).toBe(false);
  });
});
