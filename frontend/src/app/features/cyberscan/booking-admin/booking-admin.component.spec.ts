import { describe, it, expect } from 'vitest';
import { signal } from '@angular/core';
import { BookingAdminComponent } from './booking-admin.component';

function make(initialMonth?: string): BookingAdminComponent {
  const comp = Object.create(BookingAdminComponent.prototype) as BookingAdminComponent;
  (comp as any).currentMonth = signal(initialMonth ?? new Date().toISOString().slice(0, 7));
  (comp as any).slots = signal([]);
  (comp as any).bookings = signal([]);
  (comp as any).loading = signal(false);
  (comp as any).http = { get: () => ({ subscribe: () => {} }) };
  (comp as any).adminKey = signal('test-key');
  return comp;
}

// ── prevMonth ─────────────────────────────────────────────────────────────────

describe('BookingAdminComponent — prevMonth()', () => {
  it('recule d\'un mois (cas standard)', () => {
    const comp = make('2026-05');
    comp.prevMonth();
    expect((comp as any).currentMonth()).toBe('2026-04');
  });

  it('passe de janvier à décembre de l\'année précédente', () => {
    const comp = make('2026-01');
    comp.prevMonth();
    expect((comp as any).currentMonth()).toBe('2025-12');
  });

  it('préserve le format YYYY-MM', () => {
    const comp = make('2026-03');
    comp.prevMonth();
    expect((comp as any).currentMonth()).toMatch(/^\d{4}-\d{2}$/);
  });

  it('retourne 2026-01 depuis 2026-02', () => {
    const comp = make('2026-02');
    comp.prevMonth();
    expect((comp as any).currentMonth()).toBe('2026-01');
  });
});

// ── nextMonth ─────────────────────────────────────────────────────────────────

describe('BookingAdminComponent — nextMonth()', () => {
  it('avance d\'un mois (cas standard)', () => {
    const comp = make('2026-05');
    comp.nextMonth();
    expect((comp as any).currentMonth()).toBe('2026-06');
  });

  it('passe de décembre à janvier de l\'année suivante', () => {
    const comp = make('2025-12');
    comp.nextMonth();
    expect((comp as any).currentMonth()).toBe('2026-01');
  });

  it('préserve le format YYYY-MM', () => {
    const comp = make('2026-09');
    comp.nextMonth();
    expect((comp as any).currentMonth()).toMatch(/^\d{4}-\d{2}$/);
  });

  it('retourne 2026-10 depuis 2026-09', () => {
    const comp = make('2026-09');
    comp.nextMonth();
    expect((comp as any).currentMonth()).toBe('2026-10');
  });
});

// ── navigation symétrique ─────────────────────────────────────────────────────

describe('BookingAdminComponent — navigation symétrique', () => {
  it('next puis prev revient au même mois', () => {
    const comp = make('2026-05');
    const original = (comp as any).currentMonth();
    comp.nextMonth();
    comp.prevMonth();
    expect((comp as any).currentMonth()).toBe(original);
  });

  it('prev puis next revient au même mois', () => {
    const comp = make('2026-05');
    const original = (comp as any).currentMonth();
    comp.prevMonth();
    comp.nextMonth();
    expect((comp as any).currentMonth()).toBe(original);
  });

  it('12 next depuis janvier atteint janvier de l\'année suivante', () => {
    const comp = make('2025-01');
    for (let i = 0; i < 12; i++) comp.nextMonth();
    expect((comp as any).currentMonth()).toBe('2026-01');
  });
});

// ── formatMonthLabel ──────────────────────────────────────────────────────────

describe('BookingAdminComponent — formatMonthLabel()', () => {
  it('retourne une chaîne non vide', () => {
    const comp = make('2026-05');
    expect(comp.formatMonthLabel()).toBeTruthy();
  });

  it('contient l\'année', () => {
    const comp = make('2026-05');
    expect(comp.formatMonthLabel()).toContain('2026');
  });

  it('contient le nom du mois en français', () => {
    const comp = make('2026-05');
    expect(comp.formatMonthLabel().toLowerCase()).toContain('mai');
  });

  it('affiche janvier pour 2026-01', () => {
    const comp = make('2026-01');
    expect(comp.formatMonthLabel().toLowerCase()).toContain('janvier');
  });
});
