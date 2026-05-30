import { describe, it, expect } from 'vitest';
import { signal } from '@angular/core';
import { ApiLandingComponent } from './api-landing.component';

function make(): ApiLandingComponent {
  const comp = Object.create(ApiLandingComponent.prototype) as ApiLandingComponent;
  (comp as any).codeCopied = signal(false);
  (comp as any).activeTab = signal(0);
  return comp;
}

describe('ApiLandingComponent — colorFor()', () => {
  it('text-cyan-400 pour cyan', () => expect(make().colorFor('cyan')).toBe('text-cyan-400'));
  it('text-purple-400 pour purple', () =>
    expect(make().colorFor('purple')).toBe('text-purple-400'));
  it('text-indigo-400 pour indigo', () =>
    expect(make().colorFor('indigo')).toBe('text-indigo-400'));
  it('fallback text-cyan-400 pour couleur inconnue', () =>
    expect(make().colorFor('red')).toBe('text-cyan-400'));
});

describe('ApiLandingComponent — borderFor()', () => {
  it('contient cyan pour cyan', () => expect(make().borderFor('cyan')).toContain('cyan'));
  it('contient purple pour purple', () => expect(make().borderFor('purple')).toContain('purple'));
  it('contient indigo pour indigo', () => expect(make().borderFor('indigo')).toContain('indigo'));
  it('fallback cyan pour couleur inconnue', () =>
    expect(make().borderFor('orange')).toContain('cyan'));
});

describe('ApiLandingComponent — bgFor()', () => {
  it('contient cyan pour cyan', () => expect(make().bgFor('cyan')).toContain('cyan'));
  it('contient purple pour purple', () => expect(make().bgFor('purple')).toContain('purple'));
  it('contient indigo pour indigo', () => expect(make().bgFor('indigo')).toContain('indigo'));
  it('fallback cyan pour couleur inconnue', () => expect(make().bgFor('green')).toContain('cyan'));
});
