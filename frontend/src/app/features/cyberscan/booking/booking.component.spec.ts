/**
 * BookingComponent — tests du pré-remplissage via query params.
 *
 * On contourne Angular DI en créant l'instance directement et en injectant
 * des mocks minimaux, comme le font les autres specs du projet.
 */
import { describe, it, expect } from 'vitest';
import { signal } from '@angular/core';
import { FormBuilder } from '@angular/forms';
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
    name:      [''],
    email:     [''],
    phone:     [''],
    need_type: [''],
    message:   [''],
  });

  // Stub Angular signals (class fields bypassed by Object.create)
  const today = new Date();
  (comp as any).currentYear  = signal(today.getFullYear());
  (comp as any).currentMonth = signal(today.getMonth());
  (comp as any).loadingSlots = signal(false);
  (comp as any).selectedDay  = signal<string | null>(null);
  (comp as any).selectedSlot = signal<any>(null);
  (comp as any).step         = signal('calendar');
  (comp as any).submitting   = signal(false);
  (comp as any).apiError     = signal('');
  (comp as any).cancelMode   = signal(false);
  (comp as any).cancelLoading = signal(false);

  // Stub remaining services so ngOnInit doesn't throw
  (comp as any).titleService = { setTitle: () => {} };
  (comp as any).meta         = { updateTag: () => {} };
  (comp as any).bookingSvc   = { getSlots: () => ({ subscribe: () => {} }) };

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
