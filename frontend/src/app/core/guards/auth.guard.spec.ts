import { describe, it, expect, vi } from 'vitest';
import { Injector, runInInjectionContext } from '@angular/core';
import { Router } from '@angular/router';
import { authGuard } from './auth.guard';
import { AuthService } from '../services/auth.service';

function run(isAuthenticated: boolean, url = '/cyberscan/dashboard') {
  const createUrlTreeMock = vi.fn((cmds: any[], extras?: any) => ({ cmds, extras }));
  const authMock = { isAuthenticated: vi.fn().mockReturnValue(isAuthenticated) };

  const injector = Injector.create({
    providers: [
      { provide: AuthService, useValue: authMock },
      { provide: Router, useValue: { createUrlTree: createUrlTreeMock } },
    ],
  });

  const result = runInInjectionContext(injector, () =>
    authGuard({} as any, { url } as any)
  );

  return { result, createUrlTreeMock };
}

describe('authGuard', () => {
  it('retourne true si authentifié', () => {
    const { result } = run(true);
    expect(result).toBe(true);
  });

  it('redirige vers /auth/login si non authentifié', () => {
    const { createUrlTreeMock } = run(false, '/cyberscan/dashboard');
    expect(createUrlTreeMock).toHaveBeenCalledWith(
      ['/auth/login'],
      expect.objectContaining({ queryParams: { returnUrl: '/cyberscan/dashboard' } })
    );
  });

  it('passe le returnUrl exact dans les queryParams', () => {
    const { createUrlTreeMock } = run(false, '/cyberscan/scan/42');
    expect(createUrlTreeMock.mock.calls[0][1].queryParams.returnUrl).toBe('/cyberscan/scan/42');
  });

  it('ne crée pas de UrlTree quand authentifié', () => {
    const { createUrlTreeMock } = run(true);
    expect(createUrlTreeMock).not.toHaveBeenCalled();
  });
});
