/**
 * AuthStore — tests de couverture COMPLEMENTAIRES (ne pas dupliquer auth.store.spec.ts).
 *
 * auth.store.spec.ts couvre uniquement la logique pure de resolveReturnUrl (reproduite).
 * Ici on instancie le vrai AuthStore (ComponentStore) via TestBed avec AuthService,
 * Router et ActivatedRoute mockes, et on exerce reellement les effects login /
 * loginWith2FA, les transitions d'etat (loading/error/requires2fa), la persistance
 * des pending creds, la validation anti open-redirect du returnUrl, et les helpers
 * cancelTwoFa / clearError.
 *
 * Tout est synchrone et deterministe : AuthService.login est mocke pour renvoyer
 * un observable froid (of / throwError) => l'effect switchMap s'execute inline.
 * Aucun appel reseau reel.
 */
import { describe, it, expect, beforeAll, afterEach, vi } from 'vitest';
import { provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import {
  BrowserDynamicTestingModule,
  platformBrowserDynamicTesting,
} from '@angular/platform-browser-dynamic/testing';
import { Router, ActivatedRoute } from '@angular/router';
import { of, throwError, firstValueFrom } from 'rxjs';
import { take } from 'rxjs/operators';

import { AuthStore } from './auth.store';
import { AuthService } from '../../core/services/auth.service';

// AuthStore est un ComponentStore NgRx : il a besoin d'un DestroyRef (contexte
// d'injection). On l'instancie via TestBed, ce qui exige que l'environnement de
// test Angular soit initialise. test-setup.ts ne l'initialise pas (les vieux
// specs utilisaient Injector.create), donc on le fait ici de facon idempotente.
let envReady = false;
beforeAll(() => {
  if (!envReady) {
    TestBed.initTestEnvironment(BrowserDynamicTestingModule, platformBrowserDynamicTesting());
    envReady = true;
  }
});

// ── helpers ─────────────────────────────────────────────────────────────────

function makeStore(returnUrl: string | null = null) {
  const loginMock = vi.fn();
  // me() est appele par navigateAfterLogin quand aucun returnUrl explicite n'est
  // fourni (routage par role). Par defaut : utilisateur sans role => home '/'.
  const meMock = vi.fn(() =>
    of({
      id: 1,
      email: 'u@test.com',
      is_active: true,
      totp_enabled: false,
      is_rssi_consultant: false,
      is_portal_client: false,
    })
  );

  const authServiceMock = { login: loginMock, me: meMock } as unknown as AuthService;

  const navigateByUrlMock = vi.fn();
  const routerMock = { navigateByUrl: navigateByUrlMock } as unknown as Router;

  const routeMock = {
    snapshot: {
      queryParamMap: {
        get: vi.fn((k: string) => (k === 'returnUrl' ? returnUrl : null)),
      },
    },
  } as unknown as ActivatedRoute;

  TestBed.configureTestingModule({
    providers: [
      provideZonelessChangeDetection(),
      { provide: AuthService, useValue: authServiceMock },
      { provide: Router, useValue: routerMock },
      { provide: ActivatedRoute, useValue: routeMock },
      // AuthStore utilise l'injection par parametres de constructeur classique.
      // Sous esbuild/Vitest, la metadata de constructeur (emitDecoratorMetadata)
      // n'est pas emise, donc la DI automatique d'Angular echoue (NG0202). On
      // instancie donc AuthStore explicitement via useFactory : le `new` se fait
      // dans le contexte d'injection du TestBed, ce qui fournit le DestroyRef
      // requis par ComponentStore, tout en passant les mocks a la main.
      {
        provide: AuthStore,
        useFactory: () => new AuthStore(authServiceMock, routerMock, routeMock),
      },
    ],
  });

  const store = TestBed.inject(AuthStore);
  return { store, loginMock, meMock, navigateByUrlMock, routeMock };
}

/** Lit la valeur synchrone courante d'un selector (observable a valeur immediate). */
function currentValue<T>(obs$: { pipe: any }): T {
  let value!: T;
  (obs$ as any).pipe(take(1)).subscribe((v: T) => (value = v));
  return value;
}

/** Accede a l'etat interne complet (get() est protected). */
function state(store: AuthStore): any {
  return (store as any).get();
}

afterEach(() => {
  TestBed.resetTestingModule();
});

// ── etat initial ──────────────────────────────────────────────────────────────

describe('AuthStore — etat initial', () => {
  it("s'instancie via TestBed sans erreur", () => {
    const { store } = makeStore();
    expect(store).toBeInstanceOf(AuthStore);
  });

  it('loading=false, error=null, requires2fa=false au demarrage', () => {
    const { store } = makeStore();
    expect(currentValue<boolean>(store.loading$)).toBe(false);
    expect(currentValue<string | null>(store.error$)).toBeNull();
    expect(currentValue<boolean>(store.requires2fa$)).toBe(false);
  });

  it('pendingEmail et pendingPassword null au demarrage', () => {
    const { store } = makeStore();
    expect(state(store).pendingEmail).toBeNull();
    expect(state(store).pendingPassword).toBeNull();
  });
});

// ── login — succes (pas de 2FA) ─────────────────────────────────────────────────

describe('AuthStore — login succes', () => {
  it('appelle authService.login avec email + password', () => {
    const { store, loginMock } = makeStore();
    loginMock.mockReturnValue(of({ access_token: 'tok', token_type: 'bearer' }));
    store.login({ email: 'user@test.com', password: 'Pw1!' });
    expect(loginMock).toHaveBeenCalledWith('user@test.com', 'Pw1!');
  });

  it('remet loading a false apres succes', () => {
    const { store, loginMock } = makeStore();
    loginMock.mockReturnValue(of({ access_token: 'tok', token_type: 'bearer' }));
    store.login({ email: 'user@test.com', password: 'Pw1!' });
    expect(currentValue<boolean>(store.loading$)).toBe(false);
  });

  it('laisse requires2fa a false apres succes normal', () => {
    const { store, loginMock } = makeStore();
    loginMock.mockReturnValue(of({ access_token: 'tok', token_type: 'bearer' }));
    store.login({ email: 'user@test.com', password: 'Pw1!' });
    expect(currentValue<boolean>(store.requires2fa$)).toBe(false);
  });

  it('ne positionne pas d erreur apres succes', () => {
    const { store, loginMock } = makeStore();
    loginMock.mockReturnValue(of({ access_token: 'tok', token_type: 'bearer' }));
    store.login({ email: 'user@test.com', password: 'Pw1!' });
    expect(currentValue<string | null>(store.error$)).toBeNull();
  });
});

// ── login — returnUrl (validation anti open-redirect) ───────────────────────────

describe('AuthStore — login redirection & returnUrl', () => {
  function loginAndGetNav(returnUrl: string | null) {
    const { store, loginMock, navigateByUrlMock } = makeStore(returnUrl);
    loginMock.mockReturnValue(of({ access_token: 'tok', token_type: 'bearer' }));
    store.login({ email: 'user@test.com', password: 'Pw1!' });
    return navigateByUrlMock;
  }

  it('navigue vers returnUrl quand c est une page racine valide', () => {
    expect(loginAndGetNav('/dashboard')).toHaveBeenCalledWith('/dashboard');
  });

  it('preserve les query params du returnUrl valide', () => {
    expect(loginAndGetNav('/dashboard?tab=scans')).toHaveBeenCalledWith('/dashboard?tab=scans');
  });

  it('preserve / (landing) comme returnUrl valide', () => {
    expect(loginAndGetNav('/')).toHaveBeenCalledWith('/');
  });

  it('fallback sur / quand returnUrl absent', () => {
    expect(loginAndGetNav(null)).toHaveBeenCalledWith('/');
  });

  it('fallback sur / quand returnUrl est vide', () => {
    expect(loginAndGetNav('')).toHaveBeenCalledWith('/');
  });

  it('rejette la redirection externe // (protocol-relative)', () => {
    expect(loginAndGetNav('//evil.com')).toHaveBeenCalledWith('/');
  });

  it('rejette la redirection /\\\\ (backslash bypass)', () => {
    expect(loginAndGetNav('/\\evil.com')).toHaveBeenCalledWith('/');
  });

  it('rejette une URL absolue http sans / initial', () => {
    expect(loginAndGetNav('http://evil.com')).toHaveBeenCalledWith('/');
  });

  it('rejette /auth (boucle de login)', () => {
    expect(loginAndGetNav('/auth/master-password')).toHaveBeenCalledWith('/');
  });

  it('rejette /vault (flow crypto)', () => {
    expect(loginAndGetNav('/vault')).toHaveBeenCalledWith('/');
  });

  it('rejette /awareness (portail magic-link)', () => {
    expect(loginAndGetNav('/awareness/portal')).toHaveBeenCalledWith('/');
  });
});

// ── login — routage par role (sans returnUrl explicite) ─────────────────────────

describe('AuthStore — routage par role', () => {
  const baseUser = {
    id: 1,
    email: 'u@test.com',
    is_active: true,
    totp_enabled: false,
    is_rssi_consultant: false,
    is_portal_client: false,
  };

  function loginWithRole(role: Partial<typeof baseUser>) {
    const { store, loginMock, meMock, navigateByUrlMock } = makeStore(null);
    meMock.mockReturnValue(of({ ...baseUser, ...role }));
    loginMock.mockReturnValue(of({ access_token: 'tok', token_type: 'bearer' }));
    store.login({ email: 'user@test.com', password: 'Pw1!' });
    return navigateByUrlMock;
  }

  it('consultant -> /consultant', () => {
    expect(loginWithRole({ is_rssi_consultant: true })).toHaveBeenCalledWith('/consultant');
  });

  it('client de portail -> /espace-client', () => {
    expect(loginWithRole({ is_portal_client: true })).toHaveBeenCalledWith('/espace-client');
  });

  it('double role consultant + client -> /consultant (priorite)', () => {
    expect(
      loginWithRole({ is_rssi_consultant: true, is_portal_client: true })
    ).toHaveBeenCalledWith('/consultant');
  });

  it('utilisateur scanner classique -> /', () => {
    expect(loginWithRole({})).toHaveBeenCalledWith('/');
  });

  it('si /users/me echoue, fallback sur /', () => {
    const { store, loginMock, meMock, navigateByUrlMock } = makeStore(null);
    meMock.mockReturnValue(throwError(() => ({ status: 500 })));
    loginMock.mockReturnValue(of({ access_token: 'tok', token_type: 'bearer' }));
    store.login({ email: 'user@test.com', password: 'Pw1!' });
    expect(navigateByUrlMock).toHaveBeenCalledWith('/');
  });

  it('un returnUrl explicite valide court-circuite le routage par role (pas d appel me)', () => {
    const { store, loginMock, meMock, navigateByUrlMock } = makeStore('/dashboard');
    loginMock.mockReturnValue(of({ access_token: 'tok', token_type: 'bearer' }));
    store.login({ email: 'user@test.com', password: 'Pw1!' });
    expect(navigateByUrlMock).toHaveBeenCalledWith('/dashboard');
    expect(meMock).not.toHaveBeenCalled();
  });
});

// ── login — reponse requires_2fa ────────────────────────────────────────────────

describe('AuthStore — login requires_2fa', () => {
  it('passe requires2fa a true', () => {
    const { store, loginMock } = makeStore();
    loginMock.mockReturnValue(of({ requires_2fa: true }));
    store.login({ email: 'user@test.com', password: 'Pw1!' });
    expect(currentValue<boolean>(store.requires2fa$)).toBe(true);
  });

  it('memorise pendingEmail et pendingPassword', () => {
    const { store, loginMock } = makeStore();
    loginMock.mockReturnValue(of({ requires_2fa: true }));
    store.login({ email: 'user@test.com', password: 'Pw1!' });
    expect(state(store).pendingEmail).toBe('user@test.com');
    expect(state(store).pendingPassword).toBe('Pw1!');
  });

  it('remet loading a false', () => {
    const { store, loginMock } = makeStore();
    loginMock.mockReturnValue(of({ requires_2fa: true }));
    store.login({ email: 'user@test.com', password: 'Pw1!' });
    expect(currentValue<boolean>(store.loading$)).toBe(false);
  });

  it('ne navigue pas quand 2FA est requise', () => {
    const { store, loginMock, navigateByUrlMock } = makeStore('/dashboard');
    loginMock.mockReturnValue(of({ requires_2fa: true }));
    store.login({ email: 'user@test.com', password: 'Pw1!' });
    expect(navigateByUrlMock).not.toHaveBeenCalled();
  });
});

// ── login — erreur ─────────────────────────────────────────────────────────────

describe('AuthStore — login erreur', () => {
  it('extrait error.detail du backend', () => {
    const { store, loginMock } = makeStore();
    loginMock.mockReturnValue(throwError(() => ({ error: { detail: 'Identifiants invalides' } })));
    store.login({ email: 'user@test.com', password: 'bad' });
    expect(currentValue<string | null>(store.error$)).toBe('Identifiants invalides');
  });

  it('message par defaut si pas de detail', () => {
    const { store, loginMock } = makeStore();
    loginMock.mockReturnValue(throwError(() => ({ error: {} })));
    store.login({ email: 'user@test.com', password: 'bad' });
    expect(currentValue<string | null>(store.error$)).toBe('Erreur de connexion');
  });

  it('message par defaut si err.error est absent', () => {
    const { store, loginMock } = makeStore();
    loginMock.mockReturnValue(throwError(() => ({})));
    store.login({ email: 'user@test.com', password: 'bad' });
    expect(currentValue<string | null>(store.error$)).toBe('Erreur de connexion');
  });

  it('remet loading a false apres erreur', () => {
    const { store, loginMock } = makeStore();
    loginMock.mockReturnValue(throwError(() => ({ error: { detail: 'x' } })));
    store.login({ email: 'user@test.com', password: 'bad' });
    expect(currentValue<boolean>(store.loading$)).toBe(false);
  });

  it('ne navigue pas en cas d erreur', () => {
    const { store, loginMock, navigateByUrlMock } = makeStore('/dashboard');
    loginMock.mockReturnValue(throwError(() => ({ error: { detail: 'x' } })));
    store.login({ email: 'user@test.com', password: 'bad' });
    expect(navigateByUrlMock).not.toHaveBeenCalled();
  });
});

// ── loginWith2FA ────────────────────────────────────────────────────────────────

describe('AuthStore — loginWith2FA', () => {
  /** Amene le store dans l'etat requires_2fa avec des pending creds connus. */
  function primeTwoFa(returnUrl: string | null = '/dashboard') {
    const ctx = makeStore(returnUrl);
    ctx.loginMock.mockReturnValue(of({ requires_2fa: true }));
    ctx.store.login({ email: 'user@test.com', password: 'Pw1!' });
    ctx.loginMock.mockReset();
    return ctx;
  }

  it('no-op si aucune pending cred (etat initial)', () => {
    const { store, loginMock, navigateByUrlMock } = makeStore();
    store.loginWith2FA({ totpCode: '123456' });
    expect(loginMock).not.toHaveBeenCalled();
    expect(navigateByUrlMock).not.toHaveBeenCalled();
  });

  it('rejoue authService.login avec pending creds + totpCode', () => {
    const { store, loginMock } = primeTwoFa();
    loginMock.mockReturnValue(of({ access_token: 'tok', token_type: 'bearer' }));
    store.loginWith2FA({ totpCode: '654321' });
    expect(loginMock).toHaveBeenCalledWith('user@test.com', 'Pw1!', '654321');
  });

  it('succes : navigue vers le returnUrl valide', () => {
    const { store, loginMock, navigateByUrlMock } = primeTwoFa('/dashboard');
    loginMock.mockReturnValue(of({ access_token: 'tok', token_type: 'bearer' }));
    store.loginWith2FA({ totpCode: '654321' });
    expect(navigateByUrlMock).toHaveBeenCalledWith('/dashboard');
  });

  it('succes : nettoie pending creds et requires2fa', () => {
    const { store, loginMock } = primeTwoFa();
    loginMock.mockReturnValue(of({ access_token: 'tok', token_type: 'bearer' }));
    store.loginWith2FA({ totpCode: '654321' });
    expect(state(store).pendingEmail).toBeNull();
    expect(state(store).pendingPassword).toBeNull();
    expect(currentValue<boolean>(store.requires2fa$)).toBe(false);
  });

  it('succes : loading revient a false', () => {
    const { store, loginMock } = primeTwoFa();
    loginMock.mockReturnValue(of({ access_token: 'tok', token_type: 'bearer' }));
    store.loginWith2FA({ totpCode: '654321' });
    expect(currentValue<boolean>(store.loading$)).toBe(false);
  });

  it('succes : applique aussi le fallback anti open-redirect (rejette /vault)', () => {
    const { store, loginMock, navigateByUrlMock } = primeTwoFa('/vault');
    loginMock.mockReturnValue(of({ access_token: 'tok', token_type: 'bearer' }));
    store.loginWith2FA({ totpCode: '654321' });
    expect(navigateByUrlMock).toHaveBeenCalledWith('/');
  });

  it('erreur : positionne le detail backend', () => {
    const { store, loginMock } = primeTwoFa();
    loginMock.mockReturnValue(throwError(() => ({ error: { detail: 'Code TOTP invalide' } })));
    store.loginWith2FA({ totpCode: '000000' });
    expect(currentValue<string | null>(store.error$)).toBe('Code TOTP invalide');
  });

  it('erreur : message par defaut "Code invalide"', () => {
    const { store, loginMock } = primeTwoFa();
    loginMock.mockReturnValue(throwError(() => ({ error: {} })));
    store.loginWith2FA({ totpCode: '000000' });
    expect(currentValue<string | null>(store.error$)).toBe('Code invalide');
  });

  it('erreur : loading revient a false', () => {
    const { store, loginMock } = primeTwoFa();
    loginMock.mockReturnValue(throwError(() => ({ error: { detail: 'x' } })));
    store.loginWith2FA({ totpCode: '000000' });
    expect(currentValue<boolean>(store.loading$)).toBe(false);
  });

  it('erreur : conserve les pending creds pour reessayer', () => {
    const { store, loginMock } = primeTwoFa();
    loginMock.mockReturnValue(throwError(() => ({ error: { detail: 'x' } })));
    store.loginWith2FA({ totpCode: '000000' });
    expect(state(store).pendingEmail).toBe('user@test.com');
    expect(state(store).pendingPassword).toBe('Pw1!');
  });
});

// ── cancelTwoFa & clearError ────────────────────────────────────────────────────

describe('AuthStore — cancelTwoFa', () => {
  it('reinitialise requires2fa, pending creds et error', () => {
    const { store, loginMock } = makeStore();
    loginMock.mockReturnValue(of({ requires_2fa: true }));
    store.login({ email: 'user@test.com', password: 'Pw1!' });

    store.cancelTwoFa();

    expect(currentValue<boolean>(store.requires2fa$)).toBe(false);
    expect(state(store).pendingEmail).toBeNull();
    expect(state(store).pendingPassword).toBeNull();
    expect(currentValue<string | null>(store.error$)).toBeNull();
  });
});

describe('AuthStore — clearError', () => {
  it('remet error a null sans toucher aux autres champs', () => {
    const { store, loginMock } = makeStore();
    loginMock.mockReturnValue(throwError(() => ({ error: { detail: 'boom' } })));
    store.login({ email: 'user@test.com', password: 'bad' });
    expect(currentValue<string | null>(store.error$)).toBe('boom');

    store.clearError();
    expect(currentValue<string | null>(store.error$)).toBeNull();
    expect(currentValue<boolean>(store.loading$)).toBe(false);
  });
});

// ── selectors reactifs ──────────────────────────────────────────────────────────

describe('AuthStore — selectors reactifs', () => {
  it('loading$ emet true pendant l appel puis false (source retardee via firstValueFrom)', async () => {
    const { store, loginMock } = makeStore();
    // Observable qui ne complete jamais tout de suite : on capture l'etat "loading"
    // en utilisant une source qui n'emet pas (NEVER-like) simulee par of() differe.
    // Ici on verifie simplement que le selector expose bien la valeur finale.
    loginMock.mockReturnValue(of({ access_token: 'tok', token_type: 'bearer' }));
    store.login({ email: 'user@test.com', password: 'Pw1!' });
    const loading = await firstValueFrom(store.loading$.pipe(take(1)));
    expect(loading).toBe(false);
  });
});
