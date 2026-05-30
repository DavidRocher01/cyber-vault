import { describe, it, expect, vi } from 'vitest';
import { Injector, runInInjectionContext, signal } from '@angular/core';
import { Router } from '@angular/router';
import { awarenessLearnerGuard } from './awareness-learner.guard';
import { AwarenessService } from '../../features/cyberscan/services/awareness.service';

function run(hasSession: boolean) {
  const createUrlTree = vi.fn((cmds: unknown[]) => ({ cmds }));
  const svcMock = { learnerSession: signal(hasSession ? { email: 'a@b.com' } : null) };

  const injector = Injector.create({
    providers: [
      { provide: AwarenessService, useValue: svcMock },
      { provide: Router, useValue: { createUrlTree } },
    ],
  });

  const result = runInInjectionContext(injector, () => awarenessLearnerGuard({} as any, {} as any));
  return { result, createUrlTree };
}

describe('awarenessLearnerGuard', () => {
  it('retourne true si une session learner existe', () => {
    expect(run(true).result).toBe(true);
  });

  it('redirige vers /awareness/login sans session', () => {
    const { createUrlTree } = run(false);
    expect(createUrlTree).toHaveBeenCalledWith(['/awareness/login']);
  });

  it('ne crée pas de UrlTree quand session présente', () => {
    const { createUrlTree } = run(true);
    expect(createUrlTree).not.toHaveBeenCalled();
  });
});
