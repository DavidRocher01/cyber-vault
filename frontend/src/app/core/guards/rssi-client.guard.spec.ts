import { describe, it, expect, vi } from 'vitest';
import { Injector, runInInjectionContext } from '@angular/core';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { of, throwError, isObservable, Observable } from 'rxjs';
import { rssiClientGuard } from './rssi-client.guard';
import { AuthService } from '../services/auth.service';

interface RunOpts {
  isAuthenticated: boolean;
  url?: string;
  httpError?: boolean;
}

function run(opts: RunOpts) {
  const createUrlTree = vi.fn((cmds: unknown[], extras?: unknown) => ({ cmds, extras }));
  const authMock = { isAuthenticated: vi.fn().mockReturnValue(opts.isAuthenticated) };
  const get = vi.fn(() => (opts.httpError ? throwError(() => new Error('boom')) : of({})));
  const httpMock = { get };

  const injector = Injector.create({
    providers: [
      { provide: AuthService, useValue: authMock },
      { provide: Router, useValue: { createUrlTree } },
      { provide: HttpClient, useValue: httpMock },
    ],
  });

  const result = runInInjectionContext(injector, () =>
    rssiClientGuard({} as never, { url: opts.url ?? '/espace-client' } as never)
  );
  return { result, createUrlTree, get };
}

function resolve(result: unknown): Promise<unknown> {
  if (isObservable(result)) {
    return new Promise((res, rej) => {
      (result as Observable<unknown>).subscribe({ next: res, error: rej });
    });
  }
  return Promise.resolve(result);
}

describe('rssiClientGuard', () => {
  it('redirige vers /auth/login (avec returnUrl) si non authentifié, sans appeler l API', () => {
    const { result, createUrlTree, get } = run({ isAuthenticated: false, url: '/espace-client' });
    expect(isObservable(result)).toBe(false);
    expect(get).not.toHaveBeenCalled();
    expect(createUrlTree).toHaveBeenCalledWith(
      ['/auth/login'],
      expect.objectContaining({ queryParams: { returnUrl: '/espace-client' } })
    );
  });

  it('autorise (true) si /portal/me répond 200 (compte lié à un client)', async () => {
    const { result, createUrlTree, get } = run({ isAuthenticated: true });
    expect(isObservable(result)).toBe(true);
    expect(get).toHaveBeenCalledWith('/api/v1/portal/me');
    await expect(resolve(result)).resolves.toBe(true);
    expect(createUrlTree).not.toHaveBeenCalled();
  });

  it('refuse et redirige vers / si /portal/me échoue (403 → catchError)', async () => {
    const { result, createUrlTree } = run({ isAuthenticated: true, httpError: true });
    const resolved = await resolve(result);
    expect(createUrlTree).toHaveBeenCalledWith(['/']);
    expect(resolved).toEqual({ cmds: ['/'], extras: undefined });
  });
});
