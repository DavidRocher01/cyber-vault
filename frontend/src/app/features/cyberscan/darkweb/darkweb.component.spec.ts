import { describe, it, expect } from 'vitest';
import { signal } from '@angular/core';
import { DarkwebComponent } from './darkweb.component';

function make(): DarkwebComponent {
  const comp = Object.create(DarkwebComponent.prototype) as DarkwebComponent;
  (comp as any).status = signal(null);
  (comp as any).loading = signal(true);
  (comp as any).checking = signal(false);
  return comp;
}

describe('DarkwebComponent — statusColor()', () => {
  it('text-green-400 pour OK', () => expect(make().statusColor('OK')).toBe('text-green-400'));
  it('text-yellow-400 pour WARNING', () =>
    expect(make().statusColor('WARNING')).toBe('text-yellow-400'));
  it('text-red-400 pour CRITICAL', () =>
    expect(make().statusColor('CRITICAL')).toBe('text-red-400'));
  it('text-gray-400 par défaut', () => expect(make().statusColor('unknown')).toBe('text-gray-400'));
});

describe('DarkwebComponent — statusBg()', () => {
  it('contient green pour OK', () => expect(make().statusBg('OK')).toContain('green'));
  it('contient yellow pour WARNING', () => expect(make().statusBg('WARNING')).toContain('yellow'));
  it('contient red pour CRITICAL', () => expect(make().statusBg('CRITICAL')).toContain('red'));
  it('contient gray par défaut', () => expect(make().statusBg('unknown')).toContain('gray'));
});

describe('DarkwebComponent — statusIcon()', () => {
  it('verified pour OK', () => expect(make().statusIcon('OK')).toBe('verified'));
  it('warning pour WARNING', () => expect(make().statusIcon('WARNING')).toBe('warning'));
  it('gpp_bad pour CRITICAL', () => expect(make().statusIcon('CRITICAL')).toBe('gpp_bad'));
  it('help_outline par défaut', () => expect(make().statusIcon('unknown')).toBe('help_outline'));
});

describe('DarkwebComponent — statusLabel()', () => {
  it('Aucune fuite pour OK', () => expect(make().statusLabel('OK')).toContain('fuite'));
  it('Fuite(s) pour WARNING', () => expect(make().statusLabel('WARNING')).toContain('Fuite'));
  it('Fuites multiples pour CRITICAL', () =>
    expect(make().statusLabel('CRITICAL')).toContain('multiple'));
  it('Non vérifié pour not_checked', () =>
    expect(make().statusLabel('not_checked')).toBe('Non vérifié'));
  it('Indisponible par défaut', () => expect(make().statusLabel('other')).toBe('Indisponible'));
});

describe('DarkwebComponent — formatDate()', () => {
  it('retourne — pour null', () => expect(make().formatDate(null)).toBe('—'));
  it("contient l'année pour une date valide", () => {
    const result = make().formatDate('2024-06-15T10:00:00Z');
    expect(result).toContain('2024');
  });
  it('contient le mois en lettres', () => {
    const result = make().formatDate('2024-06-15T10:00:00Z');
    expect(result).toContain('juin');
  });
});

describe('DarkwebComponent — formatPwnCount()', () => {
  it('affiche en millions si ≥ 1 000 000', () => {
    expect(make().formatPwnCount(1_500_000)).toBe('1.5M');
  });
  it('affiche en milliers si ≥ 1 000', () => {
    expect(make().formatPwnCount(2_500)).toBe('3K');
  });
  it('affiche le chiffre exact si < 1 000', () => {
    expect(make().formatPwnCount(42)).toBe('42');
  });
  it('affiche 1.0M pour exactement 1 million', () => {
    expect(make().formatPwnCount(1_000_000)).toBe('1.0M');
  });
  it('affiche 1K pour exactement 1 000', () => {
    expect(make().formatPwnCount(1_000)).toBe('1K');
  });
});
