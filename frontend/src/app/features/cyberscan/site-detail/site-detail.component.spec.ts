import { describe, it, expect } from 'vitest';
import { SiteDetailComponent } from './site-detail.component';

function make(): SiteDetailComponent {
  return Object.create(SiteDetailComponent.prototype) as SiteDetailComponent;
}

describe('SiteDetailComponent — statusColor()', () => {
  it('retourne vert pour OK', () => expect(make().statusColor('OK')).toContain('green'));
  it('retourne jaune pour WARNING', () => expect(make().statusColor('WARNING')).toContain('yellow'));
  it('retourne rouge pour CRITICAL', () => expect(make().statusColor('CRITICAL')).toContain('red'));
  it('retourne vert pour done', () => expect(make().statusColor('done')).toContain('green'));
  it('retourne bleu pour pending', () => expect(make().statusColor('pending')).toContain('blue'));
  it('retourne bleu pour running', () => expect(make().statusColor('running')).toContain('blue'));
  it('retourne rouge pour error', () => expect(make().statusColor('error')).toContain('red'));
  it('retourne gris pour null', () => expect(make().statusColor(null)).toContain('gray'));
});

describe('SiteDetailComponent — statusIcon()', () => {
  it('retourne verified_user pour OK', () => expect(make().statusIcon('OK')).toBe('verified_user'));
  it('retourne warning pour WARNING', () => expect(make().statusIcon('WARNING')).toBe('warning'));
  it('retourne gpp_bad pour CRITICAL', () => expect(make().statusIcon('CRITICAL')).toBe('gpp_bad'));
  it('retourne check_circle pour done', () => expect(make().statusIcon('done')).toBe('check_circle'));
  it('retourne schedule pour pending', () => expect(make().statusIcon('pending')).toBe('schedule'));
  it('retourne sync pour running', () => expect(make().statusIcon('running')).toBe('sync'));
  it('retourne cancel pour error', () => expect(make().statusIcon('error')).toBe('cancel'));
  it('retourne help_outline pour null', () => expect(make().statusIcon(null)).toBe('help_outline'));
});

describe('SiteDetailComponent — formatDate()', () => {
  it('retourne "—" pour null', () => expect(make().formatDate(null)).toBe('—'));
  it('formate une date ISO', () => expect(make().formatDate('2024-03-15T10:00:00Z')).toContain('2024'));
  it('inclut l\'heure', () => expect(make().formatDate('2024-03-15T10:30:00Z')).toMatch(/\d+:\d+/));
});

describe('SiteDetailComponent — formatDateShort()', () => {
  it('retourne "—" pour null', () => expect(make().formatDateShort(null)).toBe('—'));
  it('formate une date en format court', () => {
    const result = make().formatDateShort('2024-06-01T08:00:00Z');
    expect(result).toContain('2024');
    expect(result).toMatch(/\d{2}\/\d{2}\/\d{4}/);
  });
  it('format court diffère du format long', () => {
    const d = '2024-06-01T08:00:00Z';
    expect(make().formatDateShort(d)).not.toBe(make().formatDate(d));
  });
});

describe('SiteDetailComponent — toggleFinding()', () => {
  it('ajoute la clé au premier clic', () => {
    const c = make();
    c.flippedFindings = new Set();
    c.toggleFinding('ssl');
    expect(c.flippedFindings.has('ssl')).toBe(true);
  });

  it('retire la clé au second clic', () => {
    const c = make();
    c.flippedFindings = new Set();
    c.toggleFinding('ssl');
    c.toggleFinding('ssl');
    expect(c.flippedFindings.has('ssl')).toBe(false);
  });

  it('gère plusieurs failles indépendamment', () => {
    const c = make();
    c.flippedFindings = new Set();
    c.toggleFinding('ssl');
    c.toggleFinding('headers');
    expect(c.flippedFindings.has('ssl')).toBe(true);
    expect(c.flippedFindings.has('headers')).toBe(true);
    c.toggleFinding('ssl');
    expect(c.flippedFindings.has('ssl')).toBe(false);
    expect(c.flippedFindings.has('headers')).toBe(true);
  });
});
