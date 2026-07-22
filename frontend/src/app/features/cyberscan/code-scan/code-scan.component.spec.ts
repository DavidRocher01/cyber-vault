/**
 * CodeScanComponent — tests des méthodes utilitaires pures.
 * Ces méthodes ne dépendent pas d'Angular DI ni des signaux.
 * On les teste directement via Object.create sur le prototype.
 */
import { describe, it, expect, vi } from 'vitest';
import { signal } from '@angular/core';
import { of } from 'rxjs';
import { CodeScanComponent } from './code-scan.component';

function makeComponent(): CodeScanComponent {
  // Bypass Angular DI — only test pure utility methods.
  return Object.create(CodeScanComponent.prototype) as CodeScanComponent;
}

describe('CodeScanComponent — severityColor()', () => {
  it('retourne les classes CSS pour critical', () => {
    const c = makeComponent();
    expect(c.severityColor('critical')).toContain('red');
  });

  it('retourne les classes CSS pour high', () => {
    expect(makeComponent().severityColor('high')).toContain('orange');
  });

  it('retourne les classes CSS pour medium', () => {
    expect(makeComponent().severityColor('medium')).toContain('yellow');
  });

  it('retourne les classes CSS grises pour low/inconnu', () => {
    expect(makeComponent().severityColor('low')).toContain('gray');
    expect(makeComponent().severityColor('unknown')).toContain('gray');
  });
});

describe('CodeScanComponent — severityLabel()', () => {
  it('traduit critical → Critique', () => {
    expect(makeComponent().severityLabel('critical')).toBe('Critique');
  });

  it('traduit high → Élevé', () => {
    expect(makeComponent().severityLabel('high')).toBe('Élevé');
  });

  it('traduit medium → Moyen', () => {
    expect(makeComponent().severityLabel('medium')).toBe('Moyen');
  });

  it('traduit low → Faible', () => {
    expect(makeComponent().severityLabel('low')).toBe('Faible');
  });

  it('retourne la valeur brute si inconnue', () => {
    expect(makeComponent().severityLabel('exotic')).toBe('exotic');
  });
});

describe('CodeScanComponent — severityIcon()', () => {
  it('retourne dangerous pour critical', () => {
    expect(makeComponent().severityIcon('critical')).toBe('dangerous');
  });

  it('retourne error pour high', () => {
    expect(makeComponent().severityIcon('high')).toBe('error');
  });

  it('retourne warning pour medium', () => {
    expect(makeComponent().severityIcon('medium')).toBe('warning');
  });

  it('retourne info pour low', () => {
    expect(makeComponent().severityIcon('low')).toBe('info');
  });
});

describe('CodeScanComponent — toolBadge()', () => {
  it('retourne les classes pour bandit', () => {
    expect(makeComponent().toolBadge('bandit')).toContain('purple');
  });

  it('retourne les classes pour semgrep', () => {
    expect(makeComponent().toolBadge('semgrep')).toContain('blue');
  });

  it('retourne les classes pour pip-audit', () => {
    expect(makeComponent().toolBadge('pip-audit')).toContain('yellow');
  });

  it('retourne les classes par défaut pour un outil inconnu', () => {
    expect(makeComponent().toolBadge('unknown_tool')).toContain('gray');
  });
});

describe('CodeScanComponent — statusColor()', () => {
  it('retourne vert pour done', () => {
    expect(makeComponent().statusColor('done')).toContain('green');
  });

  it('retourne cyan pour running', () => {
    expect(makeComponent().statusColor('running')).toContain('cyan');
  });

  it('retourne jaune pour pending', () => {
    expect(makeComponent().statusColor('pending')).toContain('yellow');
  });

  it('retourne rouge pour failed', () => {
    expect(makeComponent().statusColor('failed')).toContain('red');
  });

  it('retourne gris pour statut inconnu', () => {
    expect(makeComponent().statusColor('unknown')).toContain('gray');
  });
});

describe('CodeScanComponent — statusLabel()', () => {
  it('traduit done → Terminé', () => {
    expect(makeComponent().statusLabel('done')).toBe('Terminé');
  });

  it('traduit running → En cours', () => {
    expect(makeComponent().statusLabel('running')).toBe('En cours');
  });

  it('traduit pending → En attente', () => {
    expect(makeComponent().statusLabel('pending')).toBe('En attente');
  });

  it('traduit failed → Échec', () => {
    expect(makeComponent().statusLabel('failed')).toBe('Échec');
  });
});

describe('CodeScanComponent — statusBadgeClass()', () => {
  it('retourne les classes pour done', () => {
    expect(makeComponent().statusBadgeClass('done')).toContain('green');
  });

  it('retourne les classes pour running', () => {
    expect(makeComponent().statusBadgeClass('running')).toContain('cyan');
  });

  it('retourne les classes pour pending', () => {
    expect(makeComponent().statusBadgeClass('pending')).toContain('yellow');
  });

  it('retourne les classes pour failed', () => {
    expect(makeComponent().statusBadgeClass('failed')).toContain('red');
  });
});

describe('CodeScanComponent — formatDate()', () => {
  it('retourne "—" pour null', () => {
    expect(makeComponent().formatDate(null)).toBe('—');
  });

  it('formate une date ISO en français', () => {
    const result = makeComponent().formatDate('2024-03-15T10:30:00Z');
    // Should contain year 2024 (locale-dependent formatting)
    expect(result).toContain('2024');
  });

  it('formate une date ISO récente', () => {
    const result = makeComponent().formatDate('2026-04-10T08:00:00Z');
    expect(result).toContain('2026');
  });
});

describe('CodeScanComponent — formatFileSize()', () => {
  it('affiche les octets pour < 1024', () => {
    expect(makeComponent().formatFileSize(512)).toBe('512 B');
  });

  it('affiche les KB pour < 1MB', () => {
    expect(makeComponent().formatFileSize(2048)).toBe('2.0 KB');
  });

  it('affiche les MB pour >= 1MB', () => {
    expect(makeComponent().formatFileSize(5 * 1024 * 1024)).toBe('5.0 MB');
  });

  it('affiche 1024 B = 1.0 KB', () => {
    expect(makeComponent().formatFileSize(1024)).toBe('1.0 KB');
  });
});

describe('CodeScanComponent — totalFindings()', () => {
  it('additionne critical + high + medium + low', () => {
    const scan: any = { critical_count: 2, high_count: 3, medium_count: 5, low_count: 1 };
    expect(makeComponent().totalFindings(scan)).toBe(11);
  });

  it('retourne 0 si tous les compteurs sont à 0', () => {
    const scan: any = { critical_count: 0, high_count: 0, medium_count: 0, low_count: 0 };
    expect(makeComponent().totalFindings(scan)).toBe(0);
  });

  it('retourne la somme correcte avec une seule sévérité', () => {
    const scan: any = { critical_count: 0, high_count: 7, medium_count: 0, low_count: 0 };
    expect(makeComponent().totalFindings(scan)).toBe(7);
  });
});

describe('CodeScanComponent — getResults()', () => {
  it('retourne null si results_json est null', () => {
    const scan: any = { results_json: null };
    expect(makeComponent().getResults(scan)).toBeNull();
  });

  it('parse le JSON et retourne les résultats', () => {
    const data = {
      findings: [{ severity: 'high' }],
      summary: { total: 1, critical: 0, high: 1, medium: 0, low: 0 },
    };
    const scan: any = { results_json: JSON.stringify(data) };
    expect(makeComponent().getResults(scan)).toEqual(data);
  });

  it('retourne null si le JSON est invalide', () => {
    const scan: any = { results_json: 'not-valid-json' };
    expect(makeComponent().getResults(scan)).toBeNull();
  });

  it('parse le JSON avec tool_errors', () => {
    const data = {
      findings: [],
      summary: { total: 0, critical: 0, high: 0, medium: 0, low: 0 },
      tool_errors: ['Bandit', 'Semgrep'],
    };
    const scan: any = { results_json: JSON.stringify(data) };
    const result = makeComponent().getResults(scan);
    expect(result?.tool_errors).toEqual(['Bandit', 'Semgrep']);
  });
});

describe('CodeScanComponent — hasToolErrors()', () => {
  it('retourne false si results_json est null', () => {
    const scan: any = { results_json: null };
    expect(makeComponent().hasToolErrors(scan)).toBe(false);
  });

  it('retourne false si tool_errors est absent', () => {
    const data = { findings: [], summary: { total: 0, critical: 0, high: 0, medium: 0, low: 0 } };
    const scan: any = { results_json: JSON.stringify(data) };
    expect(makeComponent().hasToolErrors(scan)).toBe(false);
  });

  it('retourne false si tool_errors est vide', () => {
    const data = {
      findings: [],
      summary: { total: 0, critical: 0, high: 0, medium: 0, low: 0 },
      tool_errors: [],
    };
    const scan: any = { results_json: JSON.stringify(data) };
    expect(makeComponent().hasToolErrors(scan)).toBe(false);
  });

  it('retourne true si tool_errors contient des outils', () => {
    const data = {
      findings: [],
      summary: { total: 0, critical: 0, high: 0, medium: 0, low: 0 },
      tool_errors: ['Bandit'],
    };
    const scan: any = { results_json: JSON.stringify(data) };
    expect(makeComponent().hasToolErrors(scan)).toBe(true);
  });

  it('retourne true si plusieurs outils manquants', () => {
    const data = {
      findings: [],
      summary: { total: 0, critical: 0, high: 0, medium: 0, low: 0 },
      tool_errors: ['Bandit', 'Semgrep', 'trivy'],
    };
    const scan: any = { results_json: JSON.stringify(data) };
    expect(makeComponent().hasToolErrors(scan)).toBe(true);
  });

  it('retourne false si le JSON est invalide', () => {
    const scan: any = { results_json: 'broken-json' };
    expect(makeComponent().hasToolErrors(scan)).toBe(false);
  });
});

describe('CodeScanComponent — filteredFindings()', () => {
  const results: any = {
    findings: [
      {
        severity: 'critical',
        tool: 'bandit',
        rule: 'B1',
        title: 't',
        message: 'm',
        file: 'f',
        line: 1,
        confidence: 'h',
      },
      {
        severity: 'high',
        tool: 'semgrep',
        rule: 'S1',
        title: 't',
        message: 'm',
        file: 'f',
        line: 2,
        confidence: 'h',
      },
      {
        severity: 'high',
        tool: 'bandit',
        rule: 'B2',
        title: 't',
        message: 'm',
        file: 'g',
        line: 3,
        confidence: 'h',
      },
      {
        severity: 'medium',
        tool: 'trivy',
        rule: 'T1',
        title: 't',
        message: 'm',
        file: 'h',
        line: 4,
        confidence: 'h',
      },
      {
        severity: 'low',
        tool: 'trivy',
        rule: 'T2',
        title: 't',
        message: 'm',
        file: 'i',
        line: 5,
        confidence: 'h',
      },
    ],
    summary: { total: 5, critical: 1, high: 2, medium: 1, low: 1 },
  };

  it("retourne tous les findings pour l'onglet 'all'", () => {
    const fakeComp: any = {
      activeTab: () => 'all',
      filteredFindings: CodeScanComponent.prototype.filteredFindings,
    };
    expect(fakeComp.filteredFindings(results).length).toBe(5);
  });

  it("filtre uniquement les critical pour l'onglet 'critical'", () => {
    const fakeComp: any = {
      activeTab: () => 'critical',
      filteredFindings: CodeScanComponent.prototype.filteredFindings,
    };
    const filtered = fakeComp.filteredFindings(results);
    expect(filtered.length).toBe(1);
    expect(filtered[0].severity).toBe('critical');
  });

  it("filtre uniquement les high pour l'onglet 'high'", () => {
    const fakeComp: any = {
      activeTab: () => 'high',
      filteredFindings: CodeScanComponent.prototype.filteredFindings,
    };
    expect(fakeComp.filteredFindings(results).length).toBe(2);
  });

  it("filtre uniquement les medium pour l'onglet 'medium'", () => {
    const fakeComp: any = {
      activeTab: () => 'medium',
      filteredFindings: CodeScanComponent.prototype.filteredFindings,
    };
    const filtered = fakeComp.filteredFindings(results);
    expect(filtered.length).toBe(1);
    expect(filtered[0].severity).toBe('medium');
  });

  it("filtre uniquement les low pour l'onglet 'low'", () => {
    const fakeComp: any = {
      activeTab: () => 'low',
      filteredFindings: CodeScanComponent.prototype.filteredFindings,
    };
    const filtered = fakeComp.filteredFindings(results);
    expect(filtered.length).toBe(1);
    expect(filtered[0].severity).toBe('low');
  });

  it('retourne un tableau vide si aucun finding ne correspond', () => {
    const fakeComp: any = {
      activeTab: () => 'critical',
      filteredFindings: CodeScanComponent.prototype.filteredFindings,
    };
    const noFindings: any = {
      findings: [
        {
          severity: 'low',
          tool: 'x',
          rule: 'r',
          title: 't',
          message: 'm',
          file: 'f',
          line: 1,
          confidence: '',
        },
      ],
      summary: { total: 1, critical: 0, high: 0, medium: 0, low: 1 },
    };
    expect(fakeComp.filteredFindings(noFindings).length).toBe(0);
  });
});

describe('CodeScanComponent — toolBadge() (branches supplémentaires)', () => {
  it('retourne rouge pour gitleaks', () => {
    expect(makeComponent().toolBadge('gitleaks')).toContain('red');
  });

  it('retourne rose pour trufflehog', () => {
    expect(makeComponent().toolBadge('trufflehog')).toContain('rose');
  });

  it('retourne pink pour detect-secrets', () => {
    expect(makeComponent().toolBadge('detect-secrets')).toContain('pink');
  });

  it('retourne vert pour npm-audit', () => {
    expect(makeComponent().toolBadge('npm-audit')).toContain('green');
  });

  it('retourne cyan pour trivy', () => {
    expect(makeComponent().toolBadge('trivy')).toContain('cyan');
  });

  it('retourne indigo pour hadolint', () => {
    expect(makeComponent().toolBadge('hadolint')).toContain('indigo');
  });
});

describe('CodeScanComponent — statusBadgeClass() (défaut)', () => {
  it('retourne les classes grises pour un statut inconnu', () => {
    expect(makeComponent().statusBadgeClass('unknown')).toContain('gray');
  });
});

describe('CodeScanComponent — setMode()', () => {
  function makeComp(): CodeScanComponent {
    const c = makeComponent();
    (c as any).mode = signal<'git' | 'zip'>('git');
    (c as any).selectedFile = signal<File | null>({ name: 'x.zip' } as any);
    (c as any).dragOver = signal(true);
    return c;
  }

  it('bascule vers zip et réinitialise fichier + dragOver', () => {
    const c = makeComp();
    c.setMode('zip');
    expect((c as any).mode()).toBe('zip');
    expect((c as any).selectedFile()).toBeNull();
    expect((c as any).dragOver()).toBe(false);
  });

  it('bascule vers git', () => {
    const c = makeComp();
    c.setMode('git');
    expect((c as any).mode()).toBe('git');
  });
});

describe('CodeScanComponent — onDragOver() / onDragLeave()', () => {
  it('onDragOver active dragOver et empêche le comportement par défaut', () => {
    const c = makeComponent();
    (c as any).dragOver = signal(false);
    const ev: any = { preventDefault: vi.fn() };
    c.onDragOver(ev);
    expect(ev.preventDefault).toHaveBeenCalled();
    expect((c as any).dragOver()).toBe(true);
  });

  it('onDragLeave désactive dragOver', () => {
    const c = makeComponent();
    (c as any).dragOver = signal(true);
    c.onDragLeave();
    expect((c as any).dragOver()).toBe(false);
  });
});

describe('CodeScanComponent — onFileSelected()', () => {
  function makeComp() {
    const c = makeComponent();
    (c as any).selectedFile = signal<File | null>(null);
    (c as any).snack = { open: vi.fn() };
    return c;
  }

  it('accepte un fichier .zip', () => {
    const c = makeComp();
    const file = { name: 'archive.ZIP' } as any;
    c.onFileSelected({ target: { files: [file] } } as any);
    expect((c as any).selectedFile()).toBe(file);
    expect((c as any).snack.open).not.toHaveBeenCalled();
  });

  it('rejette un fichier non .zip avec un message', () => {
    const c = makeComp();
    const file = { name: 'archive.txt' } as any;
    c.onFileSelected({ target: { files: [file] } } as any);
    expect((c as any).selectedFile()).toBeNull();
    expect((c as any).snack.open).toHaveBeenCalled();
  });

  it("accepte l'absence de fichier (null)", () => {
    const c = makeComp();
    c.onFileSelected({ target: { files: [] } } as any);
    expect((c as any).selectedFile()).toBeNull();
    expect((c as any).snack.open).not.toHaveBeenCalled();
  });
});

describe('CodeScanComponent — onDrop()', () => {
  function makeComp() {
    const c = makeComponent();
    (c as any).selectedFile = signal<File | null>(null);
    (c as any).dragOver = signal(true);
    (c as any).snack = { open: vi.fn() };
    return c;
  }

  it('accepte un .zip déposé et réinitialise dragOver', () => {
    const c = makeComp();
    const file = { name: 'code.zip' } as any;
    const ev: any = { preventDefault: vi.fn(), dataTransfer: { files: [file] } };
    c.onDrop(ev);
    expect(ev.preventDefault).toHaveBeenCalled();
    expect((c as any).selectedFile()).toBe(file);
    expect((c as any).dragOver()).toBe(false);
  });

  it('ignore un drop sans fichier', () => {
    const c = makeComp();
    const ev: any = { preventDefault: vi.fn(), dataTransfer: { files: [] } };
    c.onDrop(ev);
    expect((c as any).selectedFile()).toBeNull();
    expect((c as any).snack.open).not.toHaveBeenCalled();
  });

  it('rejette un fichier non .zip déposé', () => {
    const c = makeComp();
    const file = { name: 'code.tar' } as any;
    const ev: any = { preventDefault: vi.fn(), dataTransfer: { files: [file] } };
    c.onDrop(ev);
    expect((c as any).selectedFile()).toBeNull();
    expect((c as any).snack.open).toHaveBeenCalled();
  });
});

describe('CodeScanComponent — urlInvalid()', () => {
  it('retourne true si le champ est modifié, invalide et non vide', () => {
    const c = makeComponent();
    (c as any).form = { controls: { repo_url: { dirty: true, invalid: true, value: 'abc' } } };
    expect(c.urlInvalid()).toBe(true);
  });

  it('retourne false si le champ est vide', () => {
    const c = makeComponent();
    (c as any).form = { controls: { repo_url: { dirty: true, invalid: true, value: '' } } };
    expect(c.urlInvalid()).toBe(false);
  });

  it('retourne false si le champ est valide', () => {
    const c = makeComponent();
    (c as any).form = { controls: { repo_url: { dirty: true, invalid: false, value: 'x' } } };
    expect(c.urlInvalid()).toBe(false);
  });

  it('retourne false si le champ est vierge (pas dirty)', () => {
    const c = makeComponent();
    (c as any).form = { controls: { repo_url: { dirty: false, invalid: true, value: 'x' } } };
    expect(c.urlInvalid()).toBe(false);
  });
});

describe('CodeScanComponent — normalizeRepoUrl()', () => {
  it('convertit une URL SSH git@ en HTTPS', () => {
    const c = makeComponent();
    const setValue = vi.fn();
    (c as any).form = {
      controls: { repo_url: { value: 'git@github.com:foo/bar.git', setValue } },
    };
    c.normalizeRepoUrl();
    expect(setValue).toHaveBeenCalledWith('https://github.com/foo/bar.git', { emitEvent: false });
  });

  it("trim les espaces autour de l'URL", () => {
    const c = makeComponent();
    const setValue = vi.fn();
    (c as any).form = {
      controls: { repo_url: { value: '  https://x.com/r.git  ', setValue } },
    };
    c.normalizeRepoUrl();
    expect(setValue).toHaveBeenCalledWith('https://x.com/r.git', { emitEvent: false });
  });

  it('ne modifie pas une URL HTTPS déjà propre', () => {
    const c = makeComponent();
    const setValue = vi.fn();
    (c as any).form = {
      controls: { repo_url: { value: 'https://x.com/r.git', setValue } },
    };
    c.normalizeRepoUrl();
    expect(setValue).not.toHaveBeenCalled();
  });

  it('gère une valeur null sans planter', () => {
    const c = makeComponent();
    const setValue = vi.fn();
    (c as any).form = { controls: { repo_url: { value: null, setValue } } };
    expect(() => c.normalizeRepoUrl()).not.toThrow();
  });
});

describe('CodeScanComponent — isRunning (getter)', () => {
  it('retourne false si aucun scan actif', () => {
    const c = makeComponent();
    (c as any).activeScan = signal(null);
    expect(c.isRunning).toBe(false);
  });

  it('retourne true si le scan actif est pending', () => {
    const c = makeComponent();
    (c as any).activeScan = signal({ id: 1, status: 'pending' });
    expect(c.isRunning).toBe(true);
  });

  it('retourne true si le scan actif est running', () => {
    const c = makeComponent();
    (c as any).activeScan = signal({ id: 1, status: 'running' });
    expect(c.isRunning).toBe(true);
  });

  it('retourne false si le scan actif est terminé', () => {
    const c = makeComponent();
    (c as any).activeScan = signal({ id: 1, status: 'done' });
    expect(c.isRunning).toBe(false);
  });
});

describe('CodeScanComponent — viewScan()', () => {
  it("sélectionne le scan et réinitialise l'onglet sur all", () => {
    const c = makeComponent();
    (c as any).activeScan = signal<any>(null);
    (c as any).activeTab = signal<any>('critical');
    const scan: any = { id: 42, status: 'done' };
    c.viewScan(scan);
    expect((c as any).activeScan()).toBe(scan);
    expect((c as any).activeTab()).toBe('all');
  });
});

describe('CodeScanComponent — loadHistory()', () => {
  function makeComp() {
    const c = makeComponent();
    (c as any).loadingHistory = signal(false);
    (c as any).currentPage = signal(1);
    (c as any).history = signal<any>(null);
    return c;
  }

  it('stocke les données paginées et coupe le chargement', () => {
    const c = makeComp();
    const data = { items: [{ id: 1, status: 'done' }], total: 1, page: 2, size: 10, pages: 1 };
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        { getCodeScans: vi.fn().mockReturnValue(of(data)) };
    c.loadHistory(2);
    expect((c as any).currentPage()).toBe(2);
    expect((c as any).history()).toEqual(data);
    expect((c as any).loadingHistory()).toBe(false);
    expect((c as any).cyberscan.getCodeScans).toHaveBeenCalledWith(2, 10);
  });
});

describe('CodeScanComponent — onPageChange()', () => {
  it('charge la page correspondante (pageIndex + 1)', () => {
    const c = makeComponent();
    const spy = vi.fn();
    (c as any).loadHistory = spy;
    c.onPageChange({ pageIndex: 3 } as any);
    expect(spy).toHaveBeenCalledWith(4);
  });
});

describe('CodeScanComponent — deleteScan()', () => {
  function makeComp() {
    const c = makeComponent();
    (c as any).activeScan = signal<any>(null);
    (c as any).history = signal<any>({
      items: [{ id: 1 }, { id: 2 }],
      total: 2,
      page: 1,
      size: 10,
      pages: 1,
    });
    return c;
  }

  it("retire le scan de l'historique et décrémente le total", () => {
    const c = makeComp();
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        { deleteCodeScan: vi.fn().mockReturnValue(of(void 0)) };
    c.deleteScan({ id: 1 } as any);
    expect((c as any).history().items.map((s: any) => s.id)).toEqual([2]);
    expect((c as any).history().total).toBe(1);
  });

  it("efface le scan actif s'il correspond à celui supprimé", () => {
    const c = makeComp();
    (c as any).activeScan.set({ id: 1 });
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        { deleteCodeScan: vi.fn().mockReturnValue(of(void 0)) };
    c.deleteScan({ id: 1 } as any);
    expect((c as any).activeScan()).toBeNull();
  });

  it("conserve le scan actif s'il ne correspond pas", () => {
    const c = makeComp();
    (c as any).activeScan.set({ id: 2 });
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        { deleteCodeScan: vi.fn().mockReturnValue(of(void 0)) };
    c.deleteScan({ id: 1 } as any);
    expect((c as any).activeScan()).toEqual({ id: 2 });
  });
});

describe('CodeScanComponent — refreshScan()', () => {
  function makeComp() {
    const c = makeComponent();
    (c as any).activeScan = signal<any>(null);
    (c as any).history = signal<any>({
      items: [{ id: 1, status: 'running' }],
      total: 1,
      page: 1,
      size: 10,
      pages: 1,
    });
    return c;
  }

  it("met à jour le scan dans l'historique", () => {
    const c = makeComp();
    const updated = { id: 1, status: 'done' };
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        { getCodeScan: vi.fn().mockReturnValue(of(updated)) };
    (c as any).startPolling = vi.fn();
    c.refreshScan(1);
    expect((c as any).history().items[0]).toEqual(updated);
    expect((c as any).startPolling).not.toHaveBeenCalled();
  });

  it("met à jour le scan actif s'il correspond", () => {
    const c = makeComp();
    (c as any).activeScan.set({ id: 1, status: 'running' });
    const updated = { id: 1, status: 'done' };
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        { getCodeScan: vi.fn().mockReturnValue(of(updated)) };
    (c as any).startPolling = vi.fn();
    c.refreshScan(1);
    expect((c as any).activeScan()).toEqual(updated);
  });

  it('relance le polling si le scan est toujours en cours', () => {
    const c = makeComp();
    const updated = { id: 1, status: 'running' };
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        { getCodeScan: vi.fn().mockReturnValue(of(updated)) };
    const spy = vi.fn();
    (c as any).startPolling = spy;
    c.refreshScan(1);
    expect(spy).toHaveBeenCalledWith(1);
  });
});

describe('CodeScanComponent — submit()', () => {
  function makeComp() {
    const c = makeComponent();
    (c as any).mode = signal<'git' | 'zip'>('git');
    (c as any).submitting = signal(false);
    (c as any).snack = { open: vi.fn() };
    (c as any).startPolling = vi.fn();
    (c as any).loadHistory = vi.fn();
    (c as any).normalizeRepoUrl = vi.fn();
    return c;
  }

  it('délègue à submitZip en mode zip', () => {
    const c = makeComp();
    (c as any).mode.set('zip');
    const spy = vi.fn();
    (c as any).submitZip = spy;
    c.submit();
    expect(spy).toHaveBeenCalled();
  });

  it('ne fait rien si le formulaire est invalide', () => {
    const c = makeComp();
    (c as any).form = { invalid: true, getRawValue: vi.fn() };
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        { triggerCodeScan: vi.fn() };
    c.submit();
    expect((c as any).cyberscan.triggerCodeScan).not.toHaveBeenCalled();
    expect((c as any).submitting()).toBe(false);
  });

  it('lance le scan et réinitialise le formulaire (happy)', () => {
    const c = makeComp();
    const patchValue = vi.fn();
    (c as any).form = {
      invalid: false,
      getRawValue: () => ({ repo_url: 'https://x.com/r.git', github_token: '' }),
      patchValue,
    };
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        {
          triggerCodeScan: vi.fn().mockReturnValue(of({ scan_id: 99 })),
        };
    c.submit();
    expect((c as any).cyberscan.triggerCodeScan).toHaveBeenCalledWith(
      'https://x.com/r.git',
      undefined
    );
    expect((c as any).submitting()).toBe(false);
    expect(patchValue).toHaveBeenCalledWith({ repo_url: '', github_token: '' });
    expect((c as any).startPolling).toHaveBeenCalledWith(99);
    expect((c as any).loadHistory).toHaveBeenCalledWith(1);
  });

  it('passe le token GitHub quand il est fourni', () => {
    const c = makeComp();
    (c as any).form = {
      invalid: false,
      getRawValue: () => ({ repo_url: 'https://x.com/r.git', github_token: 'ghp_1' }),
      patchValue: vi.fn(),
    };
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        {
          triggerCodeScan: vi.fn().mockReturnValue(of({ scan_id: 1 })),
        };
    c.submit();
    expect((c as any).cyberscan.triggerCodeScan).toHaveBeenCalledWith(
      'https://x.com/r.git',
      'ghp_1'
    );
  });
});

describe('CodeScanComponent — submitZip()', () => {
  function makeComp() {
    const c = makeComponent();
    (c as any).submitting = signal(false);
    (c as any).selectedFile = signal<File | null>({ name: 'a.zip' } as any);
    (c as any).snack = { open: vi.fn() };
    (c as any).startPolling = vi.fn();
    (c as any).loadHistory = vi.fn();
    return c;
  }

  it('ne fait rien sans fichier sélectionné', () => {
    const c = makeComp();
    (c as any).selectedFile.set(null);
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        { uploadCodeScan: vi.fn() };
    c.submitZip();
    expect((c as any).cyberscan.uploadCodeScan).not.toHaveBeenCalled();
  });

  it('upload le fichier et réinitialise la sélection (happy)', () => {
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
          uploadCodeScan: vi.fn().mockReturnValue(of({ scan_id: 7 })),
        };
    c.submitZip();
    expect((c as any).cyberscan.uploadCodeScan).toHaveBeenCalled();
    expect((c as any).submitting()).toBe(false);
    expect((c as any).selectedFile()).toBeNull();
    expect((c as any).startPolling).toHaveBeenCalledWith(7);
    expect((c as any).loadHistory).toHaveBeenCalledWith(1);
  });
});
