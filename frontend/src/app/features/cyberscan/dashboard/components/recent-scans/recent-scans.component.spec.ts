/**
 * RecentScansComponent — tests des méthodes utilitaires pures.
 */
import { describe, it, expect } from 'vitest';
import { RecentScansComponent } from './recent-scans.component';

function make(): RecentScansComponent {
  return Object.create(RecentScansComponent.prototype) as RecentScansComponent;
}

describe('RecentScansComponent — statusColor()', () => {
  it('retourne vert pour OK', () => expect(make().statusColor('OK')).toContain('green'));
  it('retourne jaune pour WARNING', () =>
    expect(make().statusColor('WARNING')).toContain('yellow'));
  it('retourne rouge pour CRITICAL', () => expect(make().statusColor('CRITICAL')).toContain('red'));
  it('retourne rouge pour error', () => expect(make().statusColor('error')).toContain('red'));
  it('retourne vert pour done', () => expect(make().statusColor('done')).toContain('green'));
  it('retourne bleu pour pending', () => expect(make().statusColor('pending')).toContain('blue'));
  it('retourne bleu pour running', () => expect(make().statusColor('running')).toContain('blue'));
  it('retourne gris pour null', () => expect(make().statusColor(null)).toContain('gray'));
  it('retourne gris pour statut inconnu', () =>
    expect(make().statusColor('xyz')).toContain('gray'));
});

describe('RecentScansComponent — statusIcon()', () => {
  it('retourne verified_user pour OK', () => expect(make().statusIcon('OK')).toBe('verified_user'));
  it('retourne warning pour WARNING', () => expect(make().statusIcon('WARNING')).toBe('warning'));
  it('retourne gpp_bad pour CRITICAL', () => expect(make().statusIcon('CRITICAL')).toBe('gpp_bad'));
  it('retourne check_circle pour done', () =>
    expect(make().statusIcon('done')).toBe('check_circle'));
  it('retourne schedule pour pending', () => expect(make().statusIcon('pending')).toBe('schedule'));
  it('retourne sync pour running', () => expect(make().statusIcon('running')).toBe('sync'));
  it('retourne cancel pour error', () => expect(make().statusIcon('error')).toBe('cancel'));
  it('retourne help_outline pour null', () => expect(make().statusIcon(null)).toBe('help_outline'));
});

describe('RecentScansComponent — formatDate()', () => {
  it('retourne "—" pour null', () => expect(make().formatDate(null)).toBe('—'));
  it("formate une date ISO en incluant l'année", () =>
    expect(make().formatDate('2024-06-01T12:00:00Z')).toContain('2024'));
  it("inclut l'heure dans le résultat", () => {
    const result = make().formatDate('2024-06-01T12:00:00Z');
    expect(result).toMatch(/\d+:\d+/);
  });
});

describe('RecentScansComponent — getScanScore()', () => {
  it('retourne null pour un scan sans results_json', () => {
    const comp = make();
    expect(comp.getScanScore({ id: 1, results_json: null } as any)).toBeNull();
  });

  it('retourne null pour un scan avec results_json vide', () => {
    const comp = make();
    expect(comp.getScanScore({ id: 1, results_json: '' } as any)).toBeNull();
  });

  it('retourne un nombre pour un scan avec results_json valide', () => {
    const comp = make();
    const resultsJson = JSON.stringify({ ssl: { status: 'OK' }, headers: { status: 'OK' } });
    const score = comp.getScanScore({ id: 1, results_json: resultsJson } as any);
    expect(typeof score).toBe('number');
    expect(score).toBeGreaterThanOrEqual(0);
    expect(score).toBeLessThanOrEqual(100);
  });
});
