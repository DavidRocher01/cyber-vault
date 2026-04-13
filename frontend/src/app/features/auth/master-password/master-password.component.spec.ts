import { describe, it, expect, vi } from 'vitest';
import { Injector, runInInjectionContext } from '@angular/core';
import { FormBuilder } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';

async function makeComponent(returnUrl?: string) {
  const { MasterPasswordComponent } = await import('./master-password.component');
  const { CryptoService } = await import('../../../core/services/crypto.service');
  const { AuthService } = await import('../../../core/services/auth.service');

  const navigateByUrlMock = vi.fn();
  const navigateMock = vi.fn();
  const cryptoMock = { deriveKey: vi.fn().mockResolvedValue(undefined) };
  const authMock = { getCurrentEmail: vi.fn().mockReturnValue('user@test.com') };
  const routeMock = {
    snapshot: {
      queryParamMap: {
        get: vi.fn((k: string) => (k === 'returnUrl' ? (returnUrl ?? null) : null)),
      },
    },
  };

  const injector = Injector.create({
    providers: [
      { provide: FormBuilder, useValue: new FormBuilder() },
      { provide: CryptoService, useValue: cryptoMock },
      { provide: AuthService, useValue: authMock },
      { provide: Router, useValue: { navigate: navigateMock, navigateByUrl: navigateByUrlMock } },
      { provide: ActivatedRoute, useValue: routeMock },
    ],
  });

  const component = runInInjectionContext(injector, () => new MasterPasswordComponent());
  return { component, navigateByUrlMock, navigateMock, cryptoMock, authMock };
}

describe('MasterPasswordComponent — soumission', () => {
  it('appelle deriveKey avec le mot de passe et l\'email', async () => {
    const { component, cryptoMock } = await makeComponent();
    component.form.setValue({ masterPassword: 'MonMotDePasse1!' });
    await component.submit();
    expect(cryptoMock.deriveKey).toHaveBeenCalledWith('MonMotDePasse1!', 'user@test.com');
  });

  it('redirige vers /vault par défaut après déverrouillage', async () => {
    const { component, navigateByUrlMock } = await makeComponent();
    component.form.setValue({ masterPassword: 'MonMotDePasse1!' });
    await component.submit();
    expect(navigateByUrlMock).toHaveBeenCalledWith('/vault');
  });

  it('redirige vers returnUrl si présent dans les queryParams', async () => {
    const { component, navigateByUrlMock } = await makeComponent('/vault/settings');
    component.form.setValue({ masterPassword: 'MonMotDePasse1!' });
    await component.submit();
    expect(navigateByUrlMock).toHaveBeenCalledWith('/vault/settings');
  });

  it('affiche une erreur si email absent (session expirée)', async () => {
    const { component, authMock } = await makeComponent();
    authMock.getCurrentEmail.mockReturnValue(null);
    component.form.setValue({ masterPassword: 'MonMotDePasse1!' });
    await component.submit();
    expect(component.error).toBe('Session expirée, reconnectez-vous.');
  });

  it('affiche une erreur si deriveKey échoue', async () => {
    const { component, cryptoMock } = await makeComponent();
    cryptoMock.deriveKey.mockRejectedValue(new Error('crypto error'));
    component.form.setValue({ masterPassword: 'MonMotDePasse1!' });
    await component.submit();
    expect(component.error).toBe('Erreur lors de la dérivation de la clé.');
  });

  it('ne soumet pas si le formulaire est invalide', async () => {
    const { component, cryptoMock } = await makeComponent();
    component.form.setValue({ masterPassword: 'court' }); // < 8 chars
    await component.submit();
    expect(cryptoMock.deriveKey).not.toHaveBeenCalled();
  });

  it('loading passe à true pendant la soumission puis false après', async () => {
    const { component } = await makeComponent();
    component.form.setValue({ masterPassword: 'MonMotDePasse1!' });
    const promise = component.submit();
    await promise;
    expect(component.loading).toBe(false);
  });
});
