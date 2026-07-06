/**
 * AwarenessLoginComponent — tests de logique (magic-link) via injection de dépendances.
 * AwarenessService / Router / ActivatedRoute mockés, aucun appel réseau.
 */
import { describe, it, expect, vi } from 'vitest';
import { Injector, runInInjectionContext } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { of, throwError } from 'rxjs';
import { AwarenessService } from '../cyberscan/services/awareness.service';

async function makeComponent(opts: { session?: unknown; tokenParam?: string | null } = {}) {
  const { AwarenessLoginComponent } = await import('./awareness-login.component');

  const svcMock = {
    learnerSession: vi.fn().mockReturnValue(opts.session ?? null),
    verifyMagicLink: vi.fn(),
  };
  const routerMock = { navigate: vi.fn() };
  const routeMock = {
    snapshot: {
      queryParamMap: { get: vi.fn().mockReturnValue(opts.tokenParam ?? null) },
    },
  };

  const injector = Injector.create({
    providers: [
      { provide: AwarenessService, useValue: svcMock },
      { provide: Router, useValue: routerMock },
      { provide: ActivatedRoute, useValue: routeMock },
    ],
  });

  const comp = runInInjectionContext(injector, () => new AwarenessLoginComponent());
  return { comp, svcMock, routerMock, routeMock };
}

describe('AwarenessLoginComponent — état initial', () => {
  it('token est vide au départ', async () => {
    const { comp } = await makeComponent();
    expect(comp.token).toBe('');
  });

  it('verifying est false au départ', async () => {
    const { comp } = await makeComponent();
    expect(comp.verifying()).toBe(false);
  });

  it('loading est false au départ', async () => {
    const { comp } = await makeComponent();
    expect(comp.loading()).toBe(false);
  });

  it('error est false au départ', async () => {
    const { comp } = await makeComponent();
    expect(comp.error()).toBe(false);
  });
});

describe('AwarenessLoginComponent — ngOnInit (session existante)', () => {
  it('redirige vers /awareness si déjà connecté', async () => {
    const { comp, routerMock } = await makeComponent({ session: { access_token: 'x' } });
    comp.ngOnInit();
    expect(routerMock.navigate).toHaveBeenCalledWith(['/awareness']);
  });

  it('ne tente pas de vérifier de token si déjà connecté', async () => {
    const { comp, svcMock } = await makeComponent({
      session: { access_token: 'x' },
      tokenParam: 'tok',
    });
    comp.ngOnInit();
    expect(svcMock.verifyMagicLink).not.toHaveBeenCalled();
  });
});

describe('AwarenessLoginComponent — ngOnInit (auto-verify token URL)', () => {
  it("ne fait rien si pas de token dans l'URL", async () => {
    const { comp, svcMock, routerMock } = await makeComponent({ tokenParam: null });
    comp.ngOnInit();
    expect(svcMock.verifyMagicLink).not.toHaveBeenCalled();
    expect(routerMock.navigate).not.toHaveBeenCalled();
    expect(comp.verifying()).toBe(false);
  });

  it("vérifie le token présent dans l'URL", async () => {
    const { comp, svcMock } = await makeComponent({ tokenParam: 'magic-url' });
    svcMock.verifyMagicLink.mockReturnValue(of({ access_token: 'ok' }));
    comp.ngOnInit();
    expect(svcMock.verifyMagicLink).toHaveBeenCalledWith('magic-url');
  });

  it('redirige vers /awareness après vérification réussie', async () => {
    const { comp, svcMock, routerMock } = await makeComponent({ tokenParam: 'magic-url' });
    svcMock.verifyMagicLink.mockReturnValue(of({ access_token: 'ok' }));
    comp.ngOnInit();
    expect(routerMock.navigate).toHaveBeenCalledWith(['/awareness']);
  });

  it("affiche l'erreur et coupe verifying si le token URL est invalide", async () => {
    const { comp, svcMock } = await makeComponent({ tokenParam: 'bad' });
    svcMock.verifyMagicLink.mockReturnValue(throwError(() => new Error('invalid')));
    comp.ngOnInit();
    expect(comp.verifying()).toBe(false);
    expect(comp.error()).toBe(true);
  });
});

describe('AwarenessLoginComponent — verifyToken() court-circuits', () => {
  it('ne fait rien si token vide', async () => {
    const { comp, svcMock } = await makeComponent();
    comp.token = '';
    comp.verifyToken();
    expect(svcMock.verifyMagicLink).not.toHaveBeenCalled();
  });

  it('ne fait rien si token uniquement des espaces', async () => {
    const { comp, svcMock } = await makeComponent();
    comp.token = '   ';
    comp.verifyToken();
    expect(svcMock.verifyMagicLink).not.toHaveBeenCalled();
  });
});

describe('AwarenessLoginComponent — verifyToken() succès', () => {
  it('vérifie le token une fois nettoyé (trim)', async () => {
    const { comp, svcMock } = await makeComponent();
    svcMock.verifyMagicLink.mockReturnValue(of({ access_token: 'ok' }));
    comp.token = '  code-123  ';
    comp.verifyToken();
    expect(svcMock.verifyMagicLink).toHaveBeenCalledWith('code-123');
  });

  it('redirige vers /awareness après succès', async () => {
    const { comp, svcMock, routerMock } = await makeComponent();
    svcMock.verifyMagicLink.mockReturnValue(of({ access_token: 'ok' }));
    comp.token = 'code-123';
    comp.verifyToken();
    expect(routerMock.navigate).toHaveBeenCalledWith(['/awareness']);
  });

  it('ne met pas error à true en cas de succès', async () => {
    const { comp, svcMock } = await makeComponent();
    svcMock.verifyMagicLink.mockReturnValue(of({ access_token: 'ok' }));
    comp.token = 'code-123';
    comp.verifyToken();
    expect(comp.error()).toBe(false);
  });
});

describe('AwarenessLoginComponent — verifyToken() erreur', () => {
  it("active error et coupe loading en cas d'échec", async () => {
    const { comp, svcMock, routerMock } = await makeComponent();
    svcMock.verifyMagicLink.mockReturnValue(throwError(() => new Error('nope')));
    comp.token = 'bad-code';
    comp.verifyToken();
    expect(comp.error()).toBe(true);
    expect(comp.loading()).toBe(false);
    expect(routerMock.navigate).not.toHaveBeenCalled();
  });
});
