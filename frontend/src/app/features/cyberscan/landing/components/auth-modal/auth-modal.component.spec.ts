/**
 * AuthModalComponent — bascule login/register, validation des formulaires,
 * transitions d'état (loading / erreur / 2FA). AuthService et Router mockés.
 */
import { describe, it, expect, vi } from 'vitest';
import { Injector, runInInjectionContext } from '@angular/core';
import { FormBuilder } from '@angular/forms';
import { Router } from '@angular/router';
import { of, throwError } from 'rxjs';
import { AuthService } from '../../../../../core/services/auth.service';
import { AuthModalComponent } from './auth-modal.component';

function make() {
  const authMock = { login: vi.fn(), register: vi.fn() };
  const routerMock = { navigate: vi.fn() };
  const injector = Injector.create({
    providers: [
      { provide: AuthService, useValue: authMock },
      { provide: Router, useValue: routerMock },
      { provide: FormBuilder, useValue: new FormBuilder() },
    ],
  });
  const comp = runInInjectionContext(injector, () => new AuthModalComponent());
  return { comp, authMock, routerMock };
}

describe('AuthModalComponent — état initial', () => {
  it('panneau fermé, pas d’étape 2FA, pas d’erreur', () => {
    const { comp } = make();
    expect(comp.authPanel()).toBe('closed');
    expect(comp.auth2faStep()).toBe(false);
    expect(comp.authError).toBeNull();
    expect(comp.authLoading).toBe(false);
  });
});

describe('AuthModalComponent — open() / openTab() / close()', () => {
  it('open("login") ouvre le panneau login et réinitialise l’état', () => {
    const { comp } = make();
    comp.authError = 'vieux message';
    comp.authLoading = true;
    comp.auth2faStep.set(true);
    comp.open('login');
    expect(comp.authPanel()).toBe('login');
    expect(comp.authError).toBeNull();
    expect(comp.authLoading).toBe(false);
    expect(comp.auth2faStep()).toBe(false);
  });

  it('open("register") ouvre le panneau register', () => {
    const { comp } = make();
    comp.open('register');
    expect(comp.authPanel()).toBe('register');
  });

  it('openTab bascule sans réinitialiser le loading', () => {
    const { comp } = make();
    comp.open('login');
    comp.authError = 'err';
    comp.openTab('register');
    expect(comp.authPanel()).toBe('register');
    expect(comp.authError).toBeNull();
  });

  it('close ferme le panneau et purge les identifiants en attente', () => {
    const { comp } = make();
    comp.open('login');
    comp.pendingEmail = 'a@b.com';
    comp.pendingPassword = 'secret';
    comp.auth2faStep.set(true);
    comp.close();
    expect(comp.authPanel()).toBe('closed');
    expect(comp.auth2faStep()).toBe(false);
    expect(comp.pendingEmail).toBe('');
    expect(comp.pendingPassword).toBe('');
  });
});

describe('AuthModalComponent — validation loginForm', () => {
  it('invalide si vide', () => {
    const { comp } = make();
    expect(comp.loginForm.invalid).toBe(true);
  });

  it('invalide si email mal formé', () => {
    const { comp } = make();
    comp.loginForm.setValue({ email: 'pas-un-email', password: 'x' });
    expect(comp.loginForm.invalid).toBe(true);
  });

  it('valide avec email correct et mot de passe', () => {
    const { comp } = make();
    comp.loginForm.setValue({ email: 'a@b.com', password: 'x' });
    expect(comp.loginForm.valid).toBe(true);
  });
});

describe('AuthModalComponent — validation registerForm', () => {
  it('erreur mismatch si les mots de passe diffèrent', () => {
    const { comp } = make();
    comp.registerForm.setValue({
      email: 'a@b.com',
      password: 'password1',
      confirmPassword: 'password2',
    });
    expect(comp.registerForm.errors?.['mismatch']).toBe(true);
    expect(comp.registerForm.invalid).toBe(true);
  });

  it('invalide si mot de passe trop court', () => {
    const { comp } = make();
    comp.registerForm.setValue({
      email: 'a@b.com',
      password: 'court',
      confirmPassword: 'court',
    });
    expect(comp.registerForm.get('password')?.invalid).toBe(true);
  });

  it('valide si emails/mots de passe cohérents', () => {
    const { comp } = make();
    comp.registerForm.setValue({
      email: 'a@b.com',
      password: 'password1',
      confirmPassword: 'password1',
    });
    expect(comp.registerForm.valid).toBe(true);
    expect(comp.registerForm.errors).toBeNull();
  });
});

describe('AuthModalComponent — submitLogin()', () => {
  it('ne fait rien si le formulaire est invalide', () => {
    const { comp, authMock } = make();
    comp.submitLogin();
    expect(authMock.login).not.toHaveBeenCalled();
  });

  it('ne relance pas si déjà en chargement', () => {
    const { comp, authMock } = make();
    comp.loginForm.setValue({ email: 'a@b.com', password: 'x' });
    comp.authLoading = true;
    comp.submitLogin();
    expect(authMock.login).not.toHaveBeenCalled();
  });

  it('succès sans 2FA -> ferme et navigue vers /', () => {
    const { comp, authMock, routerMock } = make();
    authMock.login.mockReturnValue(of({ access_token: 'jwt' }));
    comp.loginForm.setValue({ email: 'a@b.com', password: 'x' });
    comp.submitLogin();
    expect(authMock.login).toHaveBeenCalledWith('a@b.com', 'x');
    expect(comp.authPanel()).toBe('closed');
    expect(routerMock.navigate).toHaveBeenCalledWith(['/']);
  });

  it('réponse requires_2fa -> passe à l’étape TOTP et mémorise les identifiants', () => {
    const { comp, authMock, routerMock } = make();
    authMock.login.mockReturnValue(of({ requires_2fa: true }));
    comp.loginForm.setValue({ email: 'a@b.com', password: 'x' });
    comp.submitLogin();
    expect(comp.auth2faStep()).toBe(true);
    expect(comp.pendingEmail).toBe('a@b.com');
    expect(comp.pendingPassword).toBe('x');
    expect(comp.authLoading).toBe(false);
    expect(routerMock.navigate).not.toHaveBeenCalled();
  });

  it('erreur -> affiche le détail et coupe le loading', () => {
    const { comp, authMock } = make();
    authMock.login.mockReturnValue(throwError(() => ({ error: { detail: 'Bloqué' } })));
    comp.loginForm.setValue({ email: 'a@b.com', password: 'x' });
    comp.submitLogin();
    expect(comp.authError).toBe('Bloqué');
    expect(comp.authLoading).toBe(false);
  });

  it('erreur sans détail -> message par défaut', () => {
    const { comp, authMock } = make();
    authMock.login.mockReturnValue(throwError(() => ({ error: {} })));
    comp.loginForm.setValue({ email: 'a@b.com', password: 'x' });
    comp.submitLogin();
    expect(comp.authError).toBe('Identifiants incorrects.');
  });
});

describe('AuthModalComponent — submitLoginTotp()', () => {
  it('ne fait rien si le code n’a pas 6 chiffres', () => {
    const { comp, authMock } = make();
    comp.authOtpCode = '123';
    comp.submitLoginTotp();
    expect(authMock.login).not.toHaveBeenCalled();
  });

  it('succès -> ferme et navigue vers /', () => {
    const { comp, authMock, routerMock } = make();
    comp.pendingEmail = 'a@b.com';
    comp.pendingPassword = 'x';
    comp.authOtpCode = '123456';
    authMock.login.mockReturnValue(of({ access_token: 'jwt' }));
    comp.submitLoginTotp();
    expect(authMock.login).toHaveBeenCalledWith('a@b.com', 'x', '123456');
    expect(comp.authPanel()).toBe('closed');
    expect(routerMock.navigate).toHaveBeenCalledWith(['/']);
  });

  it('erreur -> message, loading coupé, incrémente authOtpClear', () => {
    const { comp, authMock } = make();
    comp.authOtpCode = '123456';
    const before = comp.authOtpClear;
    authMock.login.mockReturnValue(throwError(() => ({ error: { detail: 'Code invalide.' } })));
    comp.submitLoginTotp();
    expect(comp.authError).toBe('Code invalide.');
    expect(comp.authLoading).toBe(false);
    expect(comp.authOtpClear).toBe(before + 1);
  });
});

describe('AuthModalComponent — cancelAuth2fa()', () => {
  it('quitte l’étape 2FA et purge le code', () => {
    const { comp } = make();
    comp.auth2faStep.set(true);
    comp.authError = 'err';
    comp.authOtpCode = '123456';
    comp.cancelAuth2fa();
    expect(comp.auth2faStep()).toBe(false);
    expect(comp.authError).toBeNull();
    expect(comp.authOtpCode).toBe('');
  });
});

describe('AuthModalComponent — submitRegister()', () => {
  it('ne fait rien si le formulaire est invalide', () => {
    const { comp, authMock } = make();
    comp.submitRegister();
    expect(authMock.register).not.toHaveBeenCalled();
  });

  it('succès -> register puis login enchaînés, navigation /onboarding', () => {
    const { comp, authMock, routerMock } = make();
    authMock.register.mockReturnValue(of({ id: 1 }));
    authMock.login.mockReturnValue(of({ access_token: 'jwt' }));
    comp.registerForm.setValue({
      email: 'a@b.com',
      password: 'password1',
      confirmPassword: 'password1',
    });
    comp.submitRegister();
    expect(authMock.register).toHaveBeenCalledWith('a@b.com', 'password1');
    expect(authMock.login).toHaveBeenCalledWith('a@b.com', 'password1');
    expect(comp.authPanel()).toBe('closed');
    expect(routerMock.navigate).toHaveBeenCalledWith(['/onboarding']);
  });

  it('erreur -> affiche le détail et coupe le loading', () => {
    const { comp, authMock } = make();
    authMock.register.mockReturnValue(throwError(() => ({ error: { detail: 'Email déjà pris' } })));
    comp.registerForm.setValue({
      email: 'a@b.com',
      password: 'password1',
      confirmPassword: 'password1',
    });
    comp.submitRegister();
    expect(comp.authError).toBe('Email déjà pris');
    expect(comp.authLoading).toBe(false);
  });
});

describe('AuthModalComponent — registerPasswordStrength / registerStrengthLabel', () => {
  function setPw(comp: AuthModalComponent, pw: string) {
    comp.registerForm.get('password')?.setValue(pw);
  }

  it('score 0 -> Faible', () => {
    const { comp } = make();
    setPw(comp, '');
    expect(comp.registerPasswordStrength).toBe(0);
    expect(comp.registerStrengthLabel).toBe('Faible');
  });

  it('longueur seule (>=8) -> score 1 -> Faible', () => {
    const { comp } = make();
    setPw(comp, 'aaaaaaaa');
    expect(comp.registerPasswordStrength).toBe(1);
    expect(comp.registerStrengthLabel).toBe('Faible');
  });

  it('longueur + majuscule -> score 2 -> Moyen', () => {
    const { comp } = make();
    setPw(comp, 'Aaaaaaaa');
    expect(comp.registerPasswordStrength).toBe(2);
    expect(comp.registerStrengthLabel).toBe('Moyen');
  });

  it('longueur + majuscule + chiffre -> score 3 -> Fort', () => {
    const { comp } = make();
    setPw(comp, 'Aaaaaaa1');
    expect(comp.registerPasswordStrength).toBe(3);
    expect(comp.registerStrengthLabel).toBe('Fort');
  });

  it('les 4 critères -> score 4 -> Très fort', () => {
    const { comp } = make();
    setPw(comp, 'Aaaaaa1!');
    expect(comp.registerPasswordStrength).toBe(4);
    expect(comp.registerStrengthLabel).toBe('Très fort');
  });
});
