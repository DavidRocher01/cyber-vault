import { describe, it, expect, vi } from 'vitest';
import { signal } from '@angular/core';
import { of } from 'rxjs';
import { ScanDetailComponent } from './scan-detail.component';

function make(): ScanDetailComponent {
  return Object.create(ScanDetailComponent.prototype) as ScanDetailComponent;
}

describe('ScanDetailComponent — statusColor()', () => {
  it('retourne vert pour OK', () => expect(make().statusColor('OK')).toContain('green'));
  it('retourne jaune pour WARNING', () =>
    expect(make().statusColor('WARNING')).toContain('yellow'));
  it('retourne rouge pour CRITICAL', () => expect(make().statusColor('CRITICAL')).toContain('red'));
  it('retourne gris par défaut', () => expect(make().statusColor(null)).toContain('gray'));
  it('retourne gris pour une valeur inconnue', () =>
    expect(make().statusColor('unknown')).toContain('gray'));
});

describe('ScanDetailComponent — statusIcon()', () => {
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

describe('ScanDetailComponent — formatDate()', () => {
  it('retourne "—" pour null', () => expect(make().formatDate(null)).toBe('—'));
  it('formate une date ISO', () =>
    expect(make().formatDate('2024-03-15T10:30:00Z')).toContain('2024'));
  it("inclut l'heure", () => expect(make().formatDate('2024-03-15T10:30:00Z')).toMatch(/\d+:\d+/));
});

function makeWithScan(resultsJson: string | null): ScanDetailComponent {
  const comp = Object.create(ScanDetailComponent.prototype) as ScanDetailComponent;
  (comp as any).scan = signal<any>(
    resultsJson !== null ? { results_json: resultsJson, status: 'done' } : null
  );
  return comp;
}

const TIER2_SCAN = JSON.stringify({
  _meta: { tier: 2 },
  ssl: { status: 'OK' },
  headers: { status: 'OK' },
});
const TIER4_SCAN = JSON.stringify({
  _meta: { tier: 4 },
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

describe('ScanDetailComponent — scannedDomain', () => {
  it('retourne null si scan null', () => {
    expect(makeWithScan(null).scannedDomain).toBeNull();
  });
  it('retourne null si _meta absent', () => {
    expect(makeWithScan('{"ssl":{"status":"OK"}}').scannedDomain).toBeNull();
  });
  it("retourne l'URL depuis _meta.url", () => {
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
    const lockedKeys = [
      'tech',
      'tls',
      'takeover',
      'threat_intel',
      'http_methods',
      'open_redirect',
      'clickjacking',
      'directory_listing',
      'robots',
      'jwt',
    ];
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
  (comp as any).scan = signal<any>({
    results_json: null,
    status: 'done',
    overall_status: overallStatus,
  });
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
    ssl: { status: 'CRITICAL' },
    headers: { status: 'WARNING' },
    email: { status: 'WARNING' },
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
    (comp as any).scan = signal<any>({
      results_json: null,
      status: 'done',
      started_at: startedAt,
      finished_at: finishedAt,
    });
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

describe('ScanDetailComponent — CTA getters (ctaIconWrapperClass / ctaIconClass)', () => {
  it('ctaIconWrapperClass contient bg-red pour CRITICAL', () => {
    expect(makeWithStatus('CRITICAL').ctaIconWrapperClass).toContain('bg-red');
  });
  it('ctaIconWrapperClass contient bg-yellow pour WARNING', () => {
    expect(makeWithStatus('WARNING').ctaIconWrapperClass).toContain('bg-yellow');
  });
  it('ctaIconWrapperClass contient bg-cyan par défaut', () => {
    expect(makeWithStatus('OK').ctaIconWrapperClass).toContain('bg-cyan');
  });

  it('ctaIconClass contient text-red pour CRITICAL', () => {
    expect(makeWithStatus('CRITICAL').ctaIconClass).toContain('text-red');
  });
  it('ctaIconClass contient text-yellow pour WARNING', () => {
    expect(makeWithStatus('WARNING').ctaIconClass).toContain('text-yellow');
  });
  it('ctaIconClass contient text-cyan par défaut', () => {
    expect(makeWithStatus('OK').ctaIconClass).toContain('text-cyan');
  });
  it('gère un overall_status inconnu comme défaut', () => {
    expect(makeWithStatus('WEIRD').ctaIconClass).toContain('text-cyan');
    expect(makeWithStatus('WEIRD').ctaWrapperClass).toContain('border-cyan');
  });
});

describe('ScanDetailComponent — findings', () => {
  it('retourne un tableau vide si scan null', () => {
    expect(makeWithScan(null).findings).toHaveLength(0);
  });
  it('retourne un finding par module (19) pour un scan tier 4', () => {
    expect(makeWithScan(TIER4_SCAN).findings).toHaveLength(19);
  });
  it('marque les modules absents comme skipped pour un scan tier 2', () => {
    const findings = makeWithScan(TIER2_SCAN).findings;
    const tech = findings.find(f => f.key === 'tech');
    expect(tech?.skipped).toBe(true);
    const ssl = findings.find(f => f.key === 'ssl');
    expect(ssl?.skipped).toBe(false);
    expect(ssl?.status).toBe('OK');
  });
});

describe('ScanDetailComponent — score / grade / scoreColor', () => {
  it('score null si scan null', () => {
    expect(makeWithScan(null).score).toBeNull();
  });
  it('score = 100 pour un scan tout OK', () => {
    expect(makeWithScan(TIER4_SCAN).score).toBe(100);
  });
  it('grade = "—" si score null', () => {
    expect(makeWithScan(null).grade).toBe('—');
  });
  it('grade = "A" pour un score de 100', () => {
    expect(makeWithScan(TIER4_SCAN).grade).toBe('A');
  });
  it('scoreColor gris par défaut si score null', () => {
    expect(makeWithScan(null).scoreColor).toBe('#6b7280');
  });
  it('scoreColor renvoie une couleur pour un score valide', () => {
    expect(makeWithScan(TIER4_SCAN).scoreColor).toMatch(/^#/);
  });
});

describe('ScanDetailComponent — radar', () => {
  it('radarLabels renvoie les libellés des catégories', () => {
    const labels = make().radarLabels;
    expect(labels).toContain('SSL/TLS');
    expect(labels).toContain('Headers');
    expect(labels.length).toBeGreaterThan(0);
  });
  it('radarScores renvoie un score par catégorie', () => {
    const scores = makeWithScan(TIER4_SCAN).radarScores;
    expect(scores.length).toBe(make().radarLabels.length);
    expect(scores.every(s => s === 100)).toBe(true);
  });
  it('radarScores tout à 0 si scan null', () => {
    const scores = makeWithScan(null).radarScores;
    expect(scores.every(s => s === 0)).toBe(true);
  });
});

describe('ScanDetailComponent — remediationScripts', () => {
  it('retourne un tableau vide si scan null', () => {
    expect(makeWithScan(null).remediationScripts).toHaveLength(0);
  });
  it('retourne un tableau vide si JSON invalide', () => {
    expect(makeWithScan('not-json').remediationScripts).toHaveLength(0);
  });
  it('retourne un tableau vide si pas de _meta.remediation_scripts', () => {
    expect(makeWithScan('{"ssl":{"status":"OK"}}').remediationScripts).toHaveLength(0);
  });
  it('mappe les scripts connus et ignore les clés inconnues', () => {
    const json = JSON.stringify({
      _meta: { remediation_scripts: { ufw: {}, ssh: {}, cle_inconnue: {} } },
    });
    const scripts = makeWithScan(json).remediationScripts;
    expect(scripts).toHaveLength(2);
    const keys = scripts.map(s => s.key);
    expect(keys).toContain('ufw');
    expect(keys).toContain('ssh');
    expect(keys).not.toContain('cle_inconnue');
    const ufw = scripts.find(s => s.key === 'ufw');
    expect(ufw?.label).toBeTruthy();
    expect(ufw?.icon).toBeTruthy();
  });
});

describe('ScanDetailComponent — loadScan()', () => {
  function makeComp(): ScanDetailComponent {
    const c = Object.create(ScanDetailComponent.prototype) as ScanDetailComponent;
    (c as any).scan = signal<any>(null);
    (c as any).loading = signal(true);
    (c as any).error = signal<string | null>(null);
    return c;
  }

  it('stocke le scan et arrête le chargement en cas de succès', () => {
    const c = makeComp();
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        {
          getScan: vi.fn().mockReturnValue(of({ id: 1, status: 'done' })),
        };
    c.loadScan(1);
    expect(c.scan()).toEqual({ id: 1, status: 'done' });
    expect(c.loading()).toBe(false);
    expect(c.error()).toBeNull();
  });

  it('déclenche le polling si le scan est pending', () => {
    const c = makeComp();
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        {
          getScan: vi.fn().mockReturnValue(of({ id: 2, status: 'pending' })),
        };
    const spy = vi.spyOn(c, 'startPolling').mockImplementation(() => {});
    c.loadScan(2);
    expect(spy).toHaveBeenCalledWith(2);
  });

  it('ne déclenche pas le polling si le scan est terminé', () => {
    const c = makeComp();
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        {
          getScan: vi.fn().mockReturnValue(of({ id: 3, status: 'done' })),
        };
    const spy = vi.spyOn(c, 'startPolling').mockImplementation(() => {});
    c.loadScan(3);
    expect(spy).not.toHaveBeenCalled();
  });

  it('positionne une erreur si le service échoue', () => {
    const c = makeComp();
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        {
          getScan: vi.fn().mockReturnValue({
            subscribe: (obs: any) => obs.error(new Error('boom')),
          }),
        };
    c.loadScan(9);
    expect(c.error()).toBe('Scan introuvable');
    expect(c.loading()).toBe(false);
  });
});

describe('ScanDetailComponent — downloads', () => {
  function withDom() {
    const anchor: any = { href: '', download: '', click: vi.fn() };
    const createSpy = vi.spyOn(document, 'createElement').mockReturnValue(anchor);
    (globalThis.URL as any).createObjectURL = vi.fn(() => 'blob:fake');
    (globalThis.URL as any).revokeObjectURL = vi.fn();
    return { anchor, createSpy };
  }

  it('downloadPdf ne fait rien si scan null', () => {
    const c = make();
    (c as any).scan = signal<any>(null);
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        { downloadPdfBlob: vi.fn() };
    c.downloadPdf();
    expect((c as any).cyberscan.downloadPdfBlob).not.toHaveBeenCalled();
  });

  it('downloadPdf télécharge un fichier nommé avec l’id', () => {
    const { anchor, createSpy } = withDom();
    const c = make();
    (c as any).scan = signal<any>({ id: 42 });
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        { downloadPdfBlob: vi.fn().mockReturnValue(of(new Blob(['x']))) };
    c.downloadPdf();
    expect((c as any).cyberscan.downloadPdfBlob).toHaveBeenCalledWith(42);
    expect(anchor.download).toBe('cyberscan_rapport_42.pdf');
    expect(anchor.click).toHaveBeenCalled();
    createSpy.mockRestore();
  });

  it('downloadBrandedPdf remet downloadingBranded à false après succès', () => {
    const { createSpy } = withDom();
    const c = make();
    (c as any).scan = signal<any>({ id: 7 });
    (c as any).downloadingBranded = signal(false);
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        {
          downloadBrandedPdfBlob: vi.fn().mockReturnValue(of(new Blob(['x']))),
        };
    c.downloadBrandedPdf();
    expect(c.downloadingBranded()).toBe(false);
    expect((c as any).cyberscan.downloadBrandedPdfBlob).toHaveBeenCalledWith(7);
    createSpy.mockRestore();
  });

  it('downloadBrandedPdf remet downloadingBranded à false en cas d’erreur', () => {
    const c = make();
    (c as any).scan = signal<any>({ id: 7 });
    (c as any).downloadingBranded = signal(false);
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        {
          downloadBrandedPdfBlob: vi.fn().mockReturnValue({
            subscribe: (obs: any) => obs.error(new Error('x')),
          }),
        };
    c.downloadBrandedPdf();
    expect(c.downloadingBranded()).toBe(false);
  });

  it('downloadRemediation utilise l’extension .py pour fastapi', () => {
    const { anchor, createSpy } = withDom();
    const c = make();
    (c as any).scan = signal<any>({ id: 5 });
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        {
          downloadRemediationBlob: vi.fn().mockReturnValue(of(new Blob(['x']))),
        };
    c.downloadRemediation('fastapi');
    expect(anchor.download).toBe('cyberscan_fastapi_5.py');
    createSpy.mockRestore();
  });

  it('downloadRemediation utilise l’extension .sh pour les autres scripts', () => {
    const { anchor, createSpy } = withDom();
    const c = make();
    (c as any).scan = signal<any>({ id: 5 });
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        {
          downloadRemediationBlob: vi.fn().mockReturnValue(of(new Blob(['x']))),
        };
    c.downloadRemediation('ufw');
    expect(anchor.download).toBe('cyberscan_ufw_5.sh');
    createSpy.mockRestore();
  });

  it('downloadRemediation ne fait rien si scan null', () => {
    const c = make();
    (c as any).scan = signal<any>(null);
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        { downloadRemediationBlob: vi.fn() };
    c.downloadRemediation('ufw');
    expect((c as any).cyberscan.downloadRemediationBlob).not.toHaveBeenCalled();
  });
});
