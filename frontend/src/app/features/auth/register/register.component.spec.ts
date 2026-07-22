import { describe, it, expect, vi } from 'vitest';
import { Injector, runInInjectionContext } from '@angular/core';
import { FormBuilder } from '@angular/forms';
import { of, throwError } from 'rxjs';

async function makeComponent(returnUrl?: string, authOverride?: Record<string, unknown>) {
  const { RegisterComponent } = await import('./register.component');
  const { AuthService } = await import('../../../core/services/auth.service');
  const { Router, ActivatedRoute } = await import('@angular/router');

  const navigateByUrlMock = vi.fn();
  const authServiceMock = {
    register: vi.fn().mockReturnValue(of({})),
    login: vi.fn().mockReturnValue(of({ access_token: 'tok', token_type: 'bearer' })),
    ...authOverride,
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
      { provide: AuthService, useValue: authServiceMock },
      { provide: Router, useValue: { navigate: vi.fn(), navigateByUrl: navigateByUrlMock } },
      { provide: ActivatedRoute, useValue: routeMock },
    ],
  });

  const component = runInInjectionContext(injector, () => new RegisterComponent());
  return { component, navigateByUrlMock, authServiceMock };
}

describe('RegisterComponent — returnUrl', () => {
  it('returnUrl getter retourne null si absent', async () => {
    const { component } = await makeComponent();
    expect(component.returnUrl).toBeNull();
  });

  it('returnUrl getter retourne la valeur si présente', async () => {
    const { component } = await makeComponent('/dashboard');
    expect(component.returnUrl).toBe('/dashboard');
  });

  it('returnUrl getter retourne null si url pointe vers /vault', async () => {
    const { component } = await makeComponent('/vault');
    expect(component.returnUrl).toBeNull();
  });

  it('returnUrl getter retourne null pour /auth/master-password', async () => {
    const { component } = await makeComponent('/auth/master-password');
    expect(component.returnUrl).toBeNull();
  });

  it('returnUrl getter retourne null pour /cyberscan sans slash final', async () => {
    const { component } = await makeComponent('/');
    expect(component.returnUrl).toBeNull();
  });

  it('navigue vers returnUrl après inscription si présent', async () => {
    const { component, navigateByUrlMock } = await makeComponent('/dashboard');
    component.form.setValue({
      email: 'a@b.com',
      password: 'Password1!',
      confirmPassword: 'Password1!',
    });
    component.submit();
    await new Promise(r => setTimeout(r, 20));
    expect(navigateByUrlMock).toHaveBeenCalledWith('/dashboard');
  });

  it('navigue vers /cyberscan/onboarding si pas de returnUrl', async () => {
    const { component, navigateByUrlMock } = await makeComponent();
    component.form.setValue({
      email: 'a@b.com',
      password: 'Password1!',
      confirmPassword: 'Password1!',
    });
    component.submit();
    await new Promise(r => setTimeout(r, 20));
    expect(navigateByUrlMock).toHaveBeenCalledWith('/onboarding');
  });

  it('navigue vers /cyberscan/onboarding si returnUrl pointe vers /vault', async () => {
    const { component, navigateByUrlMock } = await makeComponent('/vault');
    component.form.setValue({
      email: 'a@b.com',
      password: 'Password1!',
      confirmPassword: 'Password1!',
    });
    component.submit();
    await new Promise(r => setTimeout(r, 20));
    expect(navigateByUrlMock).toHaveBeenCalledWith('/onboarding');
  });

  it('navigue vers /cyberscan/onboarding si returnUrl pointe vers /auth/master-password', async () => {
    const { component, navigateByUrlMock } = await makeComponent('/auth/master-password');
    component.form.setValue({
      email: 'a@b.com',
      password: 'Password1!',
      confirmPassword: 'Password1!',
    });
    component.submit();
    await new Promise(r => setTimeout(r, 20));
    expect(navigateByUrlMock).toHaveBeenCalledWith('/onboarding');
  });

  it('returnUrl getter retourne null pour une redirection externe //evil', async () => {
    const { component } = await makeComponent('//evil.com');
    expect(component.returnUrl).toBeNull();
  });

  it('returnUrl getter retourne null pour une redirection /\\ (backslash)', async () => {
    const { component } = await makeComponent('/\\evil.com');
    expect(component.returnUrl).toBeNull();
  });

  it('returnUrl getter retourne null pour /awareness', async () => {
    const { component } = await makeComponent('/awareness/modules');
    expect(component.returnUrl).toBeNull();
  });

  it('returnUrl getter accepte un sous-chemin applicatif valide', async () => {
    const { component } = await makeComponent('/cyberscan/sites/1');
    expect(component.returnUrl).toBe('/cyberscan/sites/1');
  });
});

describe('RegisterComponent — submit (gardes & erreurs)', () => {
  it('submit ne fait rien si le formulaire est invalide', async () => {
    const { component, authServiceMock, navigateByUrlMock } = await makeComponent();
    // formulaire vierge => required manquants => invalide
    component.submit();
    expect(authServiceMock.register).not.toHaveBeenCalled();
    expect(navigateByUrlMock).not.toHaveBeenCalled();
    expect(component.loading).toBe(false);
  });

  it('submit ne fait rien si les mots de passe ne correspondent pas', async () => {
    const { component, authServiceMock } = await makeComponent();
    component.form.setValue({
      email: 'a@b.com',
      password: 'Password1!',
      confirmPassword: 'Autre1!aa',
    });
    expect(component.form.hasError('mismatch')).toBe(true);
    component.submit();
    expect(authServiceMock.register).not.toHaveBeenCalled();
  });

  it("submit renseigne error avec le détail serveur en cas d'échec register", async () => {
    const { component, navigateByUrlMock } = await makeComponent(undefined, {
      register: vi
        .fn()
        .mockReturnValue(throwError(() => ({ error: { detail: 'email déjà pris' } }))),
    });
    component.form.setValue({
      email: 'a@b.com',
      password: 'Password1!',
      confirmPassword: 'Password1!',
    });
    component.submit();
    await new Promise(r => setTimeout(r, 20));
    expect(component.error).toBe('email déjà pris');
    expect(component.loading).toBe(false);
    expect(navigateByUrlMock).not.toHaveBeenCalled();
  });

  it('submit fournit un message par défaut si aucun détail serveur', async () => {
    const { component } = await makeComponent(undefined, {
      register: vi.fn().mockReturnValue(throwError(() => ({}))),
    });
    component.form.setValue({
      email: 'a@b.com',
      password: 'Password1!',
      confirmPassword: 'Password1!',
    });
    component.submit();
    await new Promise(r => setTimeout(r, 20));
    expect(component.error).toBe('Erreur inscription');
    expect(component.loading).toBe(false);
  });

  it('submit propage une erreur survenue au login (après register OK)', async () => {
    const { component } = await makeComponent(undefined, {
      login: vi.fn().mockReturnValue(throwError(() => ({ error: { detail: 'login KO' } }))),
    });
    component.form.setValue({
      email: 'a@b.com',
      password: 'Password1!',
      confirmPassword: 'Password1!',
    });
    component.submit();
    await new Promise(r => setTimeout(r, 20));
    expect(component.error).toBe('login KO');
    expect(component.loading).toBe(false);
  });
});

describe('RegisterComponent — passwordStrength & strengthLabel', () => {
  async function withPassword(pw: string) {
    const { component } = await makeComponent();
    component.form.get('password')?.setValue(pw);
    return component;
  }

  it('score 0 (mot de passe vide) => Faible', async () => {
    const c = await withPassword('');
    expect(c.passwordStrength).toBe(0);
    expect(c.strengthLabel).toBe('Faible');
  });

  it('score 1 (uniquement longueur) => Faible', async () => {
    const c = await withPassword('abcdefgh');
    expect(c.passwordStrength).toBe(1);
    expect(c.strengthLabel).toBe('Faible');
  });

  it('score 2 (majuscule + chiffre, trop court) => Moyen', async () => {
    const c = await withPassword('Abc1');
    expect(c.passwordStrength).toBe(2);
    expect(c.strengthLabel).toBe('Moyen');
  });

  it('score 3 (longueur + majuscule + chiffre) => Fort', async () => {
    const c = await withPassword('Abcdefg1');
    expect(c.passwordStrength).toBe(3);
    expect(c.strengthLabel).toBe('Fort');
  });

  it('score 4 (tous les critères) => Très fort', async () => {
    const c = await withPassword('Abcdefg1!');
    expect(c.passwordStrength).toBe(4);
    expect(c.strengthLabel).toBe('Très fort');
  });
});
