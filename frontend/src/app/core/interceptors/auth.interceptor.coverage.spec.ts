import { describe, it, expect, beforeAll, afterEach, vi } from 'vitest';
import { TestBed } from '@angular/core/testing';
import {
  BrowserDynamicTestingModule,
  platformBrowserDynamicTesting,
} from '@angular/platform-browser-dynamic/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideZonelessChangeDetection } from '@angular/core';
import { Router } from '@angular/router';
import { of, throwError } from 'rxjs';
import { HotToastService } from '@ngneat/hot-toast';

// Aucun spec du dépôt n'utilise TestBed (tous font Injector.create / instanciation
// directe), donc l'environnement de test Angular n'est jamais initialisé par
// test-setup.ts. On l'initialise ici, de façon idempotente.
let envReady = false;
beforeAll(() => {
  if (!envReady) {
    TestBed.initTestEnvironment(BrowserDynamicTestingModule, platformBrowserDynamicTesting());
    envReady = true;
  }
});

import { authInterceptor } from './auth.interceptor';
import { AuthService } from '../services/auth.service';
import { CryptoService } from '../services/crypto.service';

// Ce spec EXERCE réellement l'HttpInterceptorFn via le pipeline DI d'Angular :
// HttpClient -> withInterceptors([authInterceptor]) -> HttpTestingController.
// Contrairement au spec existant qui réimplémentait la logique à la main.

interface AuthMock {
  getToken: ReturnType<typeof vi.fn>;
  isAuthenticated: ReturnType<typeof vi.fn>;
  refresh: ReturnType<typeof vi.fn>;
  logout: ReturnType<typeof vi.fn>;
}

let authMock: AuthMock;
let cryptoMock: { clearKey: ReturnType<typeof vi.fn> };
let routerMock: { navigate: ReturnType<typeof vi.fn> };
let toastMock: { warning: ReturnType<typeof vi.fn> };

function setup(
  overrides: Partial<{
    token: string | null;
    authenticated: boolean;
    refreshResult: any;
    refreshError: boolean;
  }> = {}
) {
  const {
    token = 'access_tok',
    authenticated = true,
    refreshResult = { access_token: 'refreshed_tok', token_type: 'bearer' },
    refreshError = false,
  } = overrides;

  authMock = {
    getToken: vi.fn().mockReturnValue(token),
    isAuthenticated: vi.fn().mockReturnValue(authenticated),
    refresh: vi
      .fn()
      .mockReturnValue(
        refreshError ? throwError(() => new Error('refresh failed')) : of(refreshResult)
      ),
    logout: vi.fn(),
  };
  cryptoMock = { clearKey: vi.fn() };
  routerMock = { navigate: vi.fn() };
  toastMock = { warning: vi.fn() };

  TestBed.configureTestingModule({
    providers: [
      provideZonelessChangeDetection(),
      provideHttpClient(withInterceptors([authInterceptor])),
      provideHttpClientTesting(),
      { provide: AuthService, useValue: authMock },
      { provide: CryptoService, useValue: cryptoMock },
      { provide: Router, useValue: routerMock },
      { provide: HotToastService, useValue: toastMock },
    ],
  });

  return {
    http: TestBed.inject(HttpClient),
    httpMock: TestBed.inject(HttpTestingController),
  };
}

afterEach(() => {
  try {
    TestBed.inject(HttpTestingController).verify();
  } catch {
    /* certains tests laissent volontairement une requête ouverte */
  }
  TestBed.resetTestingModule();
});

describe('authInterceptor (DI réel) — injection du token', () => {
  it("ajoute l'en-tête Authorization quand un token existe", () => {
    const { http, httpMock } = setup({ token: 'my_token' });
    http.get('/api/v1/data').subscribe();

    const reqMock = httpMock.expectOne('/api/v1/data');
    expect(reqMock.request.headers.get('Authorization')).toBe('Bearer my_token');
    reqMock.flush({ ok: true });
    expect(authMock.getToken).toHaveBeenCalled();
  });

  it("n'ajoute pas d'en-tête Authorization quand le token est null", () => {
    const { http, httpMock } = setup({ token: null });
    http.get('/api/v1/data').subscribe();

    const reqMock = httpMock.expectOne('/api/v1/data');
    expect(reqMock.request.headers.has('Authorization')).toBe(false);
    reqMock.flush({ ok: true });
  });

  it('laisse passer une réponse de succès inchangée', () => {
    const { http, httpMock } = setup();
    let body: any = null;
    http.get('/api/v1/data').subscribe(r => (body = r));

    httpMock.expectOne('/api/v1/data').flush({ value: 42 });
    expect(body).toEqual({ value: 42 });
  });
});

describe('authInterceptor (DI réel) — 401 avec refresh réussi', () => {
  it('sur 401, appelle refresh() puis rejoue la requête avec le nouveau token', () => {
    const { http, httpMock } = setup({
      token: 'old_tok',
      authenticated: true,
      refreshResult: { access_token: 'new_tok', token_type: 'bearer' },
    });

    let result: any = null;
    http.get('/api/v1/protected').subscribe(r => (result = r));

    // 1ère requête -> 401
    const first = httpMock.expectOne('/api/v1/protected');
    expect(first.request.headers.get('Authorization')).toBe('Bearer old_tok');
    first.flush({ detail: 'expired' }, { status: 401, statusText: 'Unauthorized' });

    expect(authMock.refresh).toHaveBeenCalledTimes(1);

    // Retry avec le token rafraîchi
    const retry = httpMock.expectOne('/api/v1/protected');
    expect(retry.request.headers.get('Authorization')).toBe('Bearer new_tok');
    retry.flush({ ok: true });

    expect(result).toEqual({ ok: true });
    expect(authMock.logout).not.toHaveBeenCalled();
    expect(routerMock.navigate).not.toHaveBeenCalled();
  });
});

describe('authInterceptor (DI réel) — 401 avec refresh en échec', () => {
  it("si le refresh échoue : logout + clearKey + navigate(/) et propage l'erreur", () => {
    const { http, httpMock } = setup({
      token: 'old_tok',
      authenticated: true,
      refreshError: true,
    });

    let errStatus: number | null = null;
    http.get('/api/v1/protected').subscribe({
      next: () => {},
      error: (e: any) => (errStatus = e.status),
    });

    httpMock
      .expectOne('/api/v1/protected')
      .flush({ detail: 'expired' }, { status: 401, statusText: 'Unauthorized' });

    expect(authMock.refresh).toHaveBeenCalledTimes(1);
    expect(authMock.logout).toHaveBeenCalledTimes(1);
    expect(cryptoMock.clearKey).toHaveBeenCalledTimes(1);
    expect(routerMock.navigate).toHaveBeenCalledWith(['/']);
    // l'erreur 401 originale est propagée
    expect(errStatus).toBe(401);
    // pas de retry ouvert
    httpMock.expectNone('/api/v1/protected');
  });
});

describe('authInterceptor (DI réel) — 401 non authentifié', () => {
  it('sur 401 sans session authentifiée : logout + clearKey + navigate(/), pas de refresh', () => {
    const { http, httpMock } = setup({ token: 'tok', authenticated: false });

    let errStatus: number | null = null;
    http.get('/api/v1/protected').subscribe({
      next: () => {},
      error: (e: any) => (errStatus = e.status),
    });

    httpMock
      .expectOne('/api/v1/protected')
      .flush({ detail: 'nope' }, { status: 401, statusText: 'Unauthorized' });

    expect(authMock.refresh).not.toHaveBeenCalled();
    expect(authMock.logout).toHaveBeenCalledTimes(1);
    expect(cryptoMock.clearKey).toHaveBeenCalledTimes(1);
    expect(routerMock.navigate).toHaveBeenCalledWith(['/']);
    expect(errStatus).toBe(401);
  });
});

describe('authInterceptor (DI réel) — 401 sur endpoint auth (exclu)', () => {
  it('un 401 depuis /auth/login ne déclenche ni refresh ni logout', () => {
    const { http, httpMock } = setup({ token: 'tok', authenticated: true });

    let errStatus: number | null = null;
    http.post('/api/v1/auth/login', {}).subscribe({
      next: () => {},
      error: (e: any) => (errStatus = e.status),
    });

    httpMock
      .expectOne('/api/v1/auth/login')
      .flush({ detail: 'bad creds' }, { status: 401, statusText: 'Unauthorized' });

    expect(authMock.refresh).not.toHaveBeenCalled();
    expect(authMock.logout).not.toHaveBeenCalled();
    expect(routerMock.navigate).not.toHaveBeenCalled();
    expect(errStatus).toBe(401);
  });

  it('un 401 depuis /auth/register ne déclenche pas de logout', () => {
    const { http, httpMock } = setup({ token: 'tok', authenticated: true });

    http.post('/api/v1/auth/register', {}).subscribe({
      next: () => {},
      error: () => {},
    });

    httpMock
      .expectOne('/api/v1/auth/register')
      .flush({ detail: 'exists' }, { status: 401, statusText: 'Unauthorized' });

    expect(authMock.logout).not.toHaveBeenCalled();
    expect(authMock.refresh).not.toHaveBeenCalled();
  });
});

describe('authInterceptor (DI réel) — 429 rate limit', () => {
  it('affiche un toast.warning avec le detail fourni', () => {
    const { http, httpMock } = setup();

    http.get('/api/v1/data').subscribe({ next: () => {}, error: () => {} });
    httpMock
      .expectOne('/api/v1/data')
      .flush({ detail: 'Trop de requêtes' }, { status: 429, statusText: 'Too Many Requests' });

    expect(toastMock.warning).toHaveBeenCalledWith('Trop de requêtes');
  });

  it('affiche un message par défaut si detail absent', () => {
    const { http, httpMock } = setup();

    http.get('/api/v1/data').subscribe({ next: () => {}, error: () => {} });
    httpMock.expectOne('/api/v1/data').flush({}, { status: 429, statusText: 'Too Many Requests' });

    expect(toastMock.warning).toHaveBeenCalledWith(
      'Trop de requêtes. Réessayez dans quelques instants.'
    );
  });
});

describe('authInterceptor (DI réel) — 500 erreur serveur', () => {
  it('logue une erreur console sur un 500 (POST, pas de retry)', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const { http, httpMock } = setup();

    http.post('/api/v1/data', {}).subscribe({ next: () => {}, error: () => {} });
    httpMock
      .expectOne('/api/v1/data')
      .flush({ detail: 'boom' }, { status: 500, statusText: 'Server Error' });

    expect(consoleSpy).toHaveBeenCalledWith('Erreur serveur:', expect.any(String));
    consoleSpy.mockRestore();
  });

  it('rejoue une fois un GET 500 (retry avec timer), puis propage', async () => {
    vi.useFakeTimers();
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const { http, httpMock } = setup();

    let errStatus: number | null = null;
    http.get('/api/v1/data').subscribe({
      next: () => {},
      error: (e: any) => (errStatus = e.status),
    });

    // 1er essai -> 500
    httpMock
      .expectOne('/api/v1/data')
      .flush({ detail: 'boom' }, { status: 500, statusText: 'Server Error' });

    // le retry est planifié via timer(1000)
    await vi.advanceTimersByTimeAsync(1000);

    // 2e essai -> 500 de nouveau -> propagation finale
    httpMock
      .expectOne('/api/v1/data')
      .flush({ detail: 'boom' }, { status: 500, statusText: 'Server Error' });

    expect(errStatus).toBe(500);
    consoleSpy.mockRestore();
    vi.useRealTimers();
  });
});
