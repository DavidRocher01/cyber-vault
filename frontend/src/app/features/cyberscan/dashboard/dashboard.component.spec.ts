/**
 * DashboardComponent — tests des méthodes utilitaires pures.
 */
import { describe, it, expect, vi } from 'vitest';
import { signal } from '@angular/core';
import { of, throwError } from 'rxjs';
import { DashboardComponent } from './dashboard.component';

function make(): DashboardComponent {
  const comp = Object.create(DashboardComponent.prototype) as DashboardComponent;
  (comp as any).scansMap = signal({});
  (comp as any).sites = signal([]);
  return comp;
}

describe('DashboardComponent — statusColor()', () => {
  it('retourne vert pour OK', () => expect(make().statusColor('OK')).toContain('green'));
  it('retourne jaune pour WARNING', () =>
    expect(make().statusColor('WARNING')).toContain('yellow'));
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
  it('retourne check_circle pour done', () =>
    expect(make().statusIcon('done')).toBe('check_circle'));
  it('retourne schedule pour pending', () => expect(make().statusIcon('pending')).toBe('schedule'));
  it('retourne sync pour running', () => expect(make().statusIcon('running')).toBe('sync'));
  it('retourne cancel pour error', () => expect(make().statusIcon('error')).toBe('cancel'));
  it('retourne help_outline pour inconnu', () =>
    expect(make().statusIcon(null)).toBe('help_outline'));
});

describe('DashboardComponent — formatDate()', () => {
  it('retourne "—" pour null', () => expect(make().formatDate(null)).toBe('—'));
  it('formate une date ISO', () =>
    expect(make().formatDate('2024-06-01T12:00:00Z')).toContain('2024'));
  it("inclut l'heure dans le format", () => {
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
  ssl: { status: 'OK' },
  headers: { status: 'OK' },
  email: { status: 'OK' },
  cookies: { status: 'OK' },
  cors: { status: 'OK' },
  ip: { status: 'OK' },
  dns: { status: 'OK' },
  cms: { status: 'OK' },
  waf: { status: 'OK' },
  tech: { status: 'OK' },
  tls: { status: 'OK' },
  takeover: { status: 'OK' },
  threat_intel: { status: 'OK' },
  http_methods: { status: 'OK' },
  open_redirect: { status: 'OK' },
  clickjacking: { status: 'OK' },
  directory_listing: { status: 'OK' },
  robots: { status: 'OK' },
  jwt: { status: 'OK' },
});

const SCAN_CRITICAL = JSON.stringify({
  ssl: { status: 'CRITICAL' },
  headers: { status: 'CRITICAL' },
  tls: { status: 'CRITICAL' },
});

function makeWithScans(
  scansPerSite: Record<number, { status: string; results_json: string; created_at: string }[]>
): DashboardComponent {
  const comp = make();
  const map: Record<number, any> = {};
  for (const [id, items] of Object.entries(scansPerSite)) {
    map[Number(id)] = { items, total: items.length, page: 1, per_page: 10, pages: 1 };
  }
  (comp as any).scansMap = signal(map);
  (comp as any).sites = signal(
    Object.keys(scansPerSite).map(id => ({
      id: Number(id),
      name: `site${id}`,
      url: `https://site${id}.com`,
    }))
  );
  return comp;
}

describe('DashboardComponent — scoreHistory()', () => {
  it('retourne vide si pas de scans done', () => {
    const comp = makeWithScans({
      1: [{ status: 'running', results_json: '', created_at: '2024-01-01' }],
    });
    expect(comp.scoreHistory(1)).toHaveLength(0);
  });

  it("retourne les scans done dans l'ordre chronologique", () => {
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
      status: 'done',
      results_json: SCAN_OK,
      created_at: `2024-01-${String(i + 1).padStart(2, '0')}`,
    }));
    const comp = makeWithScans({ 1: scans });
    expect(comp.scoreHistory(1, 5)).toHaveLength(5);
  });
});

describe('DashboardComponent — sparklinePoints()', () => {
  it('retourne une chaîne vide si moins de 2 scans', () => {
    const comp = makeWithScans({
      1: [{ status: 'done', results_json: SCAN_OK, created_at: '2024-01-01' }],
    });
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
    const comp = makeWithScans({
      1: [{ status: 'done', results_json: SCAN_OK, created_at: '2024-01-01' }],
    });
    expect(comp.globalCategoryScores).toHaveLength(6);
  });

  it('scores entre 0 et 100', () => {
    const comp = makeWithScans({
      1: [{ status: 'done', results_json: SCAN_OK, created_at: '2024-01-01' }],
    });
    for (const cat of comp.globalCategoryScores) {
      expect(cat.score).toBeGreaterThanOrEqual(0);
      expect(cat.score).toBeLessThanOrEqual(100);
    }
  });
});

describe('DashboardComponent — globalScoreTimeline', () => {
  it('retourne vide si aucun site', () => {
    expect(make().globalScoreTimeline).toHaveLength(0);
  });

  it('fusionne les historiques de plusieurs sites', () => {
    const comp = makeWithScans({
      1: [
        { status: 'done', results_json: SCAN_OK, created_at: '2024-01-01' },
        { status: 'done', results_json: SCAN_OK, created_at: '2024-01-02' },
      ],
      2: [{ status: 'done', results_json: SCAN_OK, created_at: '2024-01-03' }],
    });
    expect(comp.globalScoreTimeline).toHaveLength(3);
  });

  it('est trié par date croissante', () => {
    const comp = makeWithScans({
      1: [
        { status: 'done', results_json: SCAN_OK, created_at: '2024-01-03' },
        { status: 'done', results_json: SCAN_OK, created_at: '2024-01-01' },
      ],
    });
    const tl = comp.globalScoreTimeline;
    expect(tl[0].date).toBe('2024-01-01');
    expect(tl[1].date).toBe('2024-01-03');
  });

  it('ignore les scans non-done', () => {
    const comp = makeWithScans({
      1: [{ status: 'running', results_json: '', created_at: '2024-01-01' }],
    });
    expect(comp.globalScoreTimeline).toHaveLength(0);
  });
});

describe('DashboardComponent — globalTrendChartPoints()', () => {
  it('retourne chaîne vide si aucun scan', () => {
    expect(make().globalTrendChartPoints()).toBe('');
  });

  it('retourne chaîne vide si un seul scan', () => {
    const comp = makeWithScans({
      1: [{ status: 'done', results_json: SCAN_OK, created_at: '2024-01-01' }],
    });
    expect(comp.globalTrendChartPoints()).toBe('');
  });

  it('retourne des paires x,y séparées par des espaces pour 2+ scans', () => {
    const comp = makeWithScans({
      1: [
        { status: 'done', results_json: SCAN_OK, created_at: '2024-01-01' },
        { status: 'done', results_json: SCAN_CRITICAL, created_at: '2024-01-02' },
      ],
    });
    const points = comp.globalTrendChartPoints();
    expect(points).toBeTruthy();
    const pairs = points.split(' ');
    expect(pairs).toHaveLength(2);
    for (const pair of pairs) {
      expect(pair).toMatch(/^\d+(\.\d+)?,\d+(\.\d+)?$/);
    }
  });

  it('premier point à cx=0 et dernier point à cx=w', () => {
    const comp = makeWithScans({
      1: [
        { status: 'done', results_json: SCAN_OK, created_at: '2024-01-01' },
        { status: 'done', results_json: SCAN_OK, created_at: '2024-01-02' },
      ],
    });
    const points = comp.globalTrendChartPoints(100, 50).split(' ');
    expect(Number(points[0].split(',')[0])).toBe(0);
    expect(Number(points[points.length - 1].split(',')[0])).toBe(100);
  });
});

describe('DashboardComponent — globalTrendDots', () => {
  it('retourne vide si moins de 2 scans', () => {
    expect(make().globalTrendDots).toHaveLength(0);
  });

  it('retourne autant de dots que de scans', () => {
    const comp = makeWithScans({
      1: [
        { status: 'done', results_json: SCAN_OK, created_at: '2024-01-01' },
        { status: 'done', results_json: SCAN_OK, created_at: '2024-01-02' },
        { status: 'done', results_json: SCAN_OK, created_at: '2024-01-03' },
      ],
    });
    expect(comp.globalTrendDots).toHaveLength(3);
  });

  it('chaque dot a cx et cy numériques', () => {
    const comp = makeWithScans({
      1: [
        { status: 'done', results_json: SCAN_OK, created_at: '2024-01-01' },
        { status: 'done', results_json: SCAN_OK, created_at: '2024-01-02' },
      ],
    });
    for (const dot of comp.globalTrendDots) {
      expect(typeof dot.cx).toBe('number');
      expect(typeof dot.cy).toBe('number');
    }
  });
});

describe('DashboardComponent — globalTrend / globalTrendAnnotation / globalTrendIsStable', () => {
  it('globalTrend est null si aucun site', () => {
    expect(make().globalTrend).toBeNull();
  });

  it('globalTrend est null si un seul scan par site', () => {
    const comp = makeWithScans({
      1: [{ status: 'done', results_json: SCAN_OK, created_at: '2024-01-01' }],
    });
    expect(comp.globalTrend).toBeNull();
  });

  it('globalTrend = 0 si deux scans identiques', () => {
    const comp = makeWithScans({
      1: [
        { status: 'done', results_json: SCAN_OK, created_at: '2024-01-01' },
        { status: 'done', results_json: SCAN_OK, created_at: '2024-01-02' },
      ],
    });
    expect(comp.globalTrend).toBe(0);
  });

  it('globalTrendIsStable = true si delta = 0', () => {
    const comp = makeWithScans({
      1: [
        { status: 'done', results_json: SCAN_OK, created_at: '2024-01-01' },
        { status: 'done', results_json: SCAN_OK, created_at: '2024-01-02' },
      ],
    });
    expect(comp.globalTrendIsStable).toBe(true);
  });

  it('globalTrendIsStable = false si delta > 1', () => {
    const comp = makeWithScans({
      1: [
        { status: 'done', results_json: SCAN_OK, created_at: '2024-01-01' },
        { status: 'done', results_json: SCAN_CRITICAL, created_at: '2024-01-02' },
      ],
    });
    expect(comp.globalTrendIsStable).toBe(false);
  });

  it('globalTrendAnnotation contient le score si averageScore non null', () => {
    const comp = makeWithScans({
      1: [{ status: 'done', results_json: SCAN_OK, created_at: '2024-01-01' }],
    });
    expect(comp.globalTrendAnnotation).toContain('/100');
  });

  it('globalTrendAnnotation contient +X pts pour tendance positive', () => {
    // Most recent scan (index 0) is OK, previous scan (index 1) is CRITICAL → positive delta
    const comp = makeWithScans({
      1: [
        { status: 'done', results_json: SCAN_OK, created_at: '2024-01-02' },
        { status: 'done', results_json: SCAN_CRITICAL, created_at: '2024-01-01' },
      ],
    });
    const annotation = comp.globalTrendAnnotation ?? '';
    expect(annotation).toContain('+');
  });
});

describe('DashboardComponent — criticalCount / warningCount / okCount', () => {
  it('criticalCount = 0 si aucun site critique', () => {
    const comp = makeWithScans({
      1: [
        { status: 'done', results_json: SCAN_OK, overall_status: 'OK', created_at: '2024-01-01' },
      ],
    });
    expect(comp.criticalCount).toBe(0);
  });

  it('criticalCount = 1 si un site CRITICAL', () => {
    const comp = makeWithScans({
      1: [
        {
          status: 'done',
          results_json: SCAN_CRITICAL,
          overall_status: 'CRITICAL',
          created_at: '2024-01-01',
        },
      ],
    });
    expect(comp.criticalCount).toBe(1);
  });

  it('okCount = 1 si un site OK', () => {
    const comp = makeWithScans({
      1: [
        { status: 'done', results_json: SCAN_OK, overall_status: 'OK', created_at: '2024-01-01' },
      ],
    });
    expect(comp.okCount).toBe(1);
  });

  it('warningCount = 1 si un site WARNING', () => {
    const comp = makeWithScans({
      1: [
        {
          status: 'done',
          results_json: SCAN_OK,
          overall_status: 'WARNING',
          created_at: '2024-01-01',
        },
      ],
    });
    expect(comp.warningCount).toBe(1);
  });
});

// ── Helper: pose overall_status sur les items (badges + comptages) ──────────
function makeWithBadge(siteId: number, items: any[]): DashboardComponent {
  const comp = make();
  (comp as any).scansMap = signal({
    [siteId]: { items, total: items.length, page: 1, per_page: 10, pages: 1 },
  });
  return comp;
}

describe('DashboardComponent — scanFrequency()', () => {
  it('retourne une chaîne', () => {
    expect(typeof make().scanFrequency(7)).toBe('string');
  });
  it('gère 1 jour', () => {
    expect(make().scanFrequency(1).length).toBeGreaterThan(0);
  });
});

describe('DashboardComponent — formatPrice()', () => {
  it('formate des centimes en euros', () => {
    const p = make().formatPrice(1000);
    expect(p).toContain('10');
    expect(p).toContain('€');
  });
  it('gère 0', () => {
    expect(make().formatPrice(0)).toContain('0');
  });
  it('gère les décimales', () => {
    expect(make().formatPrice(1999)).toContain('19');
  });
});

describe('DashboardComponent — getScans() (filtres)', () => {
  const items = [
    { status: 'done' },
    { status: 'running' },
    { status: 'pending' },
    { status: 'error' },
  ];
  function comp(filter: string): DashboardComponent {
    const c = make();
    (c as any).scansMap = signal({ 1: { items } });
    (c as any).scanFilter = signal(filter);
    return c;
  }
  it('all retourne tous les scans', () => {
    expect(comp('all').getScans(1)).toHaveLength(4);
  });
  it('done ne retourne que les done', () => {
    const r = comp('done').getScans(1);
    expect(r).toHaveLength(1);
    expect(r[0].status).toBe('done');
  });
  it('running retourne pending + running', () => {
    expect(comp('running').getScans(1)).toHaveLength(2);
  });
  it('error ne retourne que les error', () => {
    const r = comp('error').getScans(1);
    expect(r).toHaveLength(1);
    expect(r[0].status).toBe('error');
  });
  it('retourne vide si le site est inconnu', () => {
    expect(comp('all').getScans(999)).toHaveLength(0);
  });
});

describe('DashboardComponent — getters de pagination et état par site', () => {
  function comp(): DashboardComponent {
    const c = make();
    (c as any).scansMap = signal({
      1: { items: [{ status: 'done', overall_status: 'OK' }], total: 42, page: 3, per_page: 20 },
    });
    (c as any).loadingScans = signal({ 1: true });
    (c as any).triggeringScans = signal({ 1: true });
    return c;
  }
  it('getTotal retourne le total', () => expect(comp().getTotal(1)).toBe(42));
  it('getTotal retourne 0 si inconnu', () => expect(comp().getTotal(9)).toBe(0));
  it('getPerPage retourne per_page', () => expect(comp().getPerPage(1)).toBe(20));
  it('getPerPage retourne 10 par défaut', () => expect(comp().getPerPage(9)).toBe(10));
  it('getCurrentPage retourne page - 1', () => expect(comp().getCurrentPage(1)).toBe(2));
  it('getCurrentPage retourne 0 par défaut', () => expect(comp().getCurrentPage(9)).toBe(0));
  it('isLoadingScans reflète la map', () => expect(comp().isLoadingScans(1)).toBe(true));
  it('isLoadingScans false si absent', () => expect(comp().isLoadingScans(9)).toBe(false));
  it('isTriggeringScans reflète la map', () => expect(comp().isTriggeringScans(1)).toBe(true));
  it('isTriggeringScans false si absent', () => expect(comp().isTriggeringScans(9)).toBe(false));
});

describe('DashboardComponent — hasActiveScans() / lastScanStatus()', () => {
  it('hasActiveScans true si un scan running', () => {
    const c = makeWithBadge(1, [{ status: 'running' }]);
    expect(c.hasActiveScans(1)).toBe(true);
  });
  it('hasActiveScans true si un scan pending', () => {
    const c = makeWithBadge(1, [{ status: 'pending' }]);
    expect(c.hasActiveScans(1)).toBe(true);
  });
  it('hasActiveScans false si tout est done', () => {
    const c = makeWithBadge(1, [{ status: 'done' }]);
    expect(c.hasActiveScans(1)).toBe(false);
  });
  it('lastScanStatus retourne le overall_status du premier item', () => {
    const c = makeWithBadge(1, [{ status: 'done', overall_status: 'WARNING' }]);
    expect(c.lastScanStatus(1)).toBe('WARNING');
  });
  it('lastScanStatus retourne null si aucun scan', () => {
    const c = makeWithBadge(1, []);
    expect(c.lastScanStatus(1)).toBeNull();
  });
});

describe('DashboardComponent — siteBadgeClass()', () => {
  it('bleu si scan actif', () => {
    const c = makeWithBadge(1, [{ status: 'running' }]);
    expect(c.siteBadgeClass(1)).toContain('blue');
  });
  it('vert si OK', () => {
    const c = makeWithBadge(1, [{ status: 'done', overall_status: 'OK' }]);
    expect(c.siteBadgeClass(1)).toContain('green');
  });
  it('jaune si WARNING', () => {
    const c = makeWithBadge(1, [{ status: 'done', overall_status: 'WARNING' }]);
    expect(c.siteBadgeClass(1)).toContain('yellow');
  });
  it('rouge si CRITICAL', () => {
    const c = makeWithBadge(1, [{ status: 'done', overall_status: 'CRITICAL' }]);
    expect(c.siteBadgeClass(1)).toContain('red');
  });
  it('gris par défaut', () => {
    const c = makeWithBadge(1, []);
    expect(c.siteBadgeClass(1)).toContain('gray');
  });
});

describe('DashboardComponent — siteBadgeLabel() / siteBadgeIcon()', () => {
  it('label "En cours..." si scan actif', () => {
    const c = makeWithBadge(1, [{ status: 'pending' }]);
    expect(c.siteBadgeLabel(1)).toBe('En cours...');
  });
  it('label = overall_status sinon', () => {
    const c = makeWithBadge(1, [{ status: 'done', overall_status: 'OK' }]);
    expect(c.siteBadgeLabel(1)).toBe('OK');
  });
  it('label "Aucun scan" si vide', () => {
    const c = makeWithBadge(1, []);
    expect(c.siteBadgeLabel(1)).toBe('Aucun scan');
  });
  it('icône sync si scan actif', () => {
    const c = makeWithBadge(1, [{ status: 'running' }]);
    expect(c.siteBadgeIcon(1)).toBe('sync');
  });
  it('icône verified_user si OK', () => {
    const c = makeWithBadge(1, [{ status: 'done', overall_status: 'OK' }]);
    expect(c.siteBadgeIcon(1)).toBe('verified_user');
  });
  it('icône warning si WARNING', () => {
    const c = makeWithBadge(1, [{ status: 'done', overall_status: 'WARNING' }]);
    expect(c.siteBadgeIcon(1)).toBe('warning');
  });
  it('icône gpp_bad si CRITICAL', () => {
    const c = makeWithBadge(1, [{ status: 'done', overall_status: 'CRITICAL' }]);
    expect(c.siteBadgeIcon(1)).toBe('gpp_bad');
  });
  it('icône help_outline par défaut', () => {
    const c = makeWithBadge(1, []);
    expect(c.siteBadgeIcon(1)).toBe('help_outline');
  });
});

describe('DashboardComponent — getScanScore() / getLastScore() / getPrevScore() / getTrend()', () => {
  it('getScanScore = 100 pour un scan OK complet', () => {
    expect(make().getScanScore({ results_json: SCAN_OK } as any)).toBe(100);
  });
  it('getScanScore = null si results_json absent', () => {
    expect(make().getScanScore({ results_json: null } as any)).toBeNull();
  });
  it('getLastScore prend le premier scan done avec score', () => {
    const c = makeWithScans({
      1: [
        { status: 'running', results_json: '', created_at: '2024-01-03' },
        { status: 'done', results_json: SCAN_OK, created_at: '2024-01-02' },
      ],
    });
    expect(c.getLastScore(1)).toBe(100);
  });
  it('getLastScore = null si aucun scan done', () => {
    const c = makeWithScans({ 1: [{ status: 'running', results_json: '', created_at: '' }] });
    expect(c.getLastScore(1)).toBeNull();
  });
  it('getPrevScore = null si moins de 2 scans done', () => {
    const c = makeWithScans({
      1: [{ status: 'done', results_json: SCAN_OK, created_at: '2024-01-01' }],
    });
    expect(c.getPrevScore(1)).toBeNull();
  });
  it('getPrevScore prend le 2e scan done', () => {
    const c = makeWithScans({
      1: [
        { status: 'done', results_json: SCAN_OK, created_at: '2024-01-02' },
        { status: 'done', results_json: SCAN_CRITICAL, created_at: '2024-01-01' },
      ],
    });
    expect(c.getPrevScore(1)).toBe(0);
  });
  it('getTrend = last - prev', () => {
    const c = makeWithScans({
      1: [
        { status: 'done', results_json: SCAN_OK, created_at: '2024-01-02' },
        { status: 'done', results_json: SCAN_CRITICAL, created_at: '2024-01-01' },
      ],
    });
    expect(c.getTrend(1)).toBe(100);
  });
  it('getTrend = null si un seul scan', () => {
    const c = makeWithScans({
      1: [{ status: 'done', results_json: SCAN_OK, created_at: '2024-01-01' }],
    });
    expect(c.getTrend(1)).toBeNull();
  });
});

describe('DashboardComponent — getSslDaysRemaining()', () => {
  const SCAN_SSL = JSON.stringify({ ssl: { status: 'OK', days_remaining: 42 } });
  it('retourne le nombre de jours restants', () => {
    const c = makeWithScans({
      1: [{ status: 'done', results_json: SCAN_SSL, created_at: '2024-01-01' }],
    });
    expect(c.getSslDaysRemaining(1)).toBe(42);
  });
  it('retourne null si aucun scan done', () => {
    const c = makeWithScans({ 1: [{ status: 'running', results_json: '', created_at: '' }] });
    expect(c.getSslDaysRemaining(1)).toBeNull();
  });
  it('retourne null si JSON invalide', () => {
    const c = makeWithScans({
      1: [{ status: 'done', results_json: '{invalide', created_at: '2024-01-01' }],
    });
    expect(c.getSslDaysRemaining(1)).toBeNull();
  });
  it('retourne null si pas de bloc ssl', () => {
    const c = makeWithScans({
      1: [{ status: 'done', results_json: '{}', created_at: '2024-01-01' }],
    });
    expect(c.getSslDaysRemaining(1)).toBeNull();
  });
});

describe('DashboardComponent — averageScore / totalScans', () => {
  it('averageScore = null si aucun score', () => {
    expect(make().averageScore).toBeNull();
  });
  it('averageScore moyenne des derniers scores', () => {
    const c = makeWithScans({
      1: [{ status: 'done', results_json: SCAN_OK, created_at: '2024-01-01' }],
      2: [{ status: 'done', results_json: SCAN_CRITICAL, created_at: '2024-01-01' }],
    });
    expect(c.averageScore).toBe(50);
  });
  it('totalScans somme des totaux', () => {
    const c = make();
    (c as any).scansMap = signal({ 1: { total: 5 }, 2: { total: 3 } });
    expect(c.totalScans).toBe(8);
  });
  it('totalScans = 0 si vide', () => {
    expect(make().totalScans).toBe(0);
  });
});

describe('DashboardComponent — maxSites / effectiveMaxSites / canAddSite', () => {
  function comp(maxSites: number, extra: number, nbSites: number): DashboardComponent {
    const c = make();
    (c as any).subscription = signal({ plan: { max_sites: maxSites }, extra_sites: extra });
    (c as any).sites = signal(Array.from({ length: nbSites }, (_, i) => ({ id: i })));
    return c;
  }
  it('maxSites = max_sites du plan', () => expect(comp(3, 2, 0).maxSites).toBe(3));
  it('maxSites = 0 sans abonnement', () => {
    const c = make();
    (c as any).subscription = signal(null);
    expect(c.maxSites).toBe(0);
  });
  it('effectiveMaxSites = max_sites + extra_sites', () =>
    expect(comp(3, 2, 0).effectiveMaxSites).toBe(5));
  it('canAddSite = true si sous la limite', () => expect(comp(3, 2, 4).canAddSite).toBe(true));
  it('canAddSite = false si à la limite', () => expect(comp(3, 2, 5).canAddSite).toBe(false));
});

describe('DashboardComponent — build* helpers', () => {
  const SCAN_SSL = JSON.stringify({ ssl: { status: 'OK', days_remaining: 30 } });
  function comp(): DashboardComponent {
    return makeWithScans({
      1: [
        { status: 'done', results_json: SCAN_SSL, overall_status: 'OK', created_at: '2024-01-01' },
      ],
    });
  }
  it('buildLastScores mappe siteId -> score', () => {
    expect(comp().buildLastScores()[1]).toBe(100);
  });
  it('buildTrends mappe siteId -> trend (null si 1 scan)', () => {
    expect(comp().buildTrends()[1]).toBeNull();
  });
  it('buildSslDays mappe siteId -> jours SSL', () => {
    expect(comp().buildSslDays()[1]).toBe(30);
  });
  it('buildActiveScansMap mappe siteId -> booléen', () => {
    expect(comp().buildActiveScansMap()[1]).toBe(false);
  });
  it('buildLastScanStatuses mappe siteId -> statut', () => {
    expect(comp().buildLastScanStatuses()[1]).toBe('OK');
  });
});

describe('DashboardComponent — toggles', () => {
  it('toggleAnalytics inverse analyticsOpen', () => {
    const c = make();
    (c as any).analyticsOpen = signal(true);
    c.toggleAnalytics();
    expect(c.analyticsOpen()).toBe(false);
    c.toggleAnalytics();
    expect(c.analyticsOpen()).toBe(true);
  });
  it('toggleNotifPanel inverse showNotifPanel et stoppe la propagation', () => {
    const c = make();
    (c as any).showNotifPanel = signal(false);
    const event = { stopPropagation: vi.fn() } as any;
    c.toggleNotifPanel(event);
    expect(c.showNotifPanel()).toBe(true);
    expect(event.stopPropagation).toHaveBeenCalled();
  });
});

describe('DashboardComponent — autoPrependHttps()', () => {
  function ctrl(value: string) {
    return { value, setValue: vi.fn(), markAsTouched: vi.fn() };
  }
  it('préfixe https:// si absent', () => {
    const c = make();
    const url = ctrl('example.com');
    (c as any).siteForm = { controls: { url } };
    c.autoPrependHttps();
    expect(url.setValue).toHaveBeenCalledWith('https://example.com', { emitEvent: true });
    expect(url.markAsTouched).toHaveBeenCalled();
  });
  it('ne touche pas si déjà https://', () => {
    const c = make();
    const url = ctrl('https://example.com');
    (c as any).siteForm = { controls: { url } };
    c.autoPrependHttps();
    expect(url.setValue).not.toHaveBeenCalled();
  });
  it('ne touche pas si déjà http://', () => {
    const c = make();
    const url = ctrl('http://example.com');
    (c as any).siteForm = { controls: { url } };
    c.autoPrependHttps();
    expect(url.setValue).not.toHaveBeenCalled();
  });
  it('ne fait rien si vide', () => {
    const c = make();
    const url = ctrl('   ');
    (c as any).siteForm = { controls: { url } };
    c.autoPrependHttps();
    expect(url.setValue).not.toHaveBeenCalled();
  });
});

describe('DashboardComponent — logout()', () => {
  it('délègue à authService.logout', () => {
    const c = make();
    (c as any).authService = { logout: vi.fn() };
    c.logout();
    expect((c as any).authService.logout).toHaveBeenCalled();
  });
});

describe('DashboardComponent — loadNotifications()', () => {
  it('met à jour notifications et unreadCount', () => {
    const c = make();
    (c as any).notifications = signal([]);
    (c as any).unreadCount = signal(0);
    (c as any).cyberscan = {
      getNotifications: vi.fn().mockReturnValue(of({ items: [{ id: 1 }], unread_count: 3 })),
    };
    c.loadNotifications();
    expect(c.notifications()).toHaveLength(1);
    expect(c.unreadCount()).toBe(3);
  });
});

describe('DashboardComponent — handleNotifClick()', () => {
  it('marque comme lue si non lue et décrémente le compteur', () => {
    const c = make();
    const notif = { id: 1, read: false, link: null } as any;
    (c as any).notifications = signal([notif]);
    (c as any).unreadCount = signal(2);
    (c as any).cyberscan = {
      markNotificationRead: vi.fn().mockReturnValue(of({ id: 1, read: true })),
    };
    c.handleNotifClick(notif);
    expect((c as any).cyberscan.markNotificationRead).toHaveBeenCalledWith(1);
    expect(c.unreadCount()).toBe(1);
    expect(c.notifications()[0].read).toBe(true);
  });
  it('ne marque pas si déjà lue mais navigue si lien', () => {
    const c = make();
    const notif = { id: 1, read: true, link: '/cible' } as any;
    (c as any).cyberscan = { markNotificationRead: vi.fn() };
    (c as any).router = { navigateByUrl: vi.fn() };
    (c as any).showNotifPanel = signal(true);
    c.handleNotifClick(notif);
    expect((c as any).cyberscan.markNotificationRead).not.toHaveBeenCalled();
    expect((c as any).router.navigateByUrl).toHaveBeenCalledWith('/cible');
    expect(c.showNotifPanel()).toBe(false);
  });
});

describe('DashboardComponent — markAllRead()', () => {
  it('passe toutes les notifs en lues et remet le compteur à 0', () => {
    const c = make();
    (c as any).notifications = signal([
      { id: 1, read: false },
      { id: 2, read: false },
    ]);
    (c as any).unreadCount = signal(2);
    (c as any).cyberscan = { markAllNotificationsRead: vi.fn().mockReturnValue(of({})) };
    c.markAllRead();
    expect(c.notifications().every(n => n.read)).toBe(true);
    expect(c.unreadCount()).toBe(0);
  });
});

describe('DashboardComponent — dismissNotif()', () => {
  it('retire la notif et décrémente si elle était non lue', () => {
    const c = make();
    (c as any).notifications = signal([{ id: 1, read: false }]);
    (c as any).unreadCount = signal(1);
    (c as any).cyberscan = { deleteNotification: vi.fn().mockReturnValue(of({})) };
    const event = { stopPropagation: vi.fn() } as any;
    c.dismissNotif(event, 1);
    expect(event.stopPropagation).toHaveBeenCalled();
    expect(c.notifications()).toHaveLength(0);
    expect(c.unreadCount()).toBe(0);
  });
  it('ne décrémente pas si la notif était déjà lue', () => {
    const c = make();
    (c as any).notifications = signal([{ id: 1, read: true }]);
    (c as any).unreadCount = signal(0);
    (c as any).cyberscan = { deleteNotification: vi.fn().mockReturnValue(of({})) };
    c.dismissNotif({ stopPropagation: vi.fn() } as any, 1);
    expect(c.notifications()).toHaveLength(0);
    expect(c.unreadCount()).toBe(0);
  });
});

describe('DashboardComponent — loadScans()', () => {
  it('remplit scansMap et pageMap, désactive le loading', () => {
    const c = make();
    (c as any).loadingScans = signal({});
    (c as any).pageMap = signal({});
    (c as any).scansMap = signal({});
    (c as any).pollingMap = {};
    const data = { items: [], total: 0, page: 1, per_page: 10, pages: 0 };
    (c as any).cyberscan = { getSiteScans: vi.fn().mockReturnValue(of(data)) };
    c.loadScans(1, 1);
    expect((c as any).cyberscan.getSiteScans).toHaveBeenCalledWith(1, 1);
    expect(c.scansMap()[1]).toEqual(data);
    expect(c.loadingScans()[1]).toBe(false);
    expect(c.pageMap()[1]).toBe(1);
  });
});

describe('DashboardComponent — onPageChange()', () => {
  it('appelle loadScans avec pageIndex + 1', () => {
    const c = make();
    (c as any).loadScans = vi.fn();
    c.onPageChange(5, { pageIndex: 2 } as any);
    expect((c as any).loadScans).toHaveBeenCalledWith(5, 3);
  });
});

describe('DashboardComponent — addSite()', () => {
  it('ne fait rien si le formulaire est invalide', () => {
    const c = make();
    (c as any).siteForm = { invalid: true };
    (c as any).cyberscan = { createSite: vi.fn() };
    c.addSite();
    expect((c as any).cyberscan.createSite).not.toHaveBeenCalled();
  });
  it('ajoute le site, réinitialise et charge les scans', () => {
    const c = make();
    (c as any).siteForm = {
      invalid: false,
      getRawValue: () => ({ url: 'https://x.com', name: 'x' }),
      reset: vi.fn(),
    };
    (c as any).sites = signal([]);
    (c as any).addingSite = signal(false);
    (c as any).showAddForm = signal(true);
    (c as any).snack = { open: vi.fn() };
    (c as any).cyberscan = { createSite: vi.fn().mockReturnValue(of({ id: 7, name: 'x' })) };
    (c as any).loadScans = vi.fn();
    c.addSite();
    expect(c.sites()).toHaveLength(1);
    expect(c.addingSite()).toBe(false);
    expect(c.showAddForm()).toBe(false);
    expect((c as any).snack.open).toHaveBeenCalled();
    expect((c as any).loadScans).toHaveBeenCalledWith(7, 1);
  });
  it('affiche une erreur en cas d’échec', () => {
    const c = make();
    (c as any).siteForm = {
      invalid: false,
      getRawValue: () => ({ url: 'https://x.com', name: 'x' }),
      reset: vi.fn(),
    };
    (c as any).sites = signal([]);
    (c as any).addingSite = signal(true);
    (c as any).showAddForm = signal(true);
    (c as any).snack = { open: vi.fn() };
    (c as any).cyberscan = {
      createSite: vi.fn().mockReturnValue(throwError(() => ({ error: { detail: 'boom' } }))),
    };
    c.addSite();
    expect(c.addingSite()).toBe(false);
    expect((c as any).snack.open).toHaveBeenCalledWith('boom', 'Fermer', expect.anything());
  });
});

describe('DashboardComponent — triggerScan()', () => {
  it('lance le scan, notifie et relance le polling', () => {
    const c = make();
    (c as any).triggeringScans = signal({});
    (c as any).snack = { open: vi.fn() };
    (c as any).cyberscan = { triggerScan: vi.fn().mockReturnValue(of({})) };
    (c as any).loadScans = vi.fn();
    (c as any).forceStartPolling = vi.fn();
    c.triggerScan(3);
    expect(c.triggeringScans()[3]).toBe(false);
    expect((c as any).loadScans).toHaveBeenCalledWith(3, 1);
    expect((c as any).forceStartPolling).toHaveBeenCalledWith(3);
    expect((c as any).snack.open).toHaveBeenCalled();
  });
  it('affiche une erreur en cas d’échec', () => {
    const c = make();
    (c as any).triggeringScans = signal({ 3: true });
    (c as any).snack = { open: vi.fn() };
    (c as any).cyberscan = {
      triggerScan: vi.fn().mockReturnValue(throwError(() => ({ error: {} }))),
    };
    c.triggerScan(3);
    expect(c.triggeringScans()[3]).toBe(false);
    expect((c as any).snack.open).toHaveBeenCalledWith(
      'Erreur lors du lancement',
      'Fermer',
      expect.anything()
    );
  });
});

describe('DashboardComponent — openPlansModal()', () => {
  it('ouvre la modale et charge les plans si absents', () => {
    const c = make();
    (c as any).showPlansModal = signal(false);
    (c as any).plans = signal([]);
    (c as any).cyberscan = { getPlans: vi.fn().mockReturnValue(of([{ id: 1 }])) };
    c.openPlansModal();
    expect(c.showPlansModal()).toBe(true);
    expect(c.plans()).toHaveLength(1);
  });
  it('ne recharge pas les plans déjà présents', () => {
    const c = make();
    (c as any).showPlansModal = signal(false);
    (c as any).plans = signal([{ id: 1 }]);
    (c as any).cyberscan = { getPlans: vi.fn() };
    c.openPlansModal();
    expect((c as any).cyberscan.getPlans).not.toHaveBeenCalled();
  });
});

describe('DashboardComponent — selectPlan()', () => {
  it('invalide le cache et navigue vers une URL relative', () => {
    const c = make();
    (c as any).checkoutLoading = signal(null);
    (c as any).router = { navigateByUrl: vi.fn() };
    (c as any).cyberscan = {
      invalidateSubscriptionCache: vi.fn(),
      createCheckout: vi.fn().mockReturnValue(of({ checkout_url: '/paiement' })),
    };
    c.selectPlan({ id: 2 } as any);
    expect(c.checkoutLoading()).toBe(2);
    expect((c as any).cyberscan.invalidateSubscriptionCache).toHaveBeenCalled();
    expect((c as any).router.navigateByUrl).toHaveBeenCalledWith('/paiement');
  });
  it('réinitialise checkoutLoading en cas d’erreur', () => {
    const c = make();
    (c as any).checkoutLoading = signal(null);
    (c as any).cyberscan = {
      invalidateSubscriptionCache: vi.fn(),
      createCheckout: vi.fn().mockReturnValue(throwError(() => new Error('x'))),
    };
    c.selectPlan({ id: 2 } as any);
    expect(c.checkoutLoading()).toBeNull();
  });
});

describe('DashboardComponent — purchaseExtraSites()', () => {
  it('navigue vers une URL relative après achat', () => {
    const c = make();
    (c as any).buyingExtraSites = signal(false);
    (c as any).router = { navigateByUrl: vi.fn() };
    (c as any).cyberscan = {
      purchaseExtraSites: vi.fn().mockReturnValue(of({ checkout_url: '/extra' })),
    };
    c.purchaseExtraSites();
    expect(c.buyingExtraSites()).toBe(false);
    expect((c as any).router.navigateByUrl).toHaveBeenCalledWith('/extra');
  });
  it('affiche une erreur en cas d’échec', () => {
    const c = make();
    (c as any).buyingExtraSites = signal(true);
    (c as any).snack = { open: vi.fn() };
    (c as any).cyberscan = {
      purchaseExtraSites: vi.fn().mockReturnValue(throwError(() => new Error('x'))),
    };
    c.purchaseExtraSites();
    expect(c.buyingExtraSites()).toBe(false);
    expect((c as any).snack.open).toHaveBeenCalled();
  });
});

describe('DashboardComponent — confirmDeleteSite()', () => {
  it('supprime le site si la confirmation est acceptée', () => {
    const c = make();
    (c as any).sites = signal([{ id: 1, name: 'a' }]);
    (c as any).snack = { open: vi.fn() };
    (c as any).dialog = { open: vi.fn().mockReturnValue({ afterClosed: () => of(true) }) };
    (c as any).cyberscan = { deleteSite: vi.fn().mockReturnValue(of({})) };
    c.confirmDeleteSite({ id: 1, name: 'a' } as any);
    expect((c as any).cyberscan.deleteSite).toHaveBeenCalledWith(1);
    expect(c.sites()).toHaveLength(0);
  });
  it('ne supprime rien si la confirmation est refusée', () => {
    const c = make();
    (c as any).sites = signal([{ id: 1, name: 'a' }]);
    (c as any).dialog = { open: vi.fn().mockReturnValue({ afterClosed: () => of(false) }) };
    (c as any).cyberscan = { deleteSite: vi.fn() };
    c.confirmDeleteSite({ id: 1, name: 'a' } as any);
    expect((c as any).cyberscan.deleteSite).not.toHaveBeenCalled();
    expect(c.sites()).toHaveLength(1);
  });
});

describe('DashboardComponent — downloadPdf()', () => {
  it('déclenche le téléchargement du blob', () => {
    const c = make();
    (c as any).snack = { open: vi.fn() };
    (c as any).cyberscan = {
      downloadPdfBlob: vi.fn().mockReturnValue(of(new Blob(['data']))),
    };
    const createSpy = vi.fn(() => 'blob:x');
    const revokeSpy = vi.fn();
    (globalThis as any).URL.createObjectURL = createSpy;
    (globalThis as any).URL.revokeObjectURL = revokeSpy;
    c.downloadPdf(9);
    expect((c as any).cyberscan.downloadPdfBlob).toHaveBeenCalledWith(9);
    expect(createSpy).toHaveBeenCalled();
    expect(revokeSpy).toHaveBeenCalled();
  });
  it('affiche une erreur en cas d’échec', () => {
    const c = make();
    (c as any).snack = { open: vi.fn() };
    (c as any).cyberscan = {
      downloadPdfBlob: vi.fn().mockReturnValue(throwError(() => new Error('x'))),
    };
    c.downloadPdf(9);
    expect((c as any).snack.open).toHaveBeenCalledWith(
      'Erreur lors du téléchargement du PDF',
      'Fermer',
      expect.anything()
    );
  });
});
