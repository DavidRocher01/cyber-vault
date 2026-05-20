import { describe, it, expect } from 'vitest';
import { signal } from '@angular/core';
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

function makeWithScan(resultsJson: string | null): ScanDetailComponent {
  const comp = Object.create(ScanDetailComponent.prototype) as ScanDetailComponent;
  (comp as any).scan = signal<any>(
    resultsJson !== null ? { results_json: resultsJson, status: 'done' } : null
  );
  return comp;
}

const TIER2_SCAN = JSON.stringify({ _meta: { tier: 2 }, ssl: { status: 'OK' }, headers: { status: 'OK' } });
const TIER4_SCAN = JSON.stringify({
  _meta: { tier: 4 },
  ssl: { status: 'OK' }, headers: { status: 'OK' }, email: { status: 'OK' },
  cookies: { status: 'OK' }, cors: { status: 'OK' }, ip: { status: 'OK' },
  dns: { status: 'OK' }, cms: { status: 'OK' }, waf: { status: 'OK' },
  tech: { status: 'OK' }, tls: { status: 'OK' }, takeover: { status: 'OK' },
  threat_intel: { status: 'OK' }, http_methods: { status: 'OK' },
  open_redirect: { status: 'OK' }, clickjacking: { status: 'OK' },
  directory_listing: { status: 'OK' }, robots: { status: 'OK' }, jwt: { status: 'OK' },
});

describe('ScanDetailComponent — scannedDomain', () => {
  it('retourne null si scan null', () => {
    expect(makeWithScan(null).scannedDomain).toBeNull();
  });
  it('retourne null si _meta absent', () => {
    expect(makeWithScan('{"ssl":{"status":"OK"}}').scannedDomain).toBeNull();
  });
  it('retourne l\'URL depuis _meta.url', () => {
    const json = JSON.stringify({ _meta: { url: 'https://example.com' } });
    expect(makeWithScan(json).scannedDomain).toBe('https://example.com');
  });
  it('retourne null si JSON invalide', () => {
    expect(makeWithScan('not-json').scannedDomain).toBeNull();
  });
  it('retourne null si _meta.url absent', () => {
    const json = JSON.stringify({ _meta: { tier: 2 } });
    expect(makeWithScan(json).scannedDomain).toBeNull();
  });
});

describe('ScanDetailComponent — scanTier', () => {
  it('retourne 2 si scan null', () => {
    expect(makeWithScan(null).scanTier).toBe(2);
  });
  it('retourne 2 si _meta absent', () => {
    expect(makeWithScan('{"ssl":{"status":"OK"}}').scanTier).toBe(2);
  });
  it('retourne le tier depuis _meta', () => {
    const json = JSON.stringify({ _meta: { tier: 3 }, ssl: { status: 'OK' } });
    expect(makeWithScan(json).scanTier).toBe(3);
  });
  it('retourne 2 si JSON invalide', () => {
    expect(makeWithScan('not-json').scanTier).toBe(2);
  });
});

describe('ScanDetailComponent — getProDescription()', () => {
  it('retourne la description pour tech', () => {
    expect(make().getProDescription('tech')).toBeTruthy();
  });
  it('retourne la description pour jwt', () => {
    expect(make().getProDescription('jwt')).toBeTruthy();
  });
  it('retourne chaîne vide pour clé inconnue', () => {
    expect(make().getProDescription('ssl')).toBe('');
    expect(make().getProDescription('unknown_key')).toBe('');
  });
  it('couvre tous les modules verrouillés', () => {
    const lockedKeys = ['tech', 'tls', 'takeover', 'threat_intel', 'http_methods',
                        'open_redirect', 'clickjacking', 'directory_listing', 'robots', 'jwt'];
    for (const key of lockedKeys) {
      expect(make().getProDescription(key), `description manquante pour ${key}`).toBeTruthy();
    }
  });
});

describe('ScanDetailComponent — lockedFindings', () => {
  it('retourne vide si scan null', () => {
    expect(makeWithScan(null).lockedFindings).toHaveLength(0);
  });
  it('retourne les modules skipped (tier 3+) pour un scan tier 2', () => {
    const locked = makeWithScan(TIER2_SCAN).lockedFindings;
    expect(locked.length).toBeGreaterThan(0);
    expect(locked.every(f => f.skipped)).toBe(true);
    expect(locked.every(f => f.minTier >= 3)).toBe(true);
  });
  it('retourne vide pour un scan tier 4 complet', () => {
    expect(makeWithScan(TIER4_SCAN).lockedFindings).toHaveLength(0);
  });
  it('inclut les modules Pro (minTier=3) et Business (minTier=4) pour tier 2', () => {
    const locked = makeWithScan(TIER2_SCAN).lockedFindings;
    expect(locked.some(f => f.minTier === 3)).toBe(true);
    expect(locked.some(f => f.minTier === 4)).toBe(true);
  });
});

function makeWithStatus(overallStatus: string): ScanDetailComponent {
  const comp = Object.create(ScanDetailComponent.prototype) as ScanDetailComponent;
  (comp as any).scan = signal<any>({ results_json: null, status: 'done', overall_status: overallStatus });
  return comp;
}

describe('ScanDetailComponent — CTA getters (ctaWrapperClass / ctaTitle / ctaButtonClass)', () => {
  it('ctaWrapperClass contient border-red pour CRITICAL', () => {
    expect(makeWithStatus('CRITICAL').ctaWrapperClass).toContain('border-red');
  });
  it('ctaWrapperClass contient border-yellow pour WARNING', () => {
    expect(makeWithStatus('WARNING').ctaWrapperClass).toContain('border-yellow');
  });
  it('ctaWrapperClass contient border-cyan par défaut', () => {
    expect(makeWithStatus('OK').ctaWrapperClass).toContain('border-cyan');
  });

  it('ctaTitle mentionne vulnérabilités critiques pour CRITICAL', () => {
    expect(makeWithStatus('CRITICAL').ctaTitle).toContain('critiques');
  });
  it('ctaTitle mentionne regard humain pour WARNING', () => {
    expect(makeWithStatus('WARNING').ctaTitle).toContain('humain');
  });
  it('ctaTitle mentionne expert par défaut', () => {
    expect(makeWithStatus('OK').ctaTitle).toContain('expert');
  });

  it('ctaButtonClass contient bg-red pour CRITICAL', () => {
    expect(makeWithStatus('CRITICAL').ctaButtonClass).toContain('bg-red');
  });
  it('ctaButtonClass contient bg-yellow pour WARNING', () => {
    expect(makeWithStatus('WARNING').ctaButtonClass).toContain('bg-yellow');
  });
  it('ctaButtonClass contient bg-cyan par défaut', () => {
    expect(makeWithStatus('OK').ctaButtonClass).toContain('bg-cyan');
  });
});

describe('ScanDetailComponent — criticalCount / warningCount', () => {
  const MIXED_SCAN = JSON.stringify({
    _meta: { tier: 4 },
    ssl:     { status: 'CRITICAL' },
    headers: { status: 'WARNING' },
    email:   { status: 'WARNING' },
    cookies: { status: 'OK' },
    cors:    { status: 'OK' },
    ip:      { status: 'OK' },
    dns:     { status: 'OK' },
    cms:     { status: 'OK' },
    waf:     { status: 'OK' },
    tech:    { status: 'OK' },
    tls:     { status: 'OK' },
    takeover:        { status: 'OK' },
    threat_intel:    { status: 'OK' },
    http_methods:    { status: 'OK' },
    open_redirect:   { status: 'OK' },
    clickjacking:    { status: 'OK' },
    directory_listing: { status: 'OK' },
    robots: { status: 'OK' },
    jwt:    { status: 'OK' },
  });

  it('criticalCount compte les findings CRITICAL', () => {
    expect(makeWithScan(MIXED_SCAN).criticalCount).toBe(1);
  });
  it('warningCount compte les findings WARNING', () => {
    expect(makeWithScan(MIXED_SCAN).warningCount).toBe(2);
  });
  it('criticalCount vaut 0 si scan null', () => {
    expect(makeWithScan(null).criticalCount).toBe(0);
  });
  it('warningCount vaut 0 si scan null', () => {
    expect(makeWithScan(null).warningCount).toBe(0);
  });
});

describe('ScanDetailComponent — duration', () => {
  function makeWithDates(startedAt: string | null, finishedAt: string | null): ScanDetailComponent {
    const comp = Object.create(ScanDetailComponent.prototype) as ScanDetailComponent;
    (comp as any).scan = signal<any>({ results_json: null, status: 'done', started_at: startedAt, finished_at: finishedAt });
    return comp;
  }

  it('retourne "—" si dates absentes', () => {
    expect(makeWithDates(null, null).duration).toBe('—');
  });
  it('retourne "—" si seulement started_at', () => {
    expect(makeWithDates('2024-01-01T10:00:00Z', null).duration).toBe('—');
  });
  it('affiche les secondes pour une durée < 1 min', () => {
    expect(makeWithDates('2024-01-01T10:00:00Z', '2024-01-01T10:00:45Z').duration).toBe('45s');
  });
  it('affiche minutes et secondes pour une durée >= 1 min', () => {
    expect(makeWithDates('2024-01-01T10:00:00Z', '2024-01-01T10:02:15Z').duration).toBe('2m 15s');
  });
});

describe('ScanDetailComponent — toggleFlip()', () => {
  it('ajoute la clé au premier clic', () => {
    const c = make();
    c.flippedCards = new Set();
    c.toggleFlip('ssl');
    expect(c.flippedCards.has('ssl')).toBe(true);
  });

  it('retire la clé au second clic', () => {
    const c = make();
    c.flippedCards = new Set();
    c.toggleFlip('ssl');
    c.toggleFlip('ssl');
    expect(c.flippedCards.has('ssl')).toBe(false);
  });

  it('gère plusieurs cartes indépendamment', () => {
    const c = make();
    c.flippedCards = new Set();
    c.toggleFlip('ssl');
    c.toggleFlip('headers');
    expect(c.flippedCards.has('ssl')).toBe(true);
    expect(c.flippedCards.has('headers')).toBe(true);
    c.toggleFlip('ssl');
    expect(c.flippedCards.has('ssl')).toBe(false);
    expect(c.flippedCards.has('headers')).toBe(true);
  });
});
