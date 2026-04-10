/**
 * CodeScanComponent — tests des méthodes utilitaires pures.
 * Ces méthodes ne dépendent pas d'Angular DI ni des signaux.
 * On les teste directement via Object.create sur le prototype.
 */
import { describe, it, expect } from 'vitest';
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
    const data = { findings: [{ severity: 'high' }], summary: { total: 1, critical: 0, high: 1, medium: 0, low: 0 } };
    const scan: any = { results_json: JSON.stringify(data) };
    expect(makeComponent().getResults(scan)).toEqual(data);
  });

  it('retourne null si le JSON est invalide', () => {
    const scan: any = { results_json: 'not-valid-json' };
    expect(makeComponent().getResults(scan)).toBeNull();
  });
});
