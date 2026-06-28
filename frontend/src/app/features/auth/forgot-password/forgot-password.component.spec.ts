/**
 * ForgotPasswordComponent — tests via injection de dépendances (HttpClient mocké).
 */
import { describe, it, expect, vi } from 'vitest';
import { Injector, runInInjectionContext } from '@angular/core';
import { FormBuilder } from '@angular/forms';
import { of, throwError } from 'rxjs';
import { HttpClient } from '@angular/common/http';

async function makeComponent() {
  const { ForgotPasswordComponent } = await import('./forgot-password.component');

  const httpMock = { post: vi.fn() };

  const injector = Injector.create({
    providers: [
      { provide: FormBuilder, useValue: new FormBuilder() },
      { provide: HttpClient, useValue: httpMock },
    ],
  });

  const comp = runInInjectionContext(injector, () => new ForgotPasswordComponent());
  return { comp, httpMock };
}

describe('ForgotPasswordComponent — état initial', () => {
  it('loading est false au départ', async () => {
    const { comp } = await makeComponent();
    expect(comp.loading).toBe(false);
  });

  it('sent est false au départ', async () => {
    const { comp } = await makeComponent();
    expect(comp.sent).toBe(false);
  });

  it('error est null au départ', async () => {
    const { comp } = await makeComponent();
    expect(comp.error).toBeNull();
  });

  it('le formulaire contient un champ email', async () => {
    const { comp } = await makeComponent();
    expect(comp.form.contains('email')).toBe(true);
  });
});

describe('ForgotPasswordComponent — validation du formulaire', () => {
  it('formulaire invalide avec email vide', async () => {
    const { comp } = await makeComponent();
    comp.form.setValue({ email: '' });
    expect(comp.form.invalid).toBe(true);
  });

  it('formulaire invalide avec email malformé', async () => {
    const { comp } = await makeComponent();
    comp.form.setValue({ email: 'not-an-email' });
    expect(comp.form.invalid).toBe(true);
  });

  it('formulaire valide avec email correct', async () => {
    const { comp } = await makeComponent();
    comp.form.setValue({ email: 'user@example.com' });
    expect(comp.form.valid).toBe(true);
  });
});

describe('ForgotPasswordComponent — submit() avec formulaire invalide', () => {
  it("ne fait pas d'appel HTTP si le formulaire est invalide", async () => {
    const { comp, httpMock } = await makeComponent();
    comp.form.setValue({ email: '' });
    comp.submit();
    expect(httpMock.post).not.toHaveBeenCalled();
  });
});

describe('ForgotPasswordComponent — submit() succès', () => {
  it('sent passe à true après succès', async () => {
    const { comp, httpMock } = await makeComponent();
    httpMock.post.mockReturnValue(of({}));
    comp.form.setValue({ email: 'user@example.com' });
    comp.submit();
    expect(comp.sent).toBe(true);
  });

  it('loading repasse à false après succès', async () => {
    const { comp, httpMock } = await makeComponent();
    httpMock.post.mockReturnValue(of({}));
    comp.form.setValue({ email: 'user@example.com' });
    comp.submit();
    expect(comp.loading).toBe(false);
  });

  it('error reste null après succès', async () => {
    const { comp, httpMock } = await makeComponent();
    httpMock.post.mockReturnValue(of({}));
    comp.form.setValue({ email: 'user@example.com' });
    comp.submit();
    expect(comp.error).toBeNull();
  });
});

describe('ForgotPasswordComponent — submit() erreur', () => {
  it('error est défini après une erreur', async () => {
    const { comp, httpMock } = await makeComponent();
    httpMock.post.mockReturnValue(throwError(() => new Error('network error')));
    comp.form.setValue({ email: 'user@example.com' });
    comp.submit();
    expect(comp.error).toBeTruthy();
  });

  it('loading repasse à false après erreur', async () => {
    const { comp, httpMock } = await makeComponent();
    httpMock.post.mockReturnValue(throwError(() => new Error('network error')));
    comp.form.setValue({ email: 'user@example.com' });
    comp.submit();
    expect(comp.loading).toBe(false);
  });

  it('sent reste false après erreur', async () => {
    const { comp, httpMock } = await makeComponent();
    httpMock.post.mockReturnValue(throwError(() => new Error('network error')));
    comp.form.setValue({ email: 'user@example.com' });
    comp.submit();
    expect(comp.sent).toBe(false);
  });
});
