import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { signal } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { of, throwError } from 'rxjs';
import { ConsultantProfileComponent } from './consultant-profile.component';

const PROFILE = {
  email: 'jean@acme.fr',
  display_name: 'Jean Dupont',
  company_name: 'Acme SAS',
  phone: '0102030405',
};

// Doit rester aligne sur le formulaire du composant : sans les validateurs, les
// tests ne verraient pas les branches de validation.
const PHONE_PATTERN = /^[+0-9][0-9 .\-()]{5,}$/;

function make(overrides: { rssi?: any } = {}): ConsultantProfileComponent {
  const comp = Object.create(ConsultantProfileComponent.prototype) as ConsultantProfileComponent;
  const fb = new FormBuilder();
  (comp as any).fb = fb;
  (comp as any).form = fb.nonNullable.group({
    display_name: ['', [Validators.required, Validators.maxLength(120)]],
    company_name: ['', [Validators.maxLength(120)]],
    phone: ['', [Validators.pattern(PHONE_PATTERN), Validators.maxLength(30)]],
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
  (comp as any).snack = { open: vi.fn() };
  return comp;
}

/** Remplit le formulaire avec des valeurs valides (le nom est obligatoire). */
function fillValid(comp: ConsultantProfileComponent): void {
  comp.form.setValue({ display_name: 'A B', company_name: 'C', phone: '0612345678' });
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

  it('laisse le formulaire pristine après chargement (pas de faux « non enregistré »)', () => {
    const comp = make();
    comp.ngOnInit();
    expect(comp.form.pristine).toBe(true);
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

  it('signale l’échec de chargement à l’utilisateur (avant : silencieux)', () => {
    const comp = make({
      rssi: { getProfile: vi.fn(() => throwError(() => new Error('boom'))) },
    });
    comp.ngOnInit();
    expect((comp as any).snack.open).toHaveBeenCalledTimes(1);
  });
});

// ── save : sauvegarde du profil ─────────────────────────────────────────────────

describe('ConsultantProfileComponent — save()', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('envoie les valeurs brutes du formulaire à updateProfile', () => {
    const comp = make();
    comp.form.setValue({ display_name: 'A B', company_name: 'C', phone: '0612345678' });
    comp.save();
    expect((comp as any).rssi.updateProfile).toHaveBeenCalledWith({
      display_name: 'A B',
      company_name: 'C',
      phone: '0612345678',
    });
  });

  it('passe saving à false et saved à true après succès', () => {
    const comp = make();
    fillValid(comp);
    comp.save();
    expect((comp as any).saving()).toBe(false);
    expect((comp as any).saved()).toBe(true);
  });

  it('repasse le formulaire en pristine après succès', () => {
    const comp = make();
    fillValid(comp);
    comp.form.markAsDirty();
    comp.save();
    expect(comp.form.pristine).toBe(true);
  });

  it('réinitialise saved à false après 2500 ms', () => {
    const comp = make();
    fillValid(comp);
    comp.save();
    expect((comp as any).saved()).toBe(true);
    vi.advanceTimersByTime(2500);
    expect((comp as any).saved()).toBe(false);
  });

  it('maintient saved à true avant l’échéance du timer', () => {
    const comp = make();
    fillValid(comp);
    comp.save();
    vi.advanceTimersByTime(2499);
    expect((comp as any).saved()).toBe(true);
  });

  it('passe saving à false et laisse saved à false en cas d’erreur', () => {
    const comp = make({
      rssi: { updateProfile: vi.fn(() => throwError(() => new Error('boom'))) },
    });
    fillValid(comp);
    comp.save();
    expect((comp as any).saving()).toBe(false);
    expect((comp as any).saved()).toBe(false);
  });

  it('signale l’échec de sauvegarde à l’utilisateur (avant : silencieux)', () => {
    const comp = make({
      rssi: { updateProfile: vi.fn(() => throwError(() => new Error('boom'))) },
    });
    fillValid(comp);
    comp.save();
    expect((comp as any).snack.open).toHaveBeenCalledTimes(1);
  });

  it('n’envoie rien quand le nom affiché est vide', () => {
    const comp = make();
    comp.save();
    expect((comp as any).rssi.updateProfile).not.toHaveBeenCalled();
  });

  it('marque les champs comme touchés sur submit invalide (pour afficher l’erreur)', () => {
    const comp = make();
    comp.save();
    expect(comp.form.get('display_name')!.touched).toBe(true);
  });

  it('n’envoie rien quand le téléphone est mal formé', () => {
    const comp = make();
    comp.form.setValue({ display_name: 'A B', company_name: '', phone: 'abc' });
    comp.save();
    expect((comp as any).rssi.updateProfile).not.toHaveBeenCalled();
  });

  it('accepte un numéro au format international', () => {
    const comp = make();
    comp.form.setValue({ display_name: 'A B', company_name: '', phone: '+33 6 12 34 56 78' });
    comp.save();
    expect((comp as any).rssi.updateProfile).toHaveBeenCalledTimes(1);
  });

  it('accepte un téléphone vide (champ facultatif)', () => {
    const comp = make();
    comp.form.setValue({ display_name: 'A B', company_name: '', phone: '' });
    comp.save();
    expect((comp as any).rssi.updateProfile).toHaveBeenCalledTimes(1);
  });
});

// ── isInvalid ───────────────────────────────────────────────────────────────────

describe('ConsultantProfileComponent — isInvalid()', () => {
  it('reste false sur un champ invalide mais jamais touché', () => {
    const comp = make();
    expect(comp.isInvalid('display_name')).toBe(false);
  });

  it('passe true une fois le champ touché', () => {
    const comp = make();
    comp.form.get('display_name')!.markAsTouched();
    expect(comp.isInvalid('display_name')).toBe(true);
  });

  it('reste false sur un champ valide et touché', () => {
    const comp = make();
    comp.form.get('display_name')!.setValue('Jean Dupont');
    comp.form.get('display_name')!.markAsTouched();
    expect(comp.isInvalid('display_name')).toBe(false);
  });

  it('retourne false pour un champ inconnu', () => {
    const comp = make();
    expect(comp.isInvalid('inexistant')).toBe(false);
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

  it('ignore les espaces multiples (avant : initiale vide)', () => {
    const comp = make();
    comp.form.get('display_name')!.setValue('  Jean   Dupont');
    expect(comp.displayInitials).toBe('JD');
  });
});

// ── back ────────────────────────────────────────────────────────────────────────

describe('ConsultantProfileComponent — back()', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('navigue vers /consultant quand rien n’a été modifié', () => {
    const comp = make();
    comp.back();
    expect((comp as any).router.navigate).toHaveBeenCalledWith(['/consultant']);
  });

  it('demande confirmation quand le formulaire est modifié', () => {
    const comp = make();
    const confirmSpy = vi.fn(() => true);
    vi.stubGlobal('confirm', confirmSpy);
    comp.form.markAsDirty();
    comp.back();
    expect(confirmSpy).toHaveBeenCalledTimes(1);
    expect((comp as any).router.navigate).toHaveBeenCalledWith(['/consultant']);
  });

  it('reste sur la page si l’utilisateur annule', () => {
    const comp = make();
    vi.stubGlobal(
      'confirm',
      vi.fn(() => false)
    );
    comp.form.markAsDirty();
    comp.back();
    expect((comp as any).router.navigate).not.toHaveBeenCalled();
  });
});
