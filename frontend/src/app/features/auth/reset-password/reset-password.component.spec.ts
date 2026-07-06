/**
 * ResetPasswordComponent — tests de logique via injection de dépendances.
 * HttpClient / ActivatedRoute mockés, aucun appel réseau.
 */
import { describe, it, expect, vi } from 'vitest';
import { Injector, runInInjectionContext } from '@angular/core';
import { FormBuilder } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { of, throwError } from 'rxjs';

async function makeComponent(token: string | null = 'tok-123') {
  const { ResetPasswordComponent } = await import('./reset-password.component');

  const httpMock = { post: vi.fn() };
  const routeMock = {
    snapshot: { queryParamMap: { get: vi.fn().mockReturnValue(token) } },
  };

  const injector = Injector.create({
    providers: [
      { provide: FormBuilder, useValue: new FormBuilder() },
      { provide: HttpClient, useValue: httpMock },
      { provide: ActivatedRoute, useValue: routeMock },
    ],
  });

  const comp = runInInjectionContext(injector, () => new ResetPasswordComponent());
  return { comp, httpMock, routeMock };
}

describe('ResetPasswordComponent — état initial', () => {
  it('loading est false au départ', async () => {
    const { comp } = await makeComponent();
    expect(comp.loading).toBe(false);
  });

  it('done est false au départ', async () => {
    const { comp } = await makeComponent();
    expect(comp.done).toBe(false);
  });

  it('error est null au départ', async () => {
    const { comp } = await makeComponent();
    expect(comp.error).toBeNull();
  });

  it("token est null tant que ngOnInit n'est pas appelé", async () => {
    const { comp } = await makeComponent();
    expect(comp.token).toBeNull();
  });

  it('showPassword est false au départ', async () => {
    const { comp } = await makeComponent();
    expect(comp.showPassword).toBe(false);
  });
});

describe('ResetPasswordComponent — ngOnInit (token magic-link)', () => {
  it('récupère le token depuis les query params', async () => {
    const { comp } = await makeComponent('magic-abc');
    comp.ngOnInit();
    expect(comp.token).toBe('magic-abc');
  });

  it("token reste null si absent de l'URL", async () => {
    const { comp } = await makeComponent(null);
    comp.ngOnInit();
    expect(comp.token).toBeNull();
  });
});

describe('ResetPasswordComponent — validation du formulaire', () => {
  it('invalide si mot de passe trop court (< 8)', async () => {
    const { comp } = await makeComponent();
    comp.form.setValue({ password: 'Abc1', confirmPassword: 'Abc1' });
    expect(comp.form.invalid).toBe(true);
  });

  it('invalide si les mots de passe ne correspondent pas', async () => {
    const { comp } = await makeComponent();
    comp.form.setValue({ password: 'Password1', confirmPassword: 'Password2' });
    expect(comp.form.hasError('mismatch')).toBe(true);
    expect(comp.form.invalid).toBe(true);
  });

  it('invalide si confirmPassword est vide', async () => {
    const { comp } = await makeComponent();
    comp.form.setValue({ password: 'Password1', confirmPassword: '' });
    expect(comp.form.invalid).toBe(true);
  });

  it('valide si mdp assez long et identiques', async () => {
    const { comp } = await makeComponent();
    comp.form.setValue({ password: 'Password1', confirmPassword: 'Password1' });
    expect(comp.form.valid).toBe(true);
    expect(comp.form.hasError('mismatch')).toBe(false);
  });
});

describe('ResetPasswordComponent — passwordStrength', () => {
  it('score 0 pour chaîne vide', async () => {
    const { comp } = await makeComponent();
    comp.form.get('password')!.setValue('');
    expect(comp.passwordStrength).toBe(0);
  });

  it('score 1 pour 8 caractères minuscules seulement', async () => {
    const { comp } = await makeComponent();
    comp.form.get('password')!.setValue('abcdefgh');
    expect(comp.passwordStrength).toBe(1);
  });

  it('score 4 pour maj + chiffre + spécial + longueur', async () => {
    const { comp } = await makeComponent();
    comp.form.get('password')!.setValue('Abcdef1!');
    expect(comp.passwordStrength).toBe(4);
  });

  it('score 2 pour longueur + majuscule sans chiffre ni spécial', async () => {
    const { comp } = await makeComponent();
    comp.form.get('password')!.setValue('Abcdefgh');
    expect(comp.passwordStrength).toBe(2);
  });
});

describe('ResetPasswordComponent — strengthLabel', () => {
  it('Faible pour score <= 1', async () => {
    const { comp } = await makeComponent();
    comp.form.get('password')!.setValue('abcdefgh');
    expect(comp.strengthLabel).toBe('Faible');
  });

  it('Moyen pour score 2', async () => {
    const { comp } = await makeComponent();
    comp.form.get('password')!.setValue('Abcdefgh');
    expect(comp.strengthLabel).toBe('Moyen');
  });

  it('Fort pour score 3', async () => {
    const { comp } = await makeComponent();
    comp.form.get('password')!.setValue('Abcdefg1');
    expect(comp.strengthLabel).toBe('Fort');
  });

  it('Très fort pour score 4', async () => {
    const { comp } = await makeComponent();
    comp.form.get('password')!.setValue('Abcdef1!');
    expect(comp.strengthLabel).toBe('Très fort');
  });
});

describe('ResetPasswordComponent — submit() court-circuits', () => {
  it("ne fait pas d'appel HTTP si le formulaire est invalide", async () => {
    const { comp, httpMock } = await makeComponent();
    comp.ngOnInit();
    comp.form.setValue({ password: 'short', confirmPassword: 'short' });
    comp.submit();
    expect(httpMock.post).not.toHaveBeenCalled();
  });

  it("ne fait pas d'appel HTTP si le token est absent", async () => {
    const { comp, httpMock } = await makeComponent(null);
    comp.ngOnInit();
    comp.form.setValue({ password: 'Password1', confirmPassword: 'Password1' });
    comp.submit();
    expect(httpMock.post).not.toHaveBeenCalled();
  });
});

describe('ResetPasswordComponent — submit() succès', () => {
  it('envoie token + password dans le corps', async () => {
    const { comp, httpMock } = await makeComponent('tok-xyz');
    httpMock.post.mockReturnValue(of({}));
    comp.ngOnInit();
    comp.form.setValue({ password: 'Password1', confirmPassword: 'Password1' });
    comp.submit();
    expect(httpMock.post).toHaveBeenCalledWith(expect.stringContaining('/auth/reset-password'), {
      token: 'tok-xyz',
      password: 'Password1',
    });
  });

  it('done passe à true après succès', async () => {
    const { comp, httpMock } = await makeComponent();
    httpMock.post.mockReturnValue(of({}));
    comp.ngOnInit();
    comp.form.setValue({ password: 'Password1', confirmPassword: 'Password1' });
    comp.submit();
    expect(comp.done).toBe(true);
  });

  it('loading repasse à false après succès', async () => {
    const { comp, httpMock } = await makeComponent();
    httpMock.post.mockReturnValue(of({}));
    comp.ngOnInit();
    comp.form.setValue({ password: 'Password1', confirmPassword: 'Password1' });
    comp.submit();
    expect(comp.loading).toBe(false);
  });

  it('error reste null après succès', async () => {
    const { comp, httpMock } = await makeComponent();
    httpMock.post.mockReturnValue(of({}));
    comp.ngOnInit();
    comp.form.setValue({ password: 'Password1', confirmPassword: 'Password1' });
    comp.submit();
    expect(comp.error).toBeNull();
  });
});

describe('ResetPasswordComponent — submit() erreur', () => {
  it('utilise err.error.detail comme message si présent', async () => {
    const { comp, httpMock } = await makeComponent();
    httpMock.post.mockReturnValue(throwError(() => ({ error: { detail: 'Token expiré' } })));
    comp.ngOnInit();
    comp.form.setValue({ password: 'Password1', confirmPassword: 'Password1' });
    comp.submit();
    expect(comp.error).toBe('Token expiré');
  });

  it('message par défaut si pas de detail', async () => {
    const { comp, httpMock } = await makeComponent();
    httpMock.post.mockReturnValue(throwError(() => ({ error: {} })));
    comp.ngOnInit();
    comp.form.setValue({ password: 'Password1', confirmPassword: 'Password1' });
    comp.submit();
    expect(comp.error).toBe('Lien invalide ou expiré.');
  });

  it('loading repasse à false après erreur', async () => {
    const { comp, httpMock } = await makeComponent();
    httpMock.post.mockReturnValue(throwError(() => ({ error: {} })));
    comp.ngOnInit();
    comp.form.setValue({ password: 'Password1', confirmPassword: 'Password1' });
    comp.submit();
    expect(comp.loading).toBe(false);
  });

  it('done reste false après erreur', async () => {
    const { comp, httpMock } = await makeComponent();
    httpMock.post.mockReturnValue(throwError(() => ({ error: {} })));
    comp.ngOnInit();
    comp.form.setValue({ password: 'Password1', confirmPassword: 'Password1' });
    comp.submit();
    expect(comp.done).toBe(false);
  });
});
