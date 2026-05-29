import { describe, it, expect } from 'vitest';
import { signal } from '@angular/core';
import { AwarenessAdminComponent } from './awareness-admin.component';

function make(): AwarenessAdminComponent {
  const comp = Object.create(AwarenessAdminComponent.prototype) as AwarenessAdminComponent;
  (comp as any).orgs = signal([]);
  (comp as any).loading = signal(false);
  (comp as any).creating = signal(false);
  return comp;
}

describe('AwarenessAdminComponent — completionColor()', () => {
  it('text-green-400 si taux >= 80', () =>
    expect(make().completionColor(80)).toBe('text-green-400'));
  it('text-green-400 si taux = 100', () =>
    expect(make().completionColor(100)).toBe('text-green-400'));
  it('text-yellow-400 si taux entre 50 et 79', () =>
    expect(make().completionColor(50)).toBe('text-yellow-400'));
  it('text-yellow-400 si taux = 79', () =>
    expect(make().completionColor(79)).toBe('text-yellow-400'));
  it('text-red-400 si taux < 50', () => expect(make().completionColor(49)).toBe('text-red-400'));
  it('text-red-400 si taux = 0', () => expect(make().completionColor(0)).toBe('text-red-400'));
});

describe('AwarenessAdminComponent — completionBarColor()', () => {
  it('bg-green-500 si taux >= 80', () =>
    expect(make().completionBarColor(80)).toBe('bg-green-500'));
  it('bg-yellow-500 si taux entre 50 et 79', () =>
    expect(make().completionBarColor(65)).toBe('bg-yellow-500'));
  it('bg-red-500 si taux < 50', () => expect(make().completionBarColor(30)).toBe('bg-red-500'));
});
