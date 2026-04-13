import { describe, it, expect, vi } from 'vitest';
import { Injector, runInInjectionContext } from '@angular/core';
import { Router } from '@angular/router';
import { cryptoGuard } from './crypto.guard';
import { CryptoService } from '../services/crypto.service';

function run(hasKey: boolean, url = '/vault') {
  const createUrlTreeMock = vi.fn((cmds: any[], extras?: any) => ({ cmds, extras }));
  const cryptoMock = { hasKey: vi.fn().mockReturnValue(hasKey) };

  const injector = Injector.create({
    providers: [
      { provide: CryptoService, useValue: cryptoMock },
      { provide: Router, useValue: { createUrlTree: createUrlTreeMock } },
    ],
  });

  const result = runInInjectionContext(injector, () =>
    cryptoGuard({} as any, { url } as any)
  );

  return { result, createUrlTreeMock };
}

describe('cryptoGuard', () => {
  it('retourne true si la clé est présente', () => {
    const { result } = run(true);
    expect(result).toBe(true);
  });

  it('redirige vers /auth/master-password si la clé est absente', () => {
    const { createUrlTreeMock } = run(false, '/vault');
    expect(createUrlTreeMock).toHaveBeenCalledWith(
      ['/auth/master-password'],
      expect.objectContaining({ queryParams: { returnUrl: '/vault' } })
    );
  });

  it('passe le returnUrl exact dans les queryParams', () => {
    const { createUrlTreeMock } = run(false, '/vault/settings');
    expect(createUrlTreeMock.mock.calls[0][1].queryParams.returnUrl).toBe('/vault/settings');
  });

  it('ne crée pas de UrlTree quand la clé est présente', () => {
    const { createUrlTreeMock } = run(true);
    expect(createUrlTreeMock).not.toHaveBeenCalled();
  });
});
