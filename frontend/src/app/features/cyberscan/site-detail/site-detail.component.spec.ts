import { describe, it, expect, vi } from 'vitest';
import { signal } from '@angular/core';
import { of } from 'rxjs';
import { SiteDetailComponent } from './site-detail.component';

function make(): SiteDetailComponent {
  return Object.create(SiteDetailComponent.prototype) as SiteDetailComponent;
}

describe('SiteDetailComponent — statusColor()', () => {
  it('retourne vert pour OK', () => expect(make().statusColor('OK')).toContain('green'));
  it('retourne jaune pour WARNING', () =>
    expect(make().statusColor('WARNING')).toContain('yellow'));
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
  it('retourne check_circle pour done', () =>
    expect(make().statusIcon('done')).toBe('check_circle'));
  it('retourne schedule pour pending', () => expect(make().statusIcon('pending')).toBe('schedule'));
  it('retourne sync pour running', () => expect(make().statusIcon('running')).toBe('sync'));
  it('retourne cancel pour error', () => expect(make().statusIcon('error')).toBe('cancel'));
  it('retourne help_outline pour null', () => expect(make().statusIcon(null)).toBe('help_outline'));
});

describe('SiteDetailComponent — formatDate()', () => {
  it('retourne "—" pour null', () => expect(make().formatDate(null)).toBe('—'));
  it('formate une date ISO', () =>
    expect(make().formatDate('2024-03-15T10:00:00Z')).toContain('2024'));
  it("inclut l'heure", () => expect(make().formatDate('2024-03-15T10:30:00Z')).toMatch(/\d+:\d+/));
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

describe('SiteDetailComponent — vérification de domaine (H2b)', () => {
  function makeComp(): SiteDetailComponent {
    const c = Object.create(SiteDetailComponent.prototype) as SiteDetailComponent;
    (c as any).domainStatus = signal(null);
    (c as any).verifyInfo = signal(null);
    (c as any).verifying = signal(false);
    (c as any).showVerifyPanel = signal(false);
    (c as any).siteId = signal(7);
    (c as any).snack = { open: vi.fn() };
    return c;
  }

  it('loadDomainStatus stocke le statut renvoyé', () => {
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
          getSiteDomainStatus: vi.fn().mockReturnValue(of({ domain: 'a.com', verified: false })),
        };
    c.loadDomainStatus(7);
    expect(c.domainStatus()).toEqual({ domain: 'a.com', verified: false });
  });

  it('startVerify ouvre le panneau et récupère le TXT', () => {
    const c = makeComp();
    const info = {
      domain: 'a.com',
      verified: false,
      verification_token: 't',
      dns_record_name: '_rocher-verify.a.com',
      dns_record_type: 'TXT',
      dns_record_value: 't',
      instructions: '',
    };
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        { requestSiteDomainVerify: vi.fn().mockReturnValue(of(info)) };
    c.startVerify();
    expect(c.showVerifyPanel()).toBe(true);
    expect(c.verifyInfo()).toEqual(info);
  });

  it('checkVerify vérifié -> ferme le panneau + met à jour le statut', () => {
    const c = makeComp();
    (c as any).showVerifyPanel.set(true);
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        {
          checkSiteDomainVerify: vi.fn().mockReturnValue(of({ domain: 'a.com', verified: true })),
        };
    c.checkVerify();
    expect(c.domainStatus()?.verified).toBe(true);
    expect(c.showVerifyPanel()).toBe(false);
  });

  it('checkVerify non vérifié -> garde le panneau ouvert', () => {
    const c = makeComp();
    (c as any).showVerifyPanel.set(true);
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        {
          checkSiteDomainVerify: vi.fn().mockReturnValue(of({ domain: 'a.com', verified: false })),
        };
    c.checkVerify();
    expect(c.domainStatus()?.verified).toBe(false);
    expect(c.showVerifyPanel()).toBe(true);
  });
});

describe('SiteDetailComponent — roleLabel()', () => {
  it('traduit viewer en Lecteur', () => expect(make().roleLabel('viewer')).toBe('Lecteur'));
  it('traduit auditor en Auditeur', () => expect(make().roleLabel('auditor')).toBe('Auditeur'));
  it('traduit manager en Manager', () => expect(make().roleLabel('manager')).toBe('Manager'));
  it('retourne la valeur brute pour un rôle inconnu', () =>
    expect(make().roleLabel('owner')).toBe('owner'));
});

describe('SiteDetailComponent — collaborateurs', () => {
  function makeComp(): SiteDetailComponent {
    const c = Object.create(SiteDetailComponent.prototype) as SiteDetailComponent;
    (c as any).collaborators = signal([]);
    (c as any).showInviteForm = signal(false);
    (c as any).sendingInvite = signal(false);
    (c as any).siteId = signal(7);
    (c as any).snack = { open: vi.fn() };
    c.inviteEmail = '';
    c.inviteRole = 'viewer';
    return c;
  }

  it('loadCollaborators stocke la liste renvoyée', () => {
    const c = makeComp();
    const list = [{ id: 1, email: 'a@b.com', role: 'viewer' }];
    (c as any).collabService = { list: vi.fn().mockReturnValue(of(list)) };
    c.loadCollaborators(7);
    expect(c.collaborators()).toEqual(list);
  });

  it('sendInvite ne fait rien si email vide', () => {
    const c = makeComp();
    (c as any).collabService = { invite: vi.fn() };
    c.sendInvite();
    expect((c as any).collabService.invite).not.toHaveBeenCalled();
    expect(c.sendingInvite()).toBe(false);
  });

  it('sendInvite ajoute le collaborateur et réinitialise le formulaire', () => {
    const c = makeComp();
    c.inviteEmail = 'new@b.com';
    c.inviteRole = 'manager';
    const collab = { id: 9, email: 'new@b.com', role: 'manager' };
    (c as any).collabService = { invite: vi.fn().mockReturnValue(of(collab)) };
    c.sendInvite();
    expect((c as any).collabService.invite).toHaveBeenCalledWith(7, 'new@b.com', 'manager');
    expect(c.collaborators()).toEqual([collab]);
    expect(c.inviteEmail).toBe('');
    expect(c.inviteRole).toBe('viewer');
    expect(c.showInviteForm()).toBe(false);
    expect(c.sendingInvite()).toBe(false);
    expect((c as any).snack.open).toHaveBeenCalled();
  });

  it('sendInvite gère une erreur serveur', () => {
    const c = makeComp();
    c.inviteEmail = 'new@b.com';
    (c as any).collabService = {
      invite: vi.fn().mockReturnValue({
        subscribe: (h: any) => h.error({ error: { detail: 'déjà invité' } }),
      }),
    };
    c.sendInvite();
    expect(c.sendingInvite()).toBe(false);
    expect((c as any).snack.open).toHaveBeenCalledWith('déjà invité', 'Fermer', expect.anything());
  });

  it('removeCollaborator retire le collaborateur de la liste', () => {
    const c = makeComp();
    (c as any).collaborators.set([
      { id: 1, email: 'a@b.com', role: 'viewer' },
      { id: 2, email: 'b@b.com', role: 'viewer' },
    ]);
    (c as any).collabService = { remove: vi.fn().mockReturnValue(of(void 0)) };
    c.removeCollaborator(1);
    expect(c.collaborators().map((x: any) => x.id)).toEqual([2]);
  });

  it("removeCollaborator affiche une erreur en cas d'échec", () => {
    const c = makeComp();
    (c as any).collaborators.set([{ id: 1, email: 'a@b.com', role: 'viewer' }]);
    (c as any).collabService = {
      remove: vi.fn().mockReturnValue({ subscribe: (h: any) => h.error() }),
    };
    c.removeCollaborator(1);
    expect((c as any).snack.open).toHaveBeenCalled();
    expect(c.collaborators().length).toBe(1);
  });
});

describe('SiteDetailComponent — statuts de failles', () => {
  function makeComp(): SiteDetailComponent {
    const c = Object.create(SiteDetailComponent.prototype) as SiteDetailComponent;
    (c as any).findingStatuses = signal({});
    (c as any).siteId = signal(7);
    return c;
  }

  it('loadFindingStatuses transforme la liste en map module_key -> status', () => {
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
          getFindingStatuses: vi.fn().mockReturnValue(
            of([
              { module_key: 'ssl', status: 'resolved' },
              { module_key: 'headers', status: 'todo' },
            ])
          ),
        };
    c.loadFindingStatuses(7);
    expect(c.findingStatuses()).toEqual({ ssl: 'resolved', headers: 'todo' });
  });

  it('setFindingStatus met à jour la map de façon optimiste', () => {
    const c = makeComp();
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        { updateFindingStatus: vi.fn().mockReturnValue(of(void 0)) };
    c.setFindingStatus('ssl', 'in_progress');
    expect(c.findingStatuses()).toEqual({ ssl: 'in_progress' });
    expect((c as any).cyberscan.updateFindingStatus).toHaveBeenCalledWith(7, 'ssl', 'in_progress');
  });

  it("setFindingStatus rollback en cas d'erreur", () => {
    const c = makeComp();
    (c as any).findingStatuses.set({ ssl: 'todo' });
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        {
          updateFindingStatus: vi.fn().mockReturnValue({ subscribe: (h: any) => h.error() }),
        };
    c.setFindingStatus('ssl', 'resolved');
    expect(c.findingStatuses()).toEqual({ ssl: 'todo' });
  });
});

describe('SiteDetailComponent — scans & pagination', () => {
  function makeComp(): SiteDetailComponent {
    const c = Object.create(SiteDetailComponent.prototype) as SiteDetailComponent;
    (c as any).scans = signal(null);
    (c as any).loadingScans = signal(false);
    (c as any).currentPage = signal(1);
    (c as any).triggering = signal(false);
    (c as any).siteId = signal(7);
    (c as any).snack = { open: vi.fn() };
    return c;
  }

  it('loadScans stocke les données et arrête le loader', () => {
    const c = makeComp();
    const data = { items: [], total: 0, page: 2, page_size: 20, total_pages: 0 };
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        { getSiteScans: vi.fn().mockReturnValue(of(data)) };
    c.loadScans(2);
    expect(c.scans()).toEqual(data);
    expect(c.loadingScans()).toBe(false);
    expect(c.currentPage()).toBe(2);
  });

  it("loadScans arrête le loader en cas d'erreur", () => {
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
          getSiteScans: vi.fn().mockReturnValue({ subscribe: (h: any) => h.error() }),
        };
    c.loadScans(1);
    expect(c.loadingScans()).toBe(false);
  });

  it('onPageChange convertit pageIndex 0-based en page 1-based', () => {
    const c = makeComp();
    const spy = vi.spyOn(c, 'loadScans').mockImplementation(() => {});
    c.onPageChange({ pageIndex: 3 } as any);
    expect(spy).toHaveBeenCalledWith(4);
  });

  it('maybeStartPolling ne démarre rien sans scan actif', () => {
    const c = makeComp();
    c.maybeStartPolling([{ status: 'done' } as any]);
    expect((c as any).pollingSubscription).toBeUndefined();
  });

  it('triggerScan happy path relance la liste et notifie', () => {
    const c = makeComp();
    const spy = vi.spyOn(c, 'loadScans').mockImplementation(() => {});
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        { triggerScan: vi.fn().mockReturnValue(of(void 0)) };
    c.triggerScan();
    expect(c.triggering()).toBe(false);
    expect(spy).toHaveBeenCalledWith(1);
    expect((c as any).snack.open).toHaveBeenCalled();
  });

  it("triggerScan affiche le détail de l'erreur serveur", () => {
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
          triggerScan: vi.fn().mockReturnValue({
            subscribe: (h: any) => h.error({ error: { detail: 'quota atteint' } }),
          }),
        };
    c.triggerScan();
    expect(c.triggering()).toBe(false);
    expect((c as any).snack.open).toHaveBeenCalledWith(
      'quota atteint',
      'Fermer',
      expect.anything()
    );
  });
});

describe('SiteDetailComponent — téléchargement PDF', () => {
  function makeComp(): SiteDetailComponent {
    const c = Object.create(SiteDetailComponent.prototype) as SiteDetailComponent;
    (c as any).snack = { open: vi.fn() };
    return c;
  }

  it("downloadPdf déclenche la création puis la révocation de l'URL blob", () => {
    const c = makeComp();
    const createSpy = vi.fn().mockReturnValue('blob:x');
    const revokeSpy = vi.fn();
    (URL as any).createObjectURL = createSpy;
    (URL as any).revokeObjectURL = revokeSpy;
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        {
          downloadPdfBlob: vi.fn().mockReturnValue(of(new Blob(['pdf']))),
        };
    c.downloadPdf(42);
    expect(createSpy).toHaveBeenCalled();
    expect(revokeSpy).toHaveBeenCalledWith('blob:x');
  });

  it("downloadPdf notifie en cas d'erreur", () => {
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
          downloadPdfBlob: vi.fn().mockReturnValue({ subscribe: (h: any) => h.error() }),
        };
    c.downloadPdf(42);
    expect((c as any).snack.open).toHaveBeenCalled();
  });
});

describe('SiteDetailComponent — getters calculés', () => {
  const critical = JSON.stringify({ ssl: { status: 'CRITICAL' }, headers: { status: 'WARNING' } });
  const good = JSON.stringify({ ssl: { status: 'OK' }, headers: { status: 'OK' } });

  function withScans(items: any[]): SiteDetailComponent {
    const c = Object.create(SiteDetailComponent.prototype) as SiteDetailComponent;
    (c as any).scans = signal({
      items,
      total: items.length,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });
    return c;
  }

  function empty(): SiteDetailComponent {
    const c = Object.create(SiteDetailComponent.prototype) as SiteDetailComponent;
    (c as any).scans = signal(null);
    return c;
  }

  it('latestDoneScan retourne le premier scan terminé avec résultats', () => {
    const c = withScans([
      { id: 3, status: 'pending', results_json: null },
      { id: 2, status: 'done', results_json: critical },
    ]);
    expect(c.latestDoneScan?.id).toBe(2);
  });

  it('latestDoneScan retourne null si aucun scan terminé', () => {
    expect(empty().latestDoneScan).toBeNull();
  });

  it('latestScore calcule le score du dernier scan', () => {
    const c = withScans([{ id: 2, status: 'done', results_json: critical }]);
    expect(c.latestScore).toBe(25);
  });

  it('latestGrade et latestScoreColor sur score bas', () => {
    const c = withScans([{ id: 2, status: 'done', results_json: critical }]);
    expect(c.latestGrade).toBe('F');
    expect(c.latestScoreColor).toBe('#f87171');
  });

  it('latestGrade et latestScoreColor par défaut quand pas de score', () => {
    const c = empty();
    expect(c.latestGrade).toBe('—');
    expect(c.latestScoreColor).toBe('#6b7280');
  });

  it('findings / criticalFindings / warningFindings / alertFindings', () => {
    const c = withScans([{ id: 2, status: 'done', results_json: critical }]);
    expect(c.findings.length).toBeGreaterThan(0);
    expect(c.criticalFindings.every(f => f.status === 'CRITICAL')).toBe(true);
    expect(c.criticalFindings.length).toBe(1);
    expect(c.warningFindings.length).toBe(1);
    expect(c.alertFindings.length).toBe(2);
  });

  it('findings vide quand pas de scan', () => {
    expect(empty().findings).toEqual([]);
  });

  it('pdfScans ne garde que les scans avec pdf_path', () => {
    const c = withScans([
      { id: 2, status: 'done', results_json: good, pdf_path: 'a.pdf' },
      { id: 1, status: 'done', results_json: good, pdf_path: null },
    ]);
    expect(c.pdfScans.map((s: any) => s.id)).toEqual([2]);
  });

  it('hasActiveScans vrai avec un scan running, faux sinon', () => {
    expect(withScans([{ status: 'running' }]).hasActiveScans).toBe(true);
    expect(withScans([{ status: 'done' }]).hasActiveScans).toBe(false);
    expect(empty().hasActiveScans).toBe(false);
  });

  it('scoreTrend ne garde que les scans terminés avec finished_at et score > 0', () => {
    const c = withScans([
      { status: 'done', results_json: critical, finished_at: '2024-06-02T10:00:00Z' },
      { status: 'done', results_json: good, finished_at: '2024-06-01T10:00:00Z' },
      { status: 'done', results_json: critical, finished_at: null },
      { status: 'pending', results_json: null, finished_at: null },
    ]);
    expect(c.scoreTrend.length).toBe(2);
  });

  it('scoreProgression calcule delta entre le plus ancien et le plus récent', () => {
    const c = withScans([
      { status: 'done', results_json: critical, finished_at: '2024-06-02T10:00:00Z' },
      { status: 'done', results_json: good, finished_at: '2024-06-01T10:00:00Z' },
    ]);
    const prog = c.scoreProgression!;
    expect(prog.count).toBe(2);
    expect(prog.last).toBe(25);
    expect(prog.first).toBe(100);
    expect(prog.delta).toBe(-75);
  });

  it('scoreProgression null avec moins de 2 points', () => {
    const c = withScans([
      { status: 'done', results_json: critical, finished_at: '2024-06-02T10:00:00Z' },
    ]);
    expect(c.scoreProgression).toBeNull();
  });

  it('getScanScore / getScanCriticalCount / getScanWarningCount', () => {
    const c = Object.create(SiteDetailComponent.prototype) as SiteDetailComponent;
    const scan = { results_json: critical } as any;
    expect(c.getScanScore(scan)).toBe(25);
    expect(c.getScanCriticalCount(scan)).toBe(1);
    expect(c.getScanWarningCount(scan)).toBe(1);
  });

  it('getScanScore null sans résultats', () => {
    const c = Object.create(SiteDetailComponent.prototype) as SiteDetailComponent;
    expect(c.getScanScore({ results_json: null } as any)).toBeNull();
  });
});
