/**
 * DashboardComponent — tests des méthodes utilitaires pures.
 */
import { describe, it, expect } from 'vitest';
import { signal } from '@angular/core';
import { DashboardComponent } from './dashboard.component';

function make(): DashboardComponent {
  const comp = Object.create(DashboardComponent.prototype) as DashboardComponent;
  (comp as any).scansMap = signal({});
  (comp as any).sites = signal([]);
  return comp;
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

// ── Analytics helpers ──────────────────────────────────────────────────────────

const SCAN_OK = JSON.stringify({
  ssl: { status: 'OK' }, headers: { status: 'OK' }, email: { status: 'OK' },
  cookies: { status: 'OK' }, cors: { status: 'OK' }, ip: { status: 'OK' },
  dns: { status: 'OK' }, cms: { status: 'OK' }, waf: { status: 'OK' },
  tech: { status: 'OK' }, tls: { status: 'OK' }, takeover: { status: 'OK' },
  threat_intel: { status: 'OK' }, http_methods: { status: 'OK' },
  open_redirect: { status: 'OK' }, clickjacking: { status: 'OK' },
  directory_listing: { status: 'OK' }, robots: { status: 'OK' }, jwt: { status: 'OK' },
});

const SCAN_CRITICAL = JSON.stringify({
  ssl: { status: 'CRITICAL' }, headers: { status: 'CRITICAL' }, tls: { status: 'CRITICAL' },
});

function makeWithScans(scansPerSite: Record<number, { status: string; results_json: string; created_at: string }[]>): DashboardComponent {
  const comp = make();
  const map: Record<number, any> = {};
  for (const [id, items] of Object.entries(scansPerSite)) {
    map[Number(id)] = { items, total: items.length, page: 1, per_page: 10, pages: 1 };
  }
  (comp as any).scansMap = signal(map);
  (comp as any).sites = signal(Object.keys(scansPerSite).map(id => ({ id: Number(id), name: `site${id}`, url: `https://site${id}.com` })));
  return comp;
}

describe('DashboardComponent — scoreHistory()', () => {
  it('retourne vide si pas de scans done', () => {
    const comp = makeWithScans({ 1: [{ status: 'running', results_json: '', created_at: '2024-01-01' }] });
    expect(comp.scoreHistory(1)).toHaveLength(0);
  });

  it('retourne les scans done dans l\'ordre chronologique', () => {
    const scans = [
      { status: 'done', results_json: SCAN_OK, created_at: '2024-01-03' },
      { status: 'done', results_json: SCAN_OK, created_at: '2024-01-02' },
      { status: 'done', results_json: SCAN_OK, created_at: '2024-01-01' },
    ];
    const comp = makeWithScans({ 1: scans });
    const history = comp.scoreHistory(1);
    expect(history.length).toBeGreaterThan(0);
    expect(history[0].date).toBe('2024-01-01');
  });

  it('limite à n entrées', () => {
    const scans = Array.from({ length: 12 }, (_, i) => ({
      status: 'done', results_json: SCAN_OK, created_at: `2024-01-${String(i + 1).padStart(2, '0')}`,
    }));
    const comp = makeWithScans({ 1: scans });
    expect(comp.scoreHistory(1, 5)).toHaveLength(5);
  });
});

describe('DashboardComponent — sparklinePoints()', () => {
  it('retourne une chaîne vide si moins de 2 scans', () => {
    const comp = makeWithScans({ 1: [{ status: 'done', results_json: SCAN_OK, created_at: '2024-01-01' }] });
    expect(comp.sparklinePoints(1)).toBe('');
  });

  it('retourne des points SVG valides pour 2+ scans', () => {
    const scans = [
      { status: 'done', results_json: SCAN_OK, created_at: '2024-01-01' },
      { status: 'done', results_json: SCAN_CRITICAL, created_at: '2024-01-02' },
    ];
    const comp = makeWithScans({ 1: scans });
    const points = comp.sparklinePoints(1);
    expect(points).toBeTruthy();
    expect(points).toContain(',');
    expect(points.split(' ')).toHaveLength(2);
  });
});

describe('DashboardComponent — globalCategoryScores', () => {
  it('retourne vide si aucun scan done', () => {
    const comp = makeWithScans({ 1: [{ status: 'running', results_json: '', created_at: '' }] });
    expect(comp.globalCategoryScores).toHaveLength(0);
  });

  it('retourne 6 catégories si au moins un scan done', () => {
    const comp = makeWithScans({ 1: [{ status: 'done', results_json: SCAN_OK, created_at: '2024-01-01' }] });
    expect(comp.globalCategoryScores).toHaveLength(6);
  });

  it('scores entre 0 et 100', () => {
    const comp = makeWithScans({ 1: [{ status: 'done', results_json: SCAN_OK, created_at: '2024-01-01' }] });
    for (const cat of comp.globalCategoryScores) {
      expect(cat.score).toBeGreaterThanOrEqual(0);
      expect(cat.score).toBeLessThanOrEqual(100);
    }
  });
});

describe('DashboardComponent — criticalCount / warningCount / okCount', () => {
  it('criticalCount = 0 si aucun site critique', () => {
    const comp = makeWithScans({ 1: [{ status: 'done', results_json: SCAN_OK, overall_status: 'OK', created_at: '2024-01-01' }] });
    expect(comp.criticalCount).toBe(0);
  });

  it('criticalCount = 1 si un site CRITICAL', () => {
    const comp = makeWithScans({ 1: [{ status: 'done', results_json: SCAN_CRITICAL, overall_status: 'CRITICAL', created_at: '2024-01-01' }] });
    expect(comp.criticalCount).toBe(1);
  });

  it('okCount = 1 si un site OK', () => {
    const comp = makeWithScans({ 1: [{ status: 'done', results_json: SCAN_OK, overall_status: 'OK', created_at: '2024-01-01' }] });
    expect(comp.okCount).toBe(1);
  });
});
