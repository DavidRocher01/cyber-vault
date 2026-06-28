/**
 * CollabAcceptComponent — accepte une invitation collaborateur via token.
 */
import { describe, it, expect, vi } from 'vitest';
import { Injector, runInInjectionContext } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Title } from '@angular/platform-browser';
import { of, throwError } from 'rxjs';
import { CollabService } from '../services/collab.service';

async function makeComponent(token = 'tok123') {
  const { CollabAcceptComponent } = await import('./collab-accept.component');
  const collabMock = { acceptInvite: vi.fn() };
  const route = { snapshot: { paramMap: { get: (k: string) => (k === 'token' ? token : null) } } };
  const injector = Injector.create({
    providers: [
      { provide: ActivatedRoute, useValue: route },
      { provide: CollabService, useValue: collabMock },
      { provide: Title, useValue: { setTitle: vi.fn() } },
    ],
  });
  const comp = runInInjectionContext(injector, () => new CollabAcceptComponent());
  return { comp, collabMock };
}

describe('CollabAcceptComponent', () => {
  it('appelle acceptInvite avec le token', async () => {
    const { comp, collabMock } = await makeComponent('abc');
    collabMock.acceptInvite.mockReturnValue(of({ role: 'viewer' }));
    comp.ngOnInit();
    expect(collabMock.acceptInvite).toHaveBeenCalledWith('abc');
  });

  it('succès -> collab défini, loading false, pas d’erreur', async () => {
    const { comp, collabMock } = await makeComponent();
    collabMock.acceptInvite.mockReturnValue(of({ role: 'auditor' }));
    comp.ngOnInit();
    expect(comp.collab()).toEqual({ role: 'auditor' });
    expect(comp.loading()).toBe(false);
    expect(comp.error()).toBeNull();
  });

  it('erreur -> error défini, loading false', async () => {
    const { comp, collabMock } = await makeComponent();
    collabMock.acceptInvite.mockReturnValue(throwError(() => ({ error: { detail: 'Expirée' } })));
    comp.ngOnInit();
    expect(comp.error()).toBe('Expirée');
    expect(comp.loading()).toBe(false);
  });

  it('roleLabel mappe les rôles connus et inconnus', async () => {
    const { comp } = await makeComponent();
    expect(comp.roleLabel('viewer')).toBe('Lecteur');
    expect(comp.roleLabel('auditor')).toBe('Auditeur');
    expect(comp.roleLabel('manager')).toBe('Manager');
    expect(comp.roleLabel('inconnu')).toBe('inconnu');
  });
});
