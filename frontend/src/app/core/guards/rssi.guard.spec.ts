import { describe, it, expect, vi } from 'vitest';
import { Injector, runInInjectionContext } from '@angular/core';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { of, throwError, isObservable, Observable } from 'rxjs';
import { rssiGuard } from './rssi.guard';
import { AuthService } from '../services/auth.service';

interface RunOpts {
  isAuthenticated: boolean;
  url?: string;
  // undefined => guard n'appelle pas http.get (cas non authentifié)
  httpResponse?: { is_rssi_consultant: boolean };
  httpError?: boolean;
}

function run(opts: RunOpts) {
  const createUrlTree = vi.fn((cmds: unknown[], extras?: unknown) => ({ cmds, extras }));
  const authMock = { isAuthenticated: vi.fn().mockReturnValue(opts.isAuthenticated) };

  const get = vi.fn(() => {
    if (opts.httpError) {
      return throwError(() => new Error('boom'));
    }
    return of(opts.httpResponse ?? { is_rssi_consultant: false });
  });
  const httpMock = { get };

  const injector = Injector.create({
    providers: [
      { provide: AuthService, useValue: authMock },
      { provide: Router, useValue: { createUrlTree } },
      { provide: HttpClient, useValue: httpMock },
    ],
  });

  const result = runInInjectionContext(injector, () =>
    rssiGuard({} as any, { url: opts.url ?? '/rssi/dashboard' } as any)
  );

  return { result, createUrlTree, get };
}

// Résout la valeur du guard qu'elle soit synchrone (UrlTree) ou Observable.
function resolve(result: unknown): Promise<unknown> {
  if (isObservable(result)) {
    return new Promise((res, rej) => {
      (result as Observable<unknown>).subscribe({ next: res, error: rej });
    });
  }
  return Promise.resolve(result);
}

describe('rssiGuard', () => {
  it('redirige vers /auth/login (avec returnUrl) si non authentifié, sans appeler l API', () => {
    const { result, createUrlTree, get } = run({ isAuthenticated: false, url: '/rssi/clients' });
    expect(isObservable(result)).toBe(false);
    expect(get).not.toHaveBeenCalled();
    expect(createUrlTree).toHaveBeenCalledWith(
      ['/auth/login'],
      expect.objectContaining({ queryParams: { returnUrl: '/rssi/clients' } })
    );
  });

  it('autorise l accès (true) si l utilisateur est un consultant rssi', async () => {
    const { result, createUrlTree, get } = run({
      isAuthenticated: true,
      httpResponse: { is_rssi_consultant: true },
    });
    expect(isObservable(result)).toBe(true);
    expect(get).toHaveBeenCalledWith('/api/v1/users/me');
    await expect(resolve(result)).resolves.toBe(true);
    expect(createUrlTree).not.toHaveBeenCalled();
  });

  it('refuse et redirige vers / si l utilisateur n est pas consultant rssi', async () => {
    const { result, createUrlTree } = run({
      isAuthenticated: true,
      httpResponse: { is_rssi_consultant: false },
    });
    const resolved = await resolve(result);
    expect(createUrlTree).toHaveBeenCalledWith(['/']);
    // le map renvoie le UrlTree produit par createUrlTree
    expect(resolved).toEqual({ cmds: ['/'], extras: undefined });
  });

  it('redirige vers / si l appel API échoue (catchError)', async () => {
    const { result, createUrlTree } = run({ isAuthenticated: true, httpError: true });
    const resolved = await resolve(result);
    expect(createUrlTree).toHaveBeenCalledWith(['/']);
    expect(resolved).toEqual({ cmds: ['/'], extras: undefined });
  });
});
