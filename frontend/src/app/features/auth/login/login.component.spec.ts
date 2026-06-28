/**
 * LoginComponent — tests via injection de dépendances (AuthStore mocké).
 */
import { describe, it, expect, vi } from 'vitest';
import { Injector, runInInjectionContext } from '@angular/core';
import { FormBuilder } from '@angular/forms';
import { BehaviorSubject, of } from 'rxjs';
import { ActivatedRoute } from '@angular/router';
import { AuthStore } from '../auth.store';

async function makeComponent(returnUrl?: string) {
  const { LoginComponent } = await import('./login.component');

  const loginMock = vi.fn();
  const loginWith2FAMock = vi.fn();
  const cancelTwoFaMock = vi.fn();

  const storeMock = {
    login: loginMock,
    loginWith2FA: loginWith2FAMock,
    cancelTwoFa: cancelTwoFaMock,
    loading$: new BehaviorSubject(false),
    error$: new BehaviorSubject<string | null>(null),
    requires2fa$: new BehaviorSubject(false),
  };

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
      { provide: AuthStore, useValue: storeMock },
      { provide: ActivatedRoute, useValue: routeMock },
    ],
  });

  const comp = runInInjectionContext(injector, () => new LoginComponent());
  return { comp, storeMock, loginMock, loginWith2FAMock, cancelTwoFaMock };
}

describe('LoginComponent — état initial', () => {
  it('showPassword est false au départ', async () => {
    const { comp } = await makeComponent();
    expect(comp.showPassword).toBe(false);
  });

  it('totpCode est une chaîne vide au départ', async () => {
    const { comp } = await makeComponent();
    expect(comp.totpCode).toBe('');
  });

  it('otpClear est 0 au départ', async () => {
    const { comp } = await makeComponent();
    expect(comp.otpClear).toBe(0);
  });

  it('le formulaire contient les champs email et password', async () => {
    const { comp } = await makeComponent();
    expect(comp.form.contains('email')).toBe(true);
    expect(comp.form.contains('password')).toBe(true);
  });
});

describe('LoginComponent — returnUrl', () => {
  it('returnUrl retourne une chaîne vide si absent', async () => {
    const { comp } = await makeComponent();
    expect(comp.returnUrl).toBe('');
  });

  it('returnUrl retourne la valeur si présente', async () => {
    const { comp } = await makeComponent('/cyberscan/dashboard');
    expect(comp.returnUrl).toBe('/cyberscan/dashboard');
  });
});

describe('LoginComponent — validation du formulaire', () => {
  it('formulaire invalide avec email et password vides', async () => {
    const { comp } = await makeComponent();
    expect(comp.form.invalid).toBe(true);
  });

  it('formulaire invalide avec email malformé', async () => {
    const { comp } = await makeComponent();
    comp.form.setValue({ email: 'not-email', password: 'pass123' });
    expect(comp.form.invalid).toBe(true);
  });

  it('formulaire valide avec email et password corrects', async () => {
    const { comp } = await makeComponent();
    comp.form.setValue({ email: 'user@example.com', password: 'Password1!' });
    expect(comp.form.valid).toBe(true);
  });
});

describe('LoginComponent — submit()', () => {
  it('ne déclenche pas store.login si le formulaire est invalide', async () => {
    const { comp, loginMock } = await makeComponent();
    comp.form.setValue({ email: '', password: '' });
    comp.submit();
    expect(loginMock).not.toHaveBeenCalled();
  });

  it('déclenche store.login avec les bonnes credentials', async () => {
    const { comp, loginMock } = await makeComponent();
    comp.form.setValue({ email: 'user@example.com', password: 'Password1!' });
    comp.submit();
    expect(loginMock).toHaveBeenCalledWith({
      email: 'user@example.com',
      password: 'Password1!',
    });
  });
});

describe('LoginComponent — submitTotp()', () => {
  it('ne déclenche pas loginWith2FA si totpCode est incomplet', async () => {
    const { comp, loginWith2FAMock } = await makeComponent();
    comp.totpCode = '12345'; // 5 chiffres, pas 6
    comp.submitTotp();
    expect(loginWith2FAMock).not.toHaveBeenCalled();
  });

  it('déclenche loginWith2FA avec le code à 6 chiffres', async () => {
    const { comp, loginWith2FAMock } = await makeComponent();
    comp.totpCode = '123456';
    comp.submitTotp();
    expect(loginWith2FAMock).toHaveBeenCalledWith({ totpCode: '123456' });
  });
});

describe('LoginComponent — cancelTotp()', () => {
  it('réinitialise totpCode à vide', async () => {
    const { comp } = await makeComponent();
    comp.totpCode = '123456';
    comp.cancelTotp();
    expect(comp.totpCode).toBe('');
  });

  it('incrémente otpClear', async () => {
    const { comp } = await makeComponent();
    const before = comp.otpClear;
    comp.cancelTotp();
    expect(comp.otpClear).toBe(before + 1);
  });

  it('appelle store.cancelTwoFa()', async () => {
    const { comp, cancelTwoFaMock } = await makeComponent();
    comp.cancelTotp();
    expect(cancelTwoFaMock).toHaveBeenCalledOnce();
  });
});
