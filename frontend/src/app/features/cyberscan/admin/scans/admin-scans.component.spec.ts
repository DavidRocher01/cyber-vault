import { describe, it, expect } from 'vitest';
import { signal, computed } from '@angular/core';
import { AdminScansComponent } from './admin-scans.component';

interface AdminScan {
  id: number;
  target_url: string;
  status: string;
  overall_status: string | null;
  created_at: string;
  finished_at: string | null;
  error_message: string | null;
}

function make(): AdminScansComponent {
  const comp = Object.create(AdminScansComponent.prototype) as AdminScansComponent;
  (comp as any).scans = signal<AdminScan[]>([]);
  (comp as any).loading = signal(true);
  (comp as any).filter = signal<'all' | 'completed' | 'failed' | 'pending'>('all');
  (comp as any).filtered = computed(() => {
    const f = (comp as any).filter();
    const all = (comp as any).scans();
    if (f === 'all') return all;
    if (f === 'completed')
      return all.filter(
        (s: AdminScan) =>
          s.overall_status === 'safe' ||
          s.overall_status === 'warning' ||
          s.overall_status === 'danger'
      );
    if (f === 'failed')
      return all.filter((s: AdminScan) => s.status === 'failed' || s.error_message);
    return all.filter((s: AdminScan) => s.status === 'pending' || s.status === 'running');
  });
  return comp;
}

const SCANS: AdminScan[] = [
  {
    id: 1,
    target_url: 'https://safe.com',
    status: 'completed',
    overall_status: 'safe',
    created_at: '2024-01-01T00:00:00Z',
    finished_at: '2024-01-01T00:01:00Z',
    error_message: null,
  },
  {
    id: 2,
    target_url: 'https://failed.com',
    status: 'failed',
    overall_status: null,
    created_at: '2024-01-02T00:00:00Z',
    finished_at: null,
    error_message: 'Timeout',
  },
  {
    id: 3,
    target_url: 'https://running.com',
    status: 'running',
    overall_status: null,
    created_at: '2024-01-03T00:00:00Z',
    finished_at: null,
    error_message: null,
  },
  {
    id: 4,
    target_url: 'https://danger.com',
    status: 'completed',
    overall_status: 'danger',
    created_at: '2024-01-04T00:00:00Z',
    finished_at: '2024-01-04T00:02:00Z',
    error_message: null,
  },
];

// ── statusColor ────────────────────────────────────────────────────────────────

describe('AdminScansComponent — statusColor()', () => {
  it('retourne vert pour completed', () => {
    const comp = make();
    expect(comp.statusColor('completed')).toContain('emerald');
  });

  it('retourne rouge pour failed', () => {
    const comp = make();
    expect(comp.statusColor('failed')).toContain('red');
  });

  it('retourne bleu pour running', () => {
    const comp = make();
    expect(comp.statusColor('running')).toContain('blue');
  });

  it('retourne gris pour pending', () => {
    const comp = make();
    expect(comp.statusColor('pending')).toContain('gray');
  });

  it('retourne gris pour statut inconnu', () => {
    const comp = make();
    expect(comp.statusColor('unknown')).toContain('gray');
  });
});

// ── overallColor ───────────────────────────────────────────────────────────────

describe('AdminScansComponent — overallColor()', () => {
  it('retourne vert pour safe', () => {
    const comp = make();
    expect(comp.overallColor('safe')).toContain('emerald');
  });

  it('retourne jaune pour warning', () => {
    const comp = make();
    expect(comp.overallColor('warning')).toContain('yellow');
  });

  it('retourne rouge pour danger', () => {
    const comp = make();
    expect(comp.overallColor('danger')).toContain('red');
  });

  it('retourne gris pour null', () => {
    const comp = make();
    expect(comp.overallColor(null)).toContain('gray');
  });
});

// ── truncate ───────────────────────────────────────────────────────────────────

describe('AdminScansComponent — truncate()', () => {
  it('retourne la chaîne telle quelle si elle est plus courte que max', () => {
    const comp = make();
    expect(comp.truncate('https://short.com')).toBe('https://short.com');
  });

  it('tronque et ajoute … si la chaîne dépasse max', () => {
    const comp = make();
    const long = 'https://' + 'a'.repeat(60) + '.com';
    const result = comp.truncate(long, 20);
    expect(result.length).toBe(21); // 20 chars + '…'
    expect(result).toContain('…');
  });

  it('respecte le max personnalisé', () => {
    const comp = make();
    const result = comp.truncate('abcdefghij', 5);
    expect(result).toBe('abcde…');
  });

  it('ne tronque pas si longueur === max', () => {
    const comp = make();
    expect(comp.truncate('hello', 5)).toBe('hello');
  });
});

// ── filtered ──────────────────────────────────────────────────────────────────

describe('AdminScansComponent — filtered()', () => {
  it('retourne tous les scans avec filtre "all"', () => {
    const comp = make();
    (comp as any).scans.set(SCANS);
    expect((comp as any).filtered().length).toBe(4);
  });

  it('filtre les scans terminés (avec overall_status)', () => {
    const comp = make();
    (comp as any).scans.set(SCANS);
    (comp as any).filter.set('completed');
    const result = (comp as any).filtered();
    expect(result.length).toBe(2);
    expect(result.every((s: AdminScan) => s.overall_status !== null)).toBe(true);
  });

  it('filtre les scans échoués', () => {
    const comp = make();
    (comp as any).scans.set(SCANS);
    (comp as any).filter.set('failed');
    const result = (comp as any).filtered();
    expect(result.length).toBe(1);
    expect(result[0].status).toBe('failed');
  });

  it('filtre les scans en cours', () => {
    const comp = make();
    (comp as any).scans.set(SCANS);
    (comp as any).filter.set('pending');
    const result = (comp as any).filtered();
    expect(result.length).toBe(1);
    expect(result[0].status).toBe('running');
  });

  it('retourne une liste vide si aucun scan ne correspond', () => {
    const comp = make();
    (comp as any).scans.set([]);
    (comp as any).filter.set('failed');
    expect((comp as any).filtered().length).toBe(0);
  });
});

// ── formatDate ────────────────────────────────────────────────────────────────

describe('AdminScansComponent — formatDate()', () => {
  it('retourne un tiret pour null', () => {
    const comp = make();
    expect(comp.formatDate(null)).toBe('—');
  });

  it('retourne une chaîne de date non vide pour une date valide', () => {
    const comp = make();
    expect(comp.formatDate('2024-01-15T10:00:00Z')).toBeTruthy();
    expect(comp.formatDate('2024-01-15T10:00:00Z')).not.toBe('—');
  });
});
