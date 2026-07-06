import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { signal } from '@angular/core';
import { FormBuilder } from '@angular/forms';
import { of, throwError } from 'rxjs';
import { ConsultantProfileComponent } from './consultant-profile.component';

const PROFILE = {
  email: 'jean@acme.fr',
  display_name: 'Jean Dupont',
  company_name: 'Acme SAS',
  phone: '0102030405',
};

function make(overrides: { rssi?: any } = {}): ConsultantProfileComponent {
  const comp = Object.create(ConsultantProfileComponent.prototype) as ConsultantProfileComponent;
  const fb = new FormBuilder();
  (comp as any).fb = fb;
  (comp as any).form = fb.nonNullable.group({
    display_name: [''],
    company_name: [''],
    phone: [''],
  });
  (comp as any).loading = signal(true);
  (comp as any).saving = signal(false);
  (comp as any).saved = signal(false);
  (comp as any).rssi = {
    getProfile: vi.fn(() => of(PROFILE)),
    updateProfile: vi.fn(() => of(PROFILE)),
    ...overrides.rssi,
  };
  (comp as any).router = { navigate: vi.fn() };
  return comp;
}

// ── ngOnInit : chargement du profil ─────────────────────────────────────────────

describe('ConsultantProfileComponent — ngOnInit()', () => {
  it('appelle rssi.getProfile', () => {
    const comp = make();
    comp.ngOnInit();
    expect((comp as any).rssi.getProfile).toHaveBeenCalledTimes(1);
  });

  it('patche le formulaire avec les valeurs du profil', () => {
    const comp = make();
    comp.ngOnInit();
    expect(comp.form.value.display_name).toBe('Jean Dupont');
    expect(comp.form.value.company_name).toBe('Acme SAS');
    expect(comp.form.value.phone).toBe('0102030405');
  });

  it('passe loading à false après succès', () => {
    const comp = make();
    comp.ngOnInit();
    expect((comp as any).loading()).toBe(false);
  });

  it('remplace les champs null du profil par des chaînes vides', () => {
    const comp = make({
      rssi: {
        getProfile: vi.fn(() =>
          of({ email: 'x@y.fr', display_name: null, company_name: null, phone: null })
        ),
      },
    });
    comp.ngOnInit();
    expect(comp.form.value.display_name).toBe('');
    expect(comp.form.value.company_name).toBe('');
    expect(comp.form.value.phone).toBe('');
  });

  it('passe loading à false même en cas d’erreur', () => {
    const comp = make({
      rssi: { getProfile: vi.fn(() => throwError(() => new Error('boom'))) },
    });
    comp.ngOnInit();
    expect((comp as any).loading()).toBe(false);
  });

  it('ne modifie pas le formulaire en cas d’erreur', () => {
    const comp = make({
      rssi: { getProfile: vi.fn(() => throwError(() => new Error('boom'))) },
    });
    comp.ngOnInit();
    expect(comp.form.value.display_name).toBe('');
  });
});

// ── save : sauvegarde du profil ─────────────────────────────────────────────────

describe('ConsultantProfileComponent — save()', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('envoie les valeurs brutes du formulaire à updateProfile', () => {
    const comp = make();
    comp.form.setValue({ display_name: 'A B', company_name: 'C', phone: '06' });
    comp.save();
    expect((comp as any).rssi.updateProfile).toHaveBeenCalledWith({
      display_name: 'A B',
      company_name: 'C',
      phone: '06',
    });
  });

  it('passe saving à false et saved à true après succès', () => {
    const comp = make();
    comp.save();
    expect((comp as any).saving()).toBe(false);
    expect((comp as any).saved()).toBe(true);
  });

  it('réinitialise saved à false après 2500 ms', () => {
    const comp = make();
    comp.save();
    expect((comp as any).saved()).toBe(true);
    vi.advanceTimersByTime(2500);
    expect((comp as any).saved()).toBe(false);
  });

  it('maintient saved à true avant l’échéance du timer', () => {
    const comp = make();
    comp.save();
    vi.advanceTimersByTime(2499);
    expect((comp as any).saved()).toBe(true);
  });

  it('passe saving à false et laisse saved à false en cas d’erreur', () => {
    const comp = make({
      rssi: { updateProfile: vi.fn(() => throwError(() => new Error('boom'))) },
    });
    comp.save();
    expect((comp as any).saving()).toBe(false);
    expect((comp as any).saved()).toBe(false);
  });
});

// ── displayInitials ─────────────────────────────────────────────────────────────

describe('ConsultantProfileComponent — displayInitials', () => {
  it('retourne les initiales des deux premiers mots en majuscules', () => {
    const comp = make();
    comp.form.get('display_name')!.setValue('Jean Dupont');
    expect(comp.displayInitials).toBe('JD');
  });

  it('limite à deux initiales pour un nom de trois mots', () => {
    const comp = make();
    comp.form.get('display_name')!.setValue('Jean Michel Dupont');
    expect(comp.displayInitials).toBe('JM');
  });

  it('retourne une seule initiale pour un mot unique', () => {
    const comp = make();
    comp.form.get('display_name')!.setValue('Alice');
    expect(comp.displayInitials).toBe('A');
  });

  it('retourne une chaîne vide quand le nom est vide', () => {
    const comp = make();
    comp.form.get('display_name')!.setValue('');
    expect(comp.displayInitials).toBe('');
  });

  it('met les initiales en majuscules', () => {
    const comp = make();
    comp.form.get('display_name')!.setValue('bob martin');
    expect(comp.displayInitials).toBe('BM');
  });
});

// ── back ────────────────────────────────────────────────────────────────────────

describe('ConsultantProfileComponent — back()', () => {
  it('navigue vers /consultant', () => {
    const comp = make();
    comp.back();
    expect((comp as any).router.navigate).toHaveBeenCalledWith(['/consultant']);
  });
});
