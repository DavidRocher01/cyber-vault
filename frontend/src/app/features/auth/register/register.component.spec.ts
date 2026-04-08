import { describe, it, expect, vi } from 'vitest';
import { Injector, runInInjectionContext } from '@angular/core';
import { FormBuilder } from '@angular/forms';
import { of } from 'rxjs';

async function makeComponent(returnUrl?: string) {
  const { RegisterComponent } = await import('./register.component');
  const { AuthService } = await import('../../../core/services/auth.service');
  const { Router, ActivatedRoute } = await import('@angular/router');

  const navigateByUrlMock = vi.fn();
  const authServiceMock = {
    register: vi.fn().mockReturnValue(of({})),
    login: vi.fn().mockReturnValue(of({ access_token: 'tok', token_type: 'bearer' })),
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
  return { component, navigateByUrlMock };
}

describe('RegisterComponent — returnUrl', () => {
  it('returnUrl getter retourne null si absent', async () => {
    const { component } = await makeComponent();
    expect(component.returnUrl).toBeNull();
  });

  it('returnUrl getter retourne la valeur si présente', async () => {
    const { component } = await makeComponent('/cyberscan/dashboard');
    expect(component.returnUrl).toBe('/cyberscan/dashboard');
  });

  it('navigue vers returnUrl après inscription si présent', async () => {
    const { component, navigateByUrlMock } = await makeComponent('/cyberscan/dashboard');
    component.form.setValue({ email: 'a@b.com', password: 'Password1!', confirmPassword: 'Password1!' });
    component.submit();
    await new Promise(r => setTimeout(r, 20));
    expect(navigateByUrlMock).toHaveBeenCalledWith('/cyberscan/dashboard');
  });

  it('navigue vers /cyberscan/onboarding si pas de returnUrl', async () => {
    const { component, navigateByUrlMock } = await makeComponent();
    component.form.setValue({ email: 'a@b.com', password: 'Password1!', confirmPassword: 'Password1!' });
    component.submit();
    await new Promise(r => setTimeout(r, 20));
    expect(navigateByUrlMock).toHaveBeenCalledWith('/cyberscan/onboarding');
  });
});
