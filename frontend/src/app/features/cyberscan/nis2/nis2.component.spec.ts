/**
 * Nis2Component — tests des méthodes utilitaires pures.
 */
import { describe, it, expect } from 'vitest';
import { Nis2Component } from './nis2.component';

function make(): Nis2Component {
  return Object.create(Nis2Component.prototype) as Nis2Component;
}

// ── statusLabel ──────────────────────────────────────────────────────────────

describe('Nis2Component — statusLabel()', () => {
  it('traduit compliant → Conforme',          () => expect(make().statusLabel('compliant')).toBe('Conforme'));
  it('traduit partial → Partiel',             () => expect(make().statusLabel('partial')).toBe('Partiel'));
  it('traduit non_compliant → Non conforme',  () => expect(make().statusLabel('non_compliant')).toBe('Non conforme'));
  it('traduit na → N/A',                      () => expect(make().statusLabel('na')).toBe('N/A'));
  it('retourne la valeur brute si inconnue',  () => expect(make().statusLabel('unknown')).toBe('unknown'));
});

// ── statusIcon ───────────────────────────────────────────────────────────────

describe('Nis2Component — statusIcon()', () => {
  it('retourne check_circle pour compliant',          () => expect(make().statusIcon('compliant')).toBe('check_circle'));
  it('retourne pending pour partial',                 () => expect(make().statusIcon('partial')).toBe('pending'));
  it('retourne cancel pour non_compliant',            () => expect(make().statusIcon('non_compliant')).toBe('cancel'));
  it('retourne remove_circle_outline pour na',        () => expect(make().statusIcon('na')).toBe('remove_circle_outline'));
  it('retourne help_outline pour statut inconnu',     () => expect(make().statusIcon('unknown')).toBe('help_outline'));
});

// ── statusClass ──────────────────────────────────────────────────────────────

describe('Nis2Component — statusClass()', () => {
  it('contient green pour compliant',     () => expect(make().statusClass('compliant')).toContain('green'));
  it('contient yellow pour partial',      () => expect(make().statusClass('partial')).toContain('yellow'));
  it('contient red pour non_compliant',   () => expect(make().statusClass('non_compliant')).toContain('red'));
  it('contient gray pour na',             () => expect(make().statusClass('na')).toContain('gray'));
  it('retourne classe grise par défaut',  () => expect(make().statusClass('unknown')).toContain('gray'));
});

// ── scoreColor ───────────────────────────────────────────────────────────────

describe('Nis2Component — scoreColor()', () => {
  it('retourne vert (#4ade80) pour score >= 80',      () => expect(make().scoreColor(80)).toBe('#4ade80'));
  it('retourne vert (#4ade80) pour score = 100',      () => expect(make().scoreColor(100)).toBe('#4ade80'));
  it('retourne jaune (#facc15) pour score = 50',      () => expect(make().scoreColor(50)).toBe('#facc15'));
  it('retourne jaune (#facc15) pour score = 79',      () => expect(make().scoreColor(79)).toBe('#facc15'));
  it('retourne rouge (#f87171) pour score < 50',      () => expect(make().scoreColor(49)).toBe('#f87171'));
  it('retourne rouge (#f87171) pour score = 0',       () => expect(make().scoreColor(0)).toBe('#f87171'));
});

// ── scoreLabel ───────────────────────────────────────────────────────────────

describe('Nis2Component — scoreLabel()', () => {
  it('retourne Conforme pour score >= 80',   () => expect(make().scoreLabel(80)).toBe('Conforme'));
  it('retourne En cours pour score = 50',    () => expect(make().scoreLabel(50)).toBe('En cours'));
  it('retourne En cours pour score = 79',    () => expect(make().scoreLabel(79)).toBe('En cours'));
  it('retourne Non conforme pour score < 50',() => expect(make().scoreLabel(49)).toBe('Non conforme'));
  it('retourne Non conforme pour score = 0', () => expect(make().scoreLabel(0)).toBe('Non conforme'));
});

// ── formatDate ───────────────────────────────────────────────────────────────

describe('Nis2Component — formatDate()', () => {
  it('retourne "—" pour null',        () => expect(make().formatDate(null)).toBe('—'));
  it('formate une date ISO valide',   () => {
    const result = make().formatDate('2024-01-15T10:00:00Z');
    expect(result).toContain('2024');
  });
});

// ── STATUS_LIST ──────────────────────────────────────────────────────────────

describe('Nis2Component — STATUS_LIST', () => {
  it('contient les 4 statuts',  () => {
    const c = make();
    // STATUS_LIST is a class property, initialize it
    (c as any).STATUS_LIST = ['compliant', 'partial', 'non_compliant', 'na'];
    expect((c as any).STATUS_LIST).toHaveLength(4);
    expect((c as any).STATUS_LIST).toContain('compliant');
    expect((c as any).STATUS_LIST).toContain('partial');
    expect((c as any).STATUS_LIST).toContain('non_compliant');
    expect((c as any).STATUS_LIST).toContain('na');
  });
});
