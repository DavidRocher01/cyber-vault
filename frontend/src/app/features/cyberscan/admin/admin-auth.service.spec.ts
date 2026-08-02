import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Injector, runInInjectionContext } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { of, throwError } from 'rxjs';

import { AdminAuthService } from './admin-auth.service';
import { AuthService } from '../../../core/services/auth.service';

/**
 * Le service a désormais DEUX voies d'accès (compte administrateur, puis clé de
 * secours), donc deux dépendances résolues par `inject()`. Il est instancié
 * dans un contexte d'injection créé à la main — même patron que la spec du
 * shell. `TestBed.resetTestingModule()` détruirait l'environnement de test posé
 * par le fichier de setup.
 */
function make(me: unknown = throwError(() => new Error('non connecté'))): {
  svc: AdminAuthService;
  http: { get: ReturnType<typeof vi.fn> };
} {
  const http = { get: vi.fn().mockReturnValue(of({})) };
  const injector = Injector.create({
    providers: [
      { provide: HttpClient, useValue: http },
      { provide: AuthService, useValue: { me: () => me } },
    ],
  });
  const svc = runInInjectionContext(injector, () => new AdminAuthService());
  return { svc, http };
}

describe('AdminAuthService — état initial', () => {
  beforeEach(() => sessionStorage.clear());

  it('démarre non authentifié', () => {
    const { svc } = make();
    expect(svc.authenticated()).toBe(false);
    expect(svc.adminKey()).toBe('');
    expect(svc.parCompte()).toBe(false);
  });

  it("ne lit AUCUN storage (pas de restauration d'une clé persistée — S6)", () => {
    // Une clé laissée par une ancienne version ne doit PLUS être reprise.
    sessionStorage.setItem('admin_key', 'legacy-key');
    const { svc } = make();
    expect(svc.authenticated()).toBe(false);
    expect(svc.adminKey()).toBe('');
  });
});

describe('AdminAuthService — accès par compte administrateur', () => {
  it('ouvre le back-office sans saisie de clé', async () => {
    const { svc } = make(of({ id: 1, email: 'a@b.c', is_admin: true }));
    const estAdmin = await new Promise(r => svc.verifierCompte().subscribe(r));
    expect(estAdmin).toBe(true);
    expect(svc.authenticated()).toBe(true);
    expect(svc.parCompte()).toBe(true);
  });

  it("un compte ordinaire n'ouvre rien", async () => {
    const { svc } = make(of({ id: 2, email: 'x@y.z', is_admin: false }));
    const estAdmin = await new Promise(r => svc.verifierCompte().subscribe(r));
    expect(estAdmin).toBe(false);
    expect(svc.authenticated()).toBe(false);
  });

  it("un visiteur non connecté n'est pas une erreur — on retombe sur la clé", async () => {
    const { svc } = make(throwError(() => new Error('401')));
    const estAdmin = await new Promise(r => svc.verifierCompte().subscribe(r));
    expect(estAdmin).toBe(false);
    expect(svc.verificationEnCours()).toBe(false);
  });

  it("en mode compte, aucune clé n'est envoyée", async () => {
    // L'intercepteur pose déjà Authorization ; ajouter une clé VIDE ferait
    // échouer la comparaison serveur sur les routes qui l'acceptent encore.
    const { svc } = make(of({ id: 1, email: 'a@b.c', is_admin: true }));
    await new Promise(r => svc.verifierCompte().subscribe(r));
    expect(svc.headers().has('X-Admin-Key')).toBe(false);
  });
});

describe('AdminAuthService — clé de secours', () => {
  beforeEach(() => sessionStorage.clear());

  it('active authenticated et pose la clé en mémoire', () => {
    const { svc } = make();
    svc.login('secret-key');
    expect(svc.authenticated()).toBe(true);
    expect(svc.adminKey()).toBe('secret-key');
    expect(svc.parCompte()).toBe(false);
  });

  it('ne persiste JAMAIS la clé dans un storage (S6 — pas de secret au repos)', () => {
    const { svc } = make();
    svc.login('persist-me');
    expect(sessionStorage.getItem('admin_key')).toBeNull();
    expect(localStorage.getItem('admin_key')).toBeNull();
  });

  it('la clé ne survit pas à une nouvelle instance (re-saisie par session)', () => {
    make().svc.login('ephemeral');
    // Nouvelle instance = rechargement complet simulé → état vierge.
    const { svc } = make();
    expect(svc.authenticated()).toBe(false);
    expect(svc.adminKey()).toBe('');
  });

  it('headers() porte X-Admin-Key après login', () => {
    const { svc } = make();
    svc.login('test-key');
    expect(svc.headers().get('X-Admin-Key')).toBe('test-key');
  });

  it('X-Admin-Key est vide avant login', () => {
    const { svc } = make();
    expect(svc.headers().get('X-Admin-Key')).toBe('');
  });

  it('verify() appelle GET /api/v1/admin/stats avec la clé fournie', () => {
    const { svc, http } = make();
    svc.verify('my-key');
    expect(http.get).toHaveBeenCalledWith(
      '/api/v1/admin/stats',
      expect.objectContaining({ headers: expect.anything() })
    );
  });
});

describe('AdminAuthService — logout()', () => {
  it('désactive tout, quelle que soit la voie utilisée', async () => {
    const { svc } = make(of({ id: 1, email: 'a@b.c', is_admin: true }));
    await new Promise(r => svc.verifierCompte().subscribe(r));
    svc.logout();
    expect(svc.authenticated()).toBe(false);
    expect(svc.adminKey()).toBe('');
    expect(svc.parCompte()).toBe(false);
  });
});
