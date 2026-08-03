import { describe, it, expect } from 'vitest';
import { Injector, runInInjectionContext } from '@angular/core';
import { of, throwError } from 'rxjs';

import { AdminAuthService } from './admin-auth.service';
import { AuthService } from '../../../core/services/auth.service';

/**
 * Le service n'a plus qu'une voie d'accès : un compte `is_admin`. La clé
 * `X-Admin-Key` — secret partagé sans identité ni révocation, relevé par
 * l'audit du 2026-07-27 — a été retirée le 2026-08-02.
 */
function make(me: unknown = throwError(() => new Error('non connecté'))): AdminAuthService {
  const injector = Injector.create({
    providers: [{ provide: AuthService, useValue: { me: () => me } }],
  });
  return runInInjectionContext(injector, () => new AdminAuthService());
}

const attendre = (svc: AdminAuthService) =>
  new Promise<boolean>(r => svc.verifierCompte().subscribe(r as (v: boolean) => void));

describe('AdminAuthService — état initial', () => {
  it('démarre fermé, et en cours de vérification', () => {
    const svc = make();
    expect(svc.authenticated()).toBe(false);
    expect(svc.verificationEnCours()).toBe(true);
  });
});

describe('AdminAuthService — accès par compte', () => {
  it('un compte administrateur ouvre le back-office', async () => {
    const svc = make(of({ id: 1, email: 'a@b.c', is_admin: true }));
    expect(await attendre(svc)).toBe(true);
    expect(svc.authenticated()).toBe(true);
    expect(svc.verificationEnCours()).toBe(false);
  });

  it("un compte ordinaire n'ouvre rien", async () => {
    // Le point qui compte : être connecté ne suffit pas.
    const svc = make(of({ id: 2, email: 'x@y.z', is_admin: false }));
    expect(await attendre(svc)).toBe(false);
    expect(svc.authenticated()).toBe(false);
  });

  it("un visiteur non connecté n'est pas une erreur", async () => {
    // La plupart des visiteurs de /admin ne sont simplement pas connectés :
    // on affiche une invitation, pas un message d'échec.
    const svc = make(throwError(() => new Error('401')));
    expect(await attendre(svc)).toBe(false);
    expect(svc.verificationEnCours()).toBe(false);
  });

  it('aucune clé ne subsiste dans un storage', () => {
    // Non-régression : plus aucun secret admin au repos, nulle part.
    const svc = make();
    expect(svc).not.toHaveProperty('adminKey');
    expect(sessionStorage.getItem('admin_key')).toBeNull();
    expect(localStorage.getItem('admin_key')).toBeNull();
  });
});

describe('AdminAuthService — logout()', () => {
  it('referme le back-office', async () => {
    const svc = make(of({ id: 1, email: 'a@b.c', is_admin: true }));
    await attendre(svc);
    svc.logout();
    expect(svc.authenticated()).toBe(false);
  });
});
