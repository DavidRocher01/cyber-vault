import { describe, it, expect } from 'vitest';
import { ScanDetailComponent } from './scan-detail.component';

function make(): ScanDetailComponent {
  return Object.create(ScanDetailComponent.prototype) as ScanDetailComponent;
}

describe('ScanDetailComponent — statusColor()', () => {
  it('retourne vert pour OK', () => expect(make().statusColor('OK')).toContain('green'));
  it('retourne jaune pour WARNING', () => expect(make().statusColor('WARNING')).toContain('yellow'));
  it('retourne rouge pour CRITICAL', () => expect(make().statusColor('CRITICAL')).toContain('red'));
  it('retourne gris par défaut', () => expect(make().statusColor(null)).toContain('gray'));
  it('retourne gris pour une valeur inconnue', () => expect(make().statusColor('unknown')).toContain('gray'));
});

describe('ScanDetailComponent — statusIcon()', () => {
  it('retourne verified_user pour OK', () => expect(make().statusIcon('OK')).toBe('verified_user'));
  it('retourne warning pour WARNING', () => expect(make().statusIcon('WARNING')).toBe('warning'));
  it('retourne gpp_bad pour CRITICAL', () => expect(make().statusIcon('CRITICAL')).toBe('gpp_bad'));
  it('retourne check_circle pour done', () => expect(make().statusIcon('done')).toBe('check_circle'));
  it('retourne schedule pour pending', () => expect(make().statusIcon('pending')).toBe('schedule'));
  it('retourne sync pour running', () => expect(make().statusIcon('running')).toBe('sync'));
  it('retourne cancel pour error', () => expect(make().statusIcon('error')).toBe('cancel'));
  it('retourne help_outline pour null', () => expect(make().statusIcon(null)).toBe('help_outline'));
});

describe('ScanDetailComponent — formatDate()', () => {
  it('retourne "—" pour null', () => expect(make().formatDate(null)).toBe('—'));
  it('formate une date ISO', () => expect(make().formatDate('2024-03-15T10:30:00Z')).toContain('2024'));
  it('inclut l\'heure', () => expect(make().formatDate('2024-03-15T10:30:00Z')).toMatch(/\d+:\d+/));
});
