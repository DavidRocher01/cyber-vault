/**
 * UrlScannerComponent — tests des méthodes utilitaires pures.
 */
import { describe, it, expect, vi } from 'vitest';
import { signal } from '@angular/core';
import { of } from 'rxjs';
import { UrlScannerComponent } from './url-scanner.component';

function make(): UrlScannerComponent {
  return Object.create(UrlScannerComponent.prototype) as UrlScannerComponent;
}

describe('UrlScannerComponent — verdictColor()', () => {
  it('retourne vert pour safe', () => expect(make().verdictColor('safe')).toContain('green'));
  it('retourne jaune pour suspicious', () =>
    expect(make().verdictColor('suspicious')).toContain('yellow'));
  it('retourne rouge pour malicious', () =>
    expect(make().verdictColor('malicious')).toContain('red'));
  it('retourne gris pour null', () => expect(make().verdictColor(null)).toContain('gray'));
  it('retourne gris pour inconnu', () => expect(make().verdictColor('unknown')).toContain('gray'));
});

describe('UrlScannerComponent — verdictBg()', () => {
  it('retourne bg vert pour safe', () => expect(make().verdictBg('safe')).toContain('green'));
  it('retourne bg jaune pour suspicious', () =>
    expect(make().verdictBg('suspicious')).toContain('yellow'));
  it('retourne bg rouge pour malicious', () =>
    expect(make().verdictBg('malicious')).toContain('red'));
  it('retourne bg gris pour null', () => expect(make().verdictBg(null)).toContain('gray'));
});

describe('UrlScannerComponent — verdictLabel()', () => {
  it('traduit safe → Sûr', () => expect(make().verdictLabel('safe')).toBe('Sûr'));
  it('traduit suspicious → Suspect', () =>
    expect(make().verdictLabel('suspicious')).toBe('Suspect'));
  it('traduit malicious → Malveillant', () =>
    expect(make().verdictLabel('malicious')).toBe('Malveillant'));
  it('retourne "—" pour null', () => expect(make().verdictLabel(null)).toBe('—'));
});

describe('UrlScannerComponent — verdictIcon()', () => {
  it('retourne verified_user pour safe', () =>
    expect(make().verdictIcon('safe')).toBe('verified_user'));
  it('retourne warning pour suspicious', () =>
    expect(make().verdictIcon('suspicious')).toBe('warning'));
  it('retourne gpp_bad pour malicious', () =>
    expect(make().verdictIcon('malicious')).toBe('gpp_bad'));
  it('retourne help_outline pour null', () =>
    expect(make().verdictIcon(null)).toBe('help_outline'));
});

describe('UrlScannerComponent — threatTypeLabel()', () => {
  it('traduit phishing', () => expect(make().threatTypeLabel('phishing')).toBe('Phishing'));
  it('traduit malware', () => expect(make().threatTypeLabel('malware')).toBe('Malware'));
  it('traduit redirect', () =>
    expect(make().threatTypeLabel('redirect')).toBe('Redirection suspecte'));
  it('traduit tracker', () => expect(make().threatTypeLabel('tracker')).toBe('Tracker'));
  it('traduit malicious_domain', () =>
    expect(make().threatTypeLabel('malicious_domain')).toBe('Domaine malveillant'));
  it('retourne la valeur brute pour un type inconnu', () =>
    expect(make().threatTypeLabel('custom_type')).toBe('custom_type'));
  it('retourne "—" pour null', () => expect(make().threatTypeLabel(null)).toBe('—'));
});

describe('UrlScannerComponent — severityColor()', () => {
  it('retourne les classes pour critical', () =>
    expect(make().severityColor('critical')).toContain('red'));
  it('retourne les classes pour high', () =>
    expect(make().severityColor('high')).toContain('orange'));
  it('retourne les classes pour medium', () =>
    expect(make().severityColor('medium')).toContain('yellow'));
  it('retourne les classes par défaut pour low', () =>
    expect(make().severityColor('low')).toContain('gray'));
});

describe('UrlScannerComponent — severityLabel()', () => {
  it('traduit critical → Critique', () =>
    expect(make().severityLabel('critical')).toBe('Critique'));
  it('traduit high → Élevé', () => expect(make().severityLabel('high')).toBe('Élevé'));
  it('traduit low → Faible', () => expect(make().severityLabel('low')).toBe('Faible'));
  it('retourne la valeur brute si inconnue', () =>
    expect(make().severityLabel('exotic')).toBe('exotic'));
});

describe('UrlScannerComponent — formatDate()', () => {
  it('retourne "—" pour null', () => expect(make().formatDate(null)).toBe('—'));
  it('formate une date ISO', () => {
    const result = make().formatDate('2024-01-15T10:00:00Z');
    expect(result).toContain('2024');
  });
});

describe('UrlScannerComponent — scoreGradient()', () => {
  it('retourne rouge (#f87171) pour score >= 66', () => {
    expect(make().scoreGradient(80)).toBe('#f87171');
    expect(make().scoreGradient(66)).toBe('#f87171');
  });

  it('retourne jaune (#facc15) pour score entre 31 et 65', () => {
    expect(make().scoreGradient(50)).toBe('#facc15');
    expect(make().scoreGradient(31)).toBe('#facc15');
  });

  it('retourne vert (#4ade80) pour score <= 30', () => {
    expect(make().scoreGradient(0)).toBe('#4ade80');
    expect(make().scoreGradient(30)).toBe('#4ade80');
  });
});

describe('UrlScannerComponent — verdictBg() branche par défaut', () => {
  it('retourne bg gris pour un verdict inconnu', () =>
    expect(make().verdictBg('unknown')).toContain('gray'));
});

describe('UrlScannerComponent — severityColor() branche par défaut', () => {
  it('retourne les classes par défaut pour une sévérité inconnue', () =>
    expect(make().severityColor('exotic')).toContain('gray'));
});

describe('UrlScannerComponent — severityLabel() cas medium', () => {
  it('traduit medium → Moyen', () => expect(make().severityLabel('medium')).toBe('Moyen'));
});

describe('UrlScannerComponent — getResults()', () => {
  it('retourne null si results_json est absent', () => {
    expect(make().getResults({ results_json: null } as any)).toBeNull();
  });

  it('parse un JSON valide', () => {
    const res = make().getResults({ results_json: '{"verdict":"safe","threat_score":10}' } as any);
    expect(res).toEqual({ verdict: 'safe', threat_score: 10 });
  });

  it('retourne null si le JSON est invalide', () => {
    expect(make().getResults({ results_json: '{invalide' } as any)).toBeNull();
  });
});

describe('UrlScannerComponent — isRunning (getter)', () => {
  it('retourne false quand aucun scan actif', () => {
    const c = make();
    (c as any).activeScan = signal(null);
    expect(c.isRunning).toBe(false);
  });

  it('retourne true quand le scan est pending', () => {
    const c = make();
    (c as any).activeScan = signal({ id: 1, status: 'pending' });
    expect(c.isRunning).toBe(true);
  });

  it('retourne true quand le scan est running', () => {
    const c = make();
    (c as any).activeScan = signal({ id: 1, status: 'running' });
    expect(c.isRunning).toBe(true);
  });

  it('retourne false quand le scan est terminé', () => {
    const c = make();
    (c as any).activeScan = signal({ id: 1, status: 'done' });
    expect(c.isRunning).toBe(false);
  });
});

describe('UrlScannerComponent — viewScan()', () => {
  it('affecte le scan au signal activeScan', () => {
    const c = make();
    (c as any).activeScan = signal(null);
    const scan = { id: 42, status: 'done' } as any;
    c.viewScan(scan);
    expect(c.activeScan()).toBe(scan);
  });
});

describe('UrlScannerComponent — loadHistory()', () => {
  function makeComp(): UrlScannerComponent {
    const c = make();
    (c as any).loadingHistory = signal(false);
    (c as any).currentPage = signal(1);
    (c as any).history = signal(null);
    return c;
  }

  it('stocke les données et relance le polling des scans en cours', () => {
    const c = makeComp();
    const startPolling = vi.fn();
    (c as any).startPolling = startPolling;
    const data = {
      items: [
        { id: 1, status: 'pending' },
        { id: 2, status: 'done' },
        { id: 3, status: 'running' },
      ],
      total: 3,
      page: 2,
      per_page: 20,
      pages: 1,
    };
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        { getUrlScans: vi.fn().mockReturnValue(of(data)) };

    c.loadHistory(2);

    expect((c as any).cyberscan.getUrlScans).toHaveBeenCalledWith(2, 20);
    expect(c.currentPage()).toBe(2);
    expect(c.history()).toEqual(data);
    expect(c.loadingHistory()).toBe(false);
    expect(startPolling).toHaveBeenCalledTimes(2);
    expect(startPolling).toHaveBeenCalledWith(1);
    expect(startPolling).toHaveBeenCalledWith(3);
  });
});

describe('UrlScannerComponent — onPageChange()', () => {
  it('appelle loadHistory avec pageIndex + 1', () => {
    const c = make();
    const loadHistory = vi.fn();
    (c as any).loadHistory = loadHistory;
    c.onPageChange({ pageIndex: 4, pageSize: 20, length: 100 });
    expect(loadHistory).toHaveBeenCalledWith(5);
  });
});

describe('UrlScannerComponent — submit()', () => {
  it('ne fait rien si le formulaire est invalide', () => {
    const c = make();
    (c as any).form = { invalid: true };
    (c as any).submitting = signal(false);
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        { triggerUrlScan: vi.fn() };
    c.submit();
    expect((c as any).cyberscan.triggerUrlScan).not.toHaveBeenCalled();
    expect(c.submitting()).toBe(false);
  });

  it('lance le scan, réinitialise le formulaire et déclenche le polling', () => {
    const c = make();
    const reset = vi.fn();
    (c as any).form = {
      invalid: false,
      getRawValue: () => ({ url: 'https://x.com' }),
      reset,
    };
    (c as any).submitting = signal(true);
    (c as any).activeScan = signal(null);
    (c as any).snack = { open: vi.fn() };
    const startPolling = vi.fn();
    const loadHistory = vi.fn();
    (c as any).startPolling = startPolling;
    (c as any).loadHistory = loadHistory;
    const scan = { id: 9, status: 'pending' };
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        { triggerUrlScan: vi.fn().mockReturnValue(of(scan)) };

    c.submit();

    expect((c as any).cyberscan.triggerUrlScan).toHaveBeenCalledWith('https://x.com');
    expect(c.submitting()).toBe(false);
    expect(reset).toHaveBeenCalled();
    expect(c.activeScan()).toBe(scan);
    expect((c as any).snack.open).toHaveBeenCalled();
    expect(startPolling).toHaveBeenCalledWith(9);
    expect(loadHistory).toHaveBeenCalledWith(1);
  });

  it('affiche une erreur si le lancement échoue', () => {
    const c = make();
    (c as any).form = {
      invalid: false,
      getRawValue: () => ({ url: 'https://x.com' }),
      reset: vi.fn(),
    };
    (c as any).submitting = signal(true);
    (c as any).snack = { open: vi.fn() };
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        {
          triggerUrlScan: vi.fn().mockReturnValue({
            subscribe: (h: any) => h.error({ error: { detail: 'Boom' } }),
          }),
        };

    c.submit();

    expect(c.submitting()).toBe(false);
    expect((c as any).snack.open).toHaveBeenCalledWith('Boom', 'Fermer', { duration: 6000 });
  });
});

describe('UrlScannerComponent — deleteScan()', () => {
  it('retire le scan de l’historique et vide activeScan si affiché', () => {
    const c = make();
    (c as any).history = signal({
      items: [
        { id: 1, status: 'done' },
        { id: 2, status: 'done' },
      ],
      total: 2,
      page: 1,
      per_page: 20,
      pages: 1,
    });
    (c as any).activeScan = signal({ id: 2, status: 'done' });
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        { deleteUrlScan: vi.fn().mockReturnValue(of(void 0)) };

    c.deleteScan({ id: 2 } as any);

    expect((c as any).cyberscan.deleteUrlScan).toHaveBeenCalledWith(2);
    expect(c.history()?.items.map((s: any) => s.id)).toEqual([1]);
    expect(c.history()?.total).toBe(1);
    expect(c.activeScan()).toBeNull();
  });

  it('conserve activeScan si un autre scan est affiché', () => {
    const c = make();
    (c as any).history = signal({
      items: [{ id: 1, status: 'done' }],
      total: 1,
      page: 1,
      per_page: 20,
      pages: 1,
    });
    const active = { id: 5, status: 'done' };
    (c as any).activeScan = signal(active);
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        { deleteUrlScan: vi.fn().mockReturnValue(of(void 0)) };

    c.deleteScan({ id: 1 } as any);

    expect(c.activeScan()).toBe(active);
  });
});

describe('UrlScannerComponent — downloadPdf()', () => {
  it('affiche une erreur en cas d’échec du téléchargement', () => {
    const c = make();
    (c as any).snack = { open: vi.fn() };
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        {
          downloadUrlScanPdfBlob: vi.fn().mockReturnValue({
            subscribe: (h: any) => h.error(new Error('fail')),
          }),
        };

    c.downloadPdf({ id: 3 } as any);

    expect((c as any).cyberscan.downloadUrlScanPdfBlob).toHaveBeenCalledWith(3);
    expect((c as any).snack.open).toHaveBeenCalledWith(
      'Erreur lors du téléchargement du PDF',
      'Fermer',
      { duration: 4000 }
    );
  });
});
