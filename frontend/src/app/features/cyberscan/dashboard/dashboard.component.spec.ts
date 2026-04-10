/**
 * DashboardComponent — tests des méthodes utilitaires pures.
 */
import { describe, it, expect } from 'vitest';
import { DashboardComponent } from './dashboard.component';

function make(): DashboardComponent {
  return Object.create(DashboardComponent.prototype) as DashboardComponent;
}

describe('DashboardComponent — statusColor()', () => {
  it('retourne vert pour OK', () => expect(make().statusColor('OK')).toContain('green'));
  it('retourne jaune pour WARNING', () => expect(make().statusColor('WARNING')).toContain('yellow'));
  it('retourne rouge pour CRITICAL', () => expect(make().statusColor('CRITICAL')).toContain('red'));
  it('retourne rouge pour error', () => expect(make().statusColor('error')).toContain('red'));
  it('retourne vert pour done', () => expect(make().statusColor('done')).toContain('green'));
  it('retourne bleu pour pending', () => expect(make().statusColor('pending')).toContain('blue'));
  it('retourne bleu pour running', () => expect(make().statusColor('running')).toContain('blue'));
  it('retourne gris pour null', () => expect(make().statusColor(null)).toContain('gray'));
  it('retourne gris pour inconnu', () => expect(make().statusColor('xyz')).toContain('gray'));
});

describe('DashboardComponent — statusIcon()', () => {
  it('retourne verified_user pour OK', () => expect(make().statusIcon('OK')).toBe('verified_user'));
  it('retourne warning pour WARNING', () => expect(make().statusIcon('WARNING')).toBe('warning'));
  it('retourne gpp_bad pour CRITICAL', () => expect(make().statusIcon('CRITICAL')).toBe('gpp_bad'));
  it('retourne check_circle pour done', () => expect(make().statusIcon('done')).toBe('check_circle'));
  it('retourne schedule pour pending', () => expect(make().statusIcon('pending')).toBe('schedule'));
  it('retourne sync pour running', () => expect(make().statusIcon('running')).toBe('sync'));
  it('retourne cancel pour error', () => expect(make().statusIcon('error')).toBe('cancel'));
  it('retourne help_outline pour inconnu', () => expect(make().statusIcon(null)).toBe('help_outline'));
});

describe('DashboardComponent — formatDate()', () => {
  it('retourne "—" pour null', () => expect(make().formatDate(null)).toBe('—'));
  it('formate une date ISO', () => expect(make().formatDate('2024-06-01T12:00:00Z')).toContain('2024'));
  it('inclut l\'heure dans le format', () => {
    const result = make().formatDate('2024-06-01T12:00:00Z');
    expect(result).toMatch(/\d+:\d+/);
  });
});

describe('DashboardComponent — getGrade()', () => {
  it('retourne une note pour un score', () => {
    const grade = make().getGrade(85);
    expect(typeof grade).toBe('string');
    expect(grade.length).toBeGreaterThan(0);
  });

  it('retourne une note différente pour un score bas', () => {
    const high = make().getGrade(90);
    const low = make().getGrade(20);
    expect(high).not.toBe(low);
  });
});

describe('DashboardComponent — getScoreColor()', () => {
  it('retourne une couleur CSS pour un score élevé', () => {
    expect(make().getScoreColor(85)).toBeTruthy();
  });

  it('retourne une couleur différente selon le score', () => {
    const c1 = make().getScoreColor(10);
    const c2 = make().getScoreColor(90);
    expect(c1).not.toBe(c2);
  });
});
