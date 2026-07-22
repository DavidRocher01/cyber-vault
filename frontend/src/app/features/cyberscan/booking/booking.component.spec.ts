/**
 * BookingComponent — tests du pré-remplissage via query params.
 *
 * On contourne Angular DI en créant l'instance directement et en injectant
 * des mocks minimaux, comme le font les autres specs du projet.
 */
import { describe, it, expect, vi } from 'vitest';
import { signal } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { of, throwError } from 'rxjs';
import { BookingComponent } from './booking.component';

function makeWithParams(params: Record<string, string>): BookingComponent {
  const comp = Object.create(BookingComponent.prototype) as BookingComponent;

  // Mock ActivatedRoute
  (comp as any).route = {
    snapshot: {
      queryParamMap: { get: (k: string) => params[k] ?? null },
      url: [],
    },
  };

  // Minimal FormBuilder
  const fb = new FormBuilder();
  (comp as any).fb = fb;
  (comp as any).form = fb.group({
    name: [''],
    email: [''],
    phone: [''],
    need_type: [''],
    message: [''],
  });

  // Stub Angular signals (class fields bypassed by Object.create)
  const today = new Date();
  (comp as any).currentYear = signal(today.getFullYear());
  (comp as any).currentMonth = signal(today.getMonth());
  (comp as any).loadingSlots = signal(false);
  (comp as any).selectedDay = signal<string | null>(null);
  (comp as any).selectedSlot = signal<any>(null);
  (comp as any).step = signal('calendar');
  (comp as any).submitting = signal(false);
  (comp as any).apiError = signal('');
  (comp as any).cancelMode = signal(false);
  (comp as any).cancelLoading = signal(false);

  // Stub remaining services so ngOnInit doesn't throw
  (comp as any).titleService = { setTitle: () => {} };
  (comp as any).meta = { updateTag: () => {} };
  (comp as any).bookingSvc = { getSlots: () => ({ subscribe: () => {} }) };

  return comp;
}

describe('BookingComponent — pré-remplissage depuis query params', () => {
  it('ne modifie pas le formulaire si aucun query param', () => {
    const comp = makeWithParams({});
    comp.ngOnInit();
    expect(comp.form.value.message).toBe('');
    expect(comp.form.value.need_type).toBe('');
  });

  it('pré-remplit le message avec le domaine scanné', () => {
    const comp = makeWithParams({ domain: 'https://example.com' });
    comp.ngOnInit();
    expect(comp.form.value.message).toContain('https://example.com');
  });

  it('le message mentionne Audit Flash humain', () => {
    const comp = makeWithParams({ domain: 'https://example.com' });
    comp.ngOnInit();
    expect(comp.form.value.message).toContain('Audit Flash');
  });

  it('pré-remplit need_type avec le type fourni', () => {
    const comp = makeWithParams({ need_type: 'audit-flash' });
    comp.ngOnInit();
    expect(comp.form.value.need_type).toBe('audit-flash');
  });

  it('pré-remplit domain ET need_type simultanément', () => {
    const comp = makeWithParams({ domain: 'https://mysite.fr', need_type: 'audit-flash' });
    comp.ngOnInit();
    expect(comp.form.value.message).toContain('https://mysite.fr');
    expect(comp.form.value.need_type).toBe('audit-flash');
  });

  it('domain vide ne modifie pas le message', () => {
    const comp = makeWithParams({ need_type: 'audit-flash' });
    comp.ngOnInit();
    expect(comp.form.value.message).toBe('');
  });
});

function make(): BookingComponent {
  return Object.create(BookingComponent.prototype) as BookingComponent;
}

describe('BookingComponent — isPast()', () => {
  function makeWithToday(iso: string): BookingComponent {
    const c = make();
    (c as any).today = new Date(iso);
    return c;
  }

  it('retourne true pour une date passée', () => {
    expect(makeWithToday('2026-07-22T10:00:00Z').isPast('2020-01-01')).toBe(true);
  });

  it('retourne false pour une date future', () => {
    expect(makeWithToday('2026-07-22T10:00:00Z').isPast('2099-12-31')).toBe(false);
  });

  it("retourne false pour aujourd'hui (frontière stricte)", () => {
    expect(makeWithToday('2026-07-22T10:00:00Z').isPast('2026-07-22')).toBe(false);
  });
});

describe('BookingComponent — formatDayFr()', () => {
  it('formate une date de milieu de mois', () => {
    expect(make().formatDayFr('2026-07-22')).toBe('22 juillet 2026');
  });

  it('supprime le zéro initial du jour', () => {
    expect(make().formatDayFr('2026-01-05')).toBe('5 janvier 2026');
  });

  it('gère décembre (dernier index de mois)', () => {
    expect(make().formatDayFr('2026-12-31')).toBe('31 décembre 2026');
  });

  it('gère janvier (premier index de mois)', () => {
    expect(make().formatDayFr('2026-01-01')).toBe('1 janvier 2026');
  });
});

describe('BookingComponent — getDayNum()', () => {
  it('extrait le numéro du jour', () => {
    expect(make().getDayNum('2026-07-22')).toBe(22);
  });

  it('extrait un jour à un chiffre', () => {
    expect(make().getDayNum('2026-07-05')).toBe(5);
  });
});

describe('BookingComponent — canPrevMonth()', () => {
  function makeCal(y: number, m: number): BookingComponent {
    const c = make();
    (c as any).today = new Date('2026-07-22T10:00:00Z'); // juillet = index 6, année 2026
    (c as any).currentYear = signal(y);
    (c as any).currentMonth = signal(m);
    return c;
  }

  it('retourne true pour une année future', () => {
    expect(makeCal(2027, 0).canPrevMonth()).toBe(true);
  });

  it('retourne true pour un mois futur de la même année', () => {
    expect(makeCal(2026, 7).canPrevMonth()).toBe(true);
  });

  it('retourne false pour le mois courant', () => {
    expect(makeCal(2026, 6).canPrevMonth()).toBe(false);
  });

  it('retourne false pour un mois passé de la même année', () => {
    expect(makeCal(2026, 5).canPrevMonth()).toBe(false);
  });
});

describe('BookingComponent — prevMonth() / nextMonth()', () => {
  function makeNav(y: number, m: number): BookingComponent {
    const c = make();
    (c as any).currentYear = signal(y);
    (c as any).currentMonth = signal(m);
    (c as any).loadMonth = vi.fn();
    return c;
  }

  it("nextMonth incrémente le mois en cours d'année", () => {
    const c = makeNav(2026, 6);
    c.nextMonth();
    expect((c as any).currentMonth()).toBe(7);
    expect((c as any).currentYear()).toBe(2026);
  });

  it("nextMonth passe de décembre à janvier de l'année suivante", () => {
    const c = makeNav(2026, 11);
    c.nextMonth();
    expect((c as any).currentMonth()).toBe(0);
    expect((c as any).currentYear()).toBe(2027);
  });

  it("prevMonth décrémente le mois en cours d'année", () => {
    const c = makeNav(2026, 6);
    c.prevMonth();
    expect((c as any).currentMonth()).toBe(5);
    expect((c as any).currentYear()).toBe(2026);
  });

  it("prevMonth passe de janvier à décembre de l'année précédente", () => {
    const c = makeNav(2026, 0);
    c.prevMonth();
    expect((c as any).currentMonth()).toBe(11);
    expect((c as any).currentYear()).toBe(2025);
  });

  it('recharge les créneaux après navigation', () => {
    const c = makeNav(2026, 6);
    c.nextMonth();
    c.prevMonth();
    expect((c as any).loadMonth).toHaveBeenCalledTimes(2);
  });
});

describe('BookingComponent — selectDay()', () => {
  function makeSel(available: string[]): BookingComponent {
    const c = make();
    (c as any).today = new Date('2026-07-22T10:00:00Z');
    (c as any).availableDays = signal(new Set(available));
    (c as any).selectedDay = signal<string | null>(null);
    (c as any).selectedSlot = signal<any>('previous');
    return c;
  }

  it('sélectionne un jour futur et disponible', () => {
    const c = makeSel(['2026-08-10']);
    c.selectDay('2026-08-10');
    expect((c as any).selectedDay()).toBe('2026-08-10');
    expect((c as any).selectedSlot()).toBeNull();
  });

  it('ignore un jour passé', () => {
    const c = makeSel(['2020-01-01']);
    c.selectDay('2020-01-01');
    expect((c as any).selectedDay()).toBeNull();
  });

  it('ignore un jour non disponible', () => {
    const c = makeSel([]);
    c.selectDay('2026-08-10');
    expect((c as any).selectedDay()).toBeNull();
  });
});

describe('BookingComponent — selectSlot() / backToCalendar()', () => {
  it("selectSlot mémorise le créneau et passe à l'étape form", () => {
    const c = make();
    (c as any).selectedSlot = signal<any>(null);
    (c as any).step = signal('calendar');
    const slot = { id: 42 } as any;
    c.selectSlot(slot);
    expect((c as any).selectedSlot()).toBe(slot);
    expect((c as any).step()).toBe('form');
  });

  it("backToCalendar revient au calendrier et efface l'erreur", () => {
    const c = make();
    (c as any).step = signal('form');
    (c as any).apiError = signal('boom');
    c.backToCalendar();
    expect((c as any).step()).toBe('calendar');
    expect((c as any).apiError()).toBe('');
  });
});

describe('BookingComponent — loadMonth()', () => {
  function makeLoad(): BookingComponent {
    const c = make();
    (c as any).currentYear = signal(2026);
    (c as any).currentMonth = signal(6);
    (c as any).loadingSlots = signal(false);
    (c as any).selectedDay = signal<string | null>('2026-07-22');
    (c as any).selectedSlot = signal<any>({ id: 1 });
    (c as any).slots = signal<any[]>([]);
    return c;
  }

  it('demande le mois formaté et stocke les créneaux', () => {
    const c = makeLoad();
    const getSlots = vi.fn().mockReturnValue(of([{ id: 1 }, { id: 2 }]));
    (c as any).bookingSvc = { getSlots };
    c.loadMonth();
    expect(getSlots).toHaveBeenCalledWith('2026-07');
    expect((c as any).slots()).toEqual([{ id: 1 }, { id: 2 }]);
    expect((c as any).loadingSlots()).toBe(false);
    expect((c as any).selectedDay()).toBeNull();
    expect((c as any).selectedSlot()).toBeNull();
  });

  it("vide les créneaux en cas d'erreur", () => {
    const c = makeLoad();
    (c as any).bookingSvc = { getSlots: vi.fn().mockReturnValue(throwError(() => new Error('x'))) };
    c.loadMonth();
    expect((c as any).slots()).toEqual([]);
    expect((c as any).loadingSlots()).toBe(false);
  });
});

describe('BookingComponent — submit()', () => {
  function makeSubmit(overrides: Partial<Record<string, unknown>> = {}): BookingComponent {
    const c = make();
    const fb = new FormBuilder();
    (c as any).form = fb.group({
      name: ['Jean Dupont', [Validators.required]],
      email: ['jean@example.com', [Validators.required, Validators.email]],
      phone: [''],
      need_type: ['audit-flash', [Validators.required]],
      message: [''],
    });
    (c as any).submitting = signal(false);
    (c as any).apiError = signal('');
    (c as any).confirmedMessage = signal('');
    (c as any).step = signal('form');
    (c as any).selectedSlot = signal<any>({ id: 7 });
    Object.assign(c as any, overrides);
    return c;
  }

  it('ne fait rien si le formulaire est invalide', () => {
    const c = makeSubmit();
    (c as any).form.controls.email.setValue('');
    const book = vi.fn();
    (c as any).bookingSvc = { book };
    c.submit();
    expect(book).not.toHaveBeenCalled();
  });

  it('ne fait rien si aucun créneau sélectionné', () => {
    const c = makeSubmit({ selectedSlot: signal(null) });
    const book = vi.fn();
    (c as any).bookingSvc = { book };
    c.submit();
    expect(book).not.toHaveBeenCalled();
  });

  it('ne fait rien si une soumission est déjà en cours', () => {
    const c = makeSubmit({ submitting: signal(true) });
    const book = vi.fn();
    (c as any).bookingSvc = { book };
    c.submit();
    expect(book).not.toHaveBeenCalled();
  });

  it("réserve et passe à l'étape confirmed en cas de succès", () => {
    const c = makeSubmit();
    const book = vi.fn().mockReturnValue(of({ message: 'Réservé !', booking_id: 99 }));
    (c as any).bookingSvc = { book };
    c.submit();
    expect(book).toHaveBeenCalledWith(
      expect.objectContaining({ slot_id: 7, name: 'Jean Dupont', email: 'jean@example.com' })
    );
    expect((c as any).confirmedMessage()).toBe('Réservé !');
    expect((c as any).step()).toBe('confirmed');
    expect((c as any).submitting()).toBe(false);
  });

  it('convertit les champs vides en undefined dans le payload', () => {
    const c = makeSubmit();
    const book = vi.fn().mockReturnValue(of({ message: 'ok', booking_id: 1 }));
    (c as any).bookingSvc = { book };
    c.submit();
    const payload = book.mock.calls[0][0];
    expect(payload.phone).toBeUndefined();
    expect(payload.message).toBeUndefined();
  });

  it("affiche le détail d'erreur renvoyé par l'API", () => {
    const c = makeSubmit();
    (c as any).bookingSvc = {
      book: vi.fn().mockReturnValue(throwError(() => ({ error: { detail: 'Créneau pris' } }))),
    };
    c.submit();
    expect((c as any).apiError()).toBe('Créneau pris');
    expect((c as any).submitting()).toBe(false);
  });

  it("affiche un message générique si l'erreur n'a pas de détail", () => {
    const c = makeSubmit();
    (c as any).bookingSvc = { book: vi.fn().mockReturnValue(throwError(() => ({}))) };
    c.submit();
    expect((c as any).apiError()).toBe('Une erreur est survenue. Réessayez.');
  });
});
