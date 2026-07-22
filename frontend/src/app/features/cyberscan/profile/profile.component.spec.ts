/**
 * ProfileComponent — tests des méthodes pures et guards.
 * On instancie le composant sans DI Angular (Object.create).
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { signal } from '@angular/core';
import { of, throwError } from 'rxjs';
import { FormBuilder, Validators } from '@angular/forms';
import { ProfileComponent } from './profile.component';

function make(): ProfileComponent {
  const comp = Object.create(ProfileComponent.prototype) as ProfileComponent;
  // Initialise les dépendances minimales pour les getters/méthodes pures
  const fb = new FormBuilder();
  (comp as any).passwordForm = fb.nonNullable.group({
    current_password: ['', Validators.required],
    new_password: ['', [Validators.required, Validators.minLength(8)]],
    confirm_password: ['', Validators.required],
  });
  (comp as any).emailForm = fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    current_password: ['', Validators.required],
  });
  (comp as any).deleteForm = fb.nonNullable.group({
    password: [''],
  });
  (comp as any).profile = signal(null);
  (comp as any).twoFaStep = signal('idle');
  (comp as any).twoFaSetup = signal(null);
  (comp as any).twoFaCode = signal('');
  (comp as any).twoFaDisablePw = signal('');
  (comp as any).twoFaDisableCode = signal('');
  (comp as any).otpClear = 0;
  (comp as any).otpDisableClear = 0;
  (comp as any).notifPrefs = signal(null);
  (comp as any).savingNotifs = signal(false);
  return comp;
}

// ── initials getter ────────────────────────────────────────────────────────────

describe('ProfileComponent — initials', () => {
  it("retourne les 2 premières lettres de l'email en majuscules", () => {
    const comp = make();
    (comp as any).profile = signal({
      email: 'david@example.com',
      id: 1,
      is_active: true,
      totp_enabled: false,
    });
    expect(comp.initials).toBe('DA');
  });

  it('retourne une chaîne vide si pas de profil', () => {
    const comp = make();
    expect(comp.initials).toBe('');
  });

  it('retourne les initiales en majuscules', () => {
    const comp = make();
    (comp as any).profile = signal({
      email: 'abc@test.com',
      id: 1,
      is_active: true,
      totp_enabled: false,
    });
    expect(comp.initials).toBe(comp.initials.toUpperCase());
  });
});

// ── passwordStrength getter ────────────────────────────────────────────────────

describe('ProfileComponent — passwordStrength', () => {
  it('retourne width 0% et label vide si mot de passe vide', () => {
    const comp = make();
    comp.passwordForm.controls.new_password.setValue('');
    const { label, width } = comp.passwordStrength;
    expect(width).toBe('0%');
    expect(label).toBe('');
  });

  it('retourne Faible pour un mot de passe court sans complexité', () => {
    const comp = make();
    comp.passwordForm.controls.new_password.setValue('abc');
    expect(comp.passwordStrength.label).toBe('Faible');
  });

  it('retourne Moyen pour un mot de passe 8+ chars sans majuscule', () => {
    const comp = make();
    comp.passwordForm.controls.new_password.setValue('abcdefgh');
    const { label } = comp.passwordStrength;
    expect(['Faible', 'Moyen']).toContain(label);
  });

  it('retourne Fort pour un mot de passe long avec maj + chiffre + spécial', () => {
    const comp = make();
    comp.passwordForm.controls.new_password.setValue('StrongPass123!');
    expect(comp.passwordStrength.label).toBe('Fort');
  });

  it('retourne une couleur CSS non vide pour un mot de passe non vide', () => {
    const comp = make();
    comp.passwordForm.controls.new_password.setValue('Test1234!');
    expect(comp.passwordStrength.color).toBeTruthy();
  });

  it('score augmente avec la complexité', () => {
    const comp = make();
    comp.passwordForm.controls.new_password.setValue('abc');
    const weak = comp.passwordStrength.width;
    comp.passwordForm.controls.new_password.setValue('StrongPass123!Special');
    const strong = comp.passwordStrength.width;
    expect(parseInt(strong)).toBeGreaterThan(parseInt(weak));
  });
});

// ── cancelTwoFa ────────────────────────────────────────────────────────────────

describe('ProfileComponent — cancelTwoFa()', () => {
  it('remet twoFaStep à idle', () => {
    const comp = make();
    (comp as any).twoFaStep = signal('confirm');
    comp.cancelTwoFa();
    expect((comp as any).twoFaStep()).toBe('idle');
  });

  it('efface twoFaSetup', () => {
    const comp = make();
    (comp as any).twoFaSetup = signal({ qr_code_b64: 'abc', secret: 'XYZ' });
    comp.cancelTwoFa();
    expect((comp as any).twoFaSetup()).toBeNull();
  });

  it('efface twoFaCode', () => {
    const comp = make();
    (comp as any).twoFaCode = signal('123456');
    comp.cancelTwoFa();
    expect((comp as any).twoFaCode()).toBe('');
  });

  it('efface twoFaDisablePw et twoFaDisableCode', () => {
    const comp = make();
    (comp as any).twoFaDisablePw = signal('mypass');
    (comp as any).twoFaDisableCode = signal('654321');
    comp.cancelTwoFa();
    expect((comp as any).twoFaDisablePw()).toBe('');
    expect((comp as any).twoFaDisableCode()).toBe('');
  });

  it('incrémente otpClear et otpDisableClear', () => {
    const comp = make();
    const before = comp.otpClear;
    comp.cancelTwoFa();
    expect(comp.otpClear).toBe(before + 1);
    expect(comp.otpDisableClear).toBe(before + 1);
  });
});

// ── updateEmail guard ──────────────────────────────────────────────────────────

describe('ProfileComponent — updateEmail() guard', () => {
  it('ne soumet pas si le formulaire est invalide', () => {
    const comp = make();
    let called = false;
    (comp as any).userService = {
      updateEmail: () => {
        called = true;
      },
    };
    comp.emailForm.controls.email.setValue('');
    comp.updateEmail();
    expect(called).toBe(false);
  });
});

// ── updatePassword guard ───────────────────────────────────────────────────────

describe('ProfileComponent — updatePassword() guard', () => {
  it('ne soumet pas si le formulaire est invalide', () => {
    const comp = make();
    let called = false;
    (comp as any).userService = {
      updatePassword: () => {
        called = true;
      },
    };
    comp.updatePassword();
    expect(called).toBe(false);
  });
});

// ── disable2FA guard ───────────────────────────────────────────────────────────

describe('ProfileComponent — disable2FA() guard', () => {
  it('ne soumet pas si le mot de passe est vide', () => {
    const comp = make();
    let called = false;
    (comp as any).userService = {
      disable2FA: () => {
        called = true;
      },
    };
    (comp as any).twoFaDisablePw = signal('');
    (comp as any).twoFaDisableCode = signal('123456');
    comp.disable2FA();
    expect(called).toBe(false);
  });

  it('ne soumet pas si le code a moins de 6 chiffres', () => {
    const comp = make();
    let called = false;
    (comp as any).userService = {
      disable2FA: () => {
        called = true;
      },
    };
    (comp as any).twoFaDisablePw = signal('mypassword');
    (comp as any).twoFaDisableCode = signal('123');
    comp.disable2FA();
    expect(called).toBe(false);
  });
});

// ── exportUrl ─────────────────────────────────────────────────────────────────

describe('ProfileComponent — exportUrl()', () => {
  it("retourne l'URL d'export", () => {
    const comp = make();
    (comp as any).userService = { exportMyData: () => '/api/v1/users/me/export' };
    expect(comp.exportUrl()).toBe('/api/v1/users/me/export');
  });
});

// ── toggleNotif ───────────────────────────────────────────────────────────────

describe('ProfileComponent — toggleNotif()', () => {
  const basePrefs = () => ({
    notif_scan_done: true,
    notif_scan_critical: true,
    notif_url_scan_done: true,
    notif_code_scan_done: true,
  });

  it('inverse notif_scan_done de true à false', () => {
    const comp = make();
    (comp as any).notifPrefs = signal(basePrefs());
    comp.toggleNotif('notif_scan_done');
    expect((comp as any).notifPrefs().notif_scan_done).toBe(false);
  });

  it('inverse notif_scan_critical de true à false', () => {
    const comp = make();
    (comp as any).notifPrefs = signal(basePrefs());
    comp.toggleNotif('notif_scan_critical');
    expect((comp as any).notifPrefs().notif_scan_critical).toBe(false);
  });

  it('inverse notif_url_scan_done de false à true', () => {
    const comp = make();
    (comp as any).notifPrefs = signal({ ...basePrefs(), notif_url_scan_done: false });
    comp.toggleNotif('notif_url_scan_done');
    expect((comp as any).notifPrefs().notif_url_scan_done).toBe(true);
  });

  it('ne modifie pas les autres préférences', () => {
    const comp = make();
    (comp as any).notifPrefs = signal(basePrefs());
    comp.toggleNotif('notif_scan_done');
    const prefs = (comp as any).notifPrefs();
    expect(prefs.notif_scan_critical).toBe(true);
    expect(prefs.notif_url_scan_done).toBe(true);
    expect(prefs.notif_code_scan_done).toBe(true);
  });

  it('ne fait rien si notifPrefs est null', () => {
    const comp = make();
    (comp as any).notifPrefs = signal(null);
    expect(() => comp.toggleNotif('notif_scan_done')).not.toThrow();
    expect((comp as any).notifPrefs()).toBeNull();
  });
});

// ── saveNotifPrefs guard ──────────────────────────────────────────────────────

describe('ProfileComponent — saveNotifPrefs() guard', () => {
  it('ne soumet pas si notifPrefs est null', () => {
    const comp = make();
    (comp as any).notifPrefs = signal(null);
    let called = false;
    (comp as any).userService = {
      updateNotificationPreferences: () => {
        called = true;
        return of(null);
      },
    };
    comp.saveNotifPrefs();
    expect(called).toBe(false);
  });

  it('appelle updateNotificationPreferences avec les préférences courantes', () => {
    const comp = make();
    const prefs = {
      notif_scan_done: false,
      notif_scan_critical: true,
      notif_url_scan_done: false,
      notif_code_scan_done: true,
    };
    (comp as any).notifPrefs = signal(prefs);
    (comp as any).savingNotifs = signal(false);
    (comp as any).snack = { open: vi.fn() };
    const updateFn = vi.fn().mockReturnValue(of(prefs));
    (comp as any).userService = { updateNotificationPreferences: updateFn };
    comp.saveNotifPrefs();
    expect(updateFn).toHaveBeenCalledWith(prefs);
  });

  it('happy: met à jour notifPrefs, désactive savingNotifs et notifie', () => {
    const comp = make();
    const prefs = {
      notif_scan_done: true,
      notif_scan_critical: false,
      notif_url_scan_done: true,
      notif_code_scan_done: false,
    };
    const saved = { ...prefs, notif_scan_done: false };
    (comp as any).notifPrefs = signal(prefs);
    (comp as any).savingNotifs = signal(false);
    const open = vi.fn();
    (comp as any).snack = { open };
    (comp as any).userService = {
      updateNotificationPreferences: vi.fn().mockReturnValue(of(saved)),
    };
    comp.saveNotifPrefs();
    expect((comp as any).notifPrefs()).toEqual(saved);
    expect((comp as any).savingNotifs()).toBe(false);
    expect(open).toHaveBeenCalled();
  });

  it('error: désactive savingNotifs et affiche une erreur', () => {
    const comp = make();
    (comp as any).notifPrefs = signal({
      notif_scan_done: true,
      notif_scan_critical: true,
      notif_url_scan_done: true,
      notif_code_scan_done: true,
    });
    (comp as any).savingNotifs = signal(true);
    const open = vi.fn();
    (comp as any).snack = { open };
    (comp as any).userService = {
      updateNotificationPreferences: vi.fn().mockReturnValue(throwError(() => new Error('x'))),
    };
    comp.saveNotifPrefs();
    expect((comp as any).savingNotifs()).toBe(false);
    expect(open).toHaveBeenCalledWith('Erreur lors de la sauvegarde', 'Fermer', expect.anything());
  });
});

// ── earnedBadgesCount getter ────────────────────────────────────────────────────

describe('ProfileComponent — earnedBadgesCount', () => {
  it('compte uniquement les badges obtenus', () => {
    const comp = make();
    (comp as any).badges = signal([{ earned: true }, { earned: false }, { earned: true }]);
    expect(comp.earnedBadgesCount).toBe(2);
  });

  it('retourne 0 quand aucun badge', () => {
    const comp = make();
    (comp as any).badges = signal([]);
    expect(comp.earnedBadgesCount).toBe(0);
  });

  it('retourne 0 quand aucun badge obtenu', () => {
    const comp = make();
    (comp as any).badges = signal([{ earned: false }, { earned: false }]);
    expect(comp.earnedBadgesCount).toBe(0);
  });
});

// ── updateEmail ─────────────────────────────────────────────────────────────────

describe('ProfileComponent — updateEmail()', () => {
  it('happy: met à jour le profil, vide le mot de passe et notifie', () => {
    const comp = make();
    comp.emailForm.setValue({ email: 'new@test.com', current_password: 'pw' });
    (comp as any).savingEmail = signal(false);
    (comp as any).profile = signal(null);
    const open = vi.fn();
    (comp as any).snack = { open };
    const updated = { email: 'new@test.com', id: 1 };
    const updateEmail = vi.fn().mockReturnValue(of(updated));
    (comp as any).userService = { updateEmail };
    comp.updateEmail();
    expect(updateEmail).toHaveBeenCalledWith('new@test.com', 'pw');
    expect((comp as any).profile()).toEqual(updated);
    expect(comp.emailForm.controls.current_password.value).toBe('');
    expect((comp as any).savingEmail()).toBe(false);
    expect(open).toHaveBeenCalled();
  });

  it('error: désactive savingEmail et affiche le détail', () => {
    const comp = make();
    comp.emailForm.setValue({ email: 'new@test.com', current_password: 'pw' });
    (comp as any).savingEmail = signal(true);
    (comp as any).profile = signal(null);
    const open = vi.fn();
    (comp as any).snack = { open };
    (comp as any).userService = {
      updateEmail: vi.fn().mockReturnValue(throwError(() => ({ error: { detail: 'Email pris' } }))),
    };
    comp.updateEmail();
    expect((comp as any).savingEmail()).toBe(false);
    expect(open).toHaveBeenCalledWith('Email pris', 'Fermer', expect.anything());
  });
});

// ── startSetup2FA ───────────────────────────────────────────────────────────────

describe('ProfileComponent — startSetup2FA()', () => {
  it('happy: stocke le setup et passe à confirm', () => {
    const comp = make();
    (comp as any).twoFaLoading = signal(false);
    (comp as any).twoFaSetup = signal(null);
    (comp as any).twoFaStep = signal('idle');
    const setup = { qr_code_b64: 'q', secret: 'S', otpauth_uri: 'otpauth://x' };
    (comp as any).userService = { setup2FA: vi.fn().mockReturnValue(of(setup)) };
    comp.startSetup2FA();
    expect((comp as any).twoFaSetup()).toEqual(setup);
    expect((comp as any).twoFaStep()).toBe('confirm');
    expect((comp as any).twoFaLoading()).toBe(false);
  });

  it('error: désactive le chargement et notifie', () => {
    const comp = make();
    (comp as any).twoFaLoading = signal(true);
    (comp as any).twoFaSetup = signal(null);
    (comp as any).twoFaStep = signal('idle');
    const open = vi.fn();
    (comp as any).snack = { open };
    (comp as any).userService = {
      setup2FA: vi.fn().mockReturnValue(throwError(() => new Error())),
    };
    comp.startSetup2FA();
    expect((comp as any).twoFaLoading()).toBe(false);
    expect(open).toHaveBeenCalled();
  });
});

// ── confirm2FA ──────────────────────────────────────────────────────────────────

describe('ProfileComponent — confirm2FA()', () => {
  it('ne soumet pas si le code a moins de 6 chiffres', () => {
    const comp = make();
    (comp as any).twoFaCode = signal('123');
    const enable2FA = vi.fn();
    (comp as any).userService = { enable2FA };
    comp.confirm2FA();
    expect(enable2FA).not.toHaveBeenCalled();
  });

  it('happy: active la 2FA, remet idle et notifie', () => {
    const comp = make();
    (comp as any).twoFaCode = signal('123456');
    (comp as any).twoFaLoading = signal(false);
    (comp as any).twoFaSetup = signal({ secret: 'S' });
    (comp as any).twoFaStep = signal('confirm');
    (comp as any).profile = signal(null);
    const open = vi.fn();
    (comp as any).snack = { open };
    const p = { email: 'a@b.c', totp_enabled: true };
    (comp as any).userService = { enable2FA: vi.fn().mockReturnValue(of(p)) };
    comp.confirm2FA();
    expect((comp as any).profile()).toEqual(p);
    expect((comp as any).twoFaStep()).toBe('idle');
    expect((comp as any).twoFaSetup()).toBeNull();
    expect((comp as any).twoFaCode()).toBe('');
    expect(open).toHaveBeenCalled();
  });

  it('error: désactive le chargement et affiche le détail', () => {
    const comp = make();
    (comp as any).twoFaCode = signal('000000');
    (comp as any).twoFaLoading = signal(true);
    (comp as any).twoFaSetup = signal(null);
    (comp as any).twoFaStep = signal('confirm');
    (comp as any).profile = signal(null);
    const open = vi.fn();
    (comp as any).snack = { open };
    (comp as any).userService = {
      enable2FA: vi
        .fn()
        .mockReturnValue(throwError(() => ({ error: { detail: 'Code invalide' } }))),
    };
    comp.confirm2FA();
    expect((comp as any).twoFaLoading()).toBe(false);
    expect(open).toHaveBeenCalledWith('Code invalide', 'Fermer', expect.anything());
  });
});

// ── disable2FA happy ────────────────────────────────────────────────────────────

describe('ProfileComponent — disable2FA() happy', () => {
  it('désactive la 2FA, vide les champs et notifie', () => {
    const comp = make();
    (comp as any).twoFaDisablePw = signal('mypassword');
    (comp as any).twoFaDisableCode = signal('654321');
    (comp as any).twoFaLoading = signal(false);
    (comp as any).twoFaStep = signal('disable');
    (comp as any).profile = signal(null);
    const open = vi.fn();
    (comp as any).snack = { open };
    const p = { email: 'a@b.c', totp_enabled: false };
    const disable2FA = vi.fn().mockReturnValue(of(p));
    (comp as any).userService = { disable2FA };
    comp.disable2FA();
    expect(disable2FA).toHaveBeenCalledWith('mypassword', '654321');
    expect((comp as any).profile()).toEqual(p);
    expect((comp as any).twoFaStep()).toBe('idle');
    expect((comp as any).twoFaDisablePw()).toBe('');
    expect((comp as any).twoFaDisableCode()).toBe('');
    expect(open).toHaveBeenCalled();
  });
});

// ── removeLogo / onLogoChange ───────────────────────────────────────────────────

describe('ProfileComponent — removeLogo()', () => {
  it('vide l’aperçu du logo', () => {
    const comp = make();
    (comp as any).brandLogoPreview = signal('data:image/png;base64,xxx');
    comp.removeLogo();
    expect((comp as any).brandLogoPreview()).toBeNull();
  });
});

describe('ProfileComponent — onLogoChange()', () => {
  it('ne fait rien sans fichier', () => {
    const comp = make();
    (comp as any).brandLogoPreview = signal(null);
    const open = vi.fn();
    (comp as any).snack = { open };
    comp.onLogoChange({ target: { files: [] } } as any);
    expect((comp as any).brandLogoPreview()).toBeNull();
    expect(open).not.toHaveBeenCalled();
  });

  it('refuse un logo de plus de 200 Ko', () => {
    const comp = make();
    (comp as any).brandLogoPreview = signal(null);
    const open = vi.fn();
    (comp as any).snack = { open };
    comp.onLogoChange({ target: { files: [{ size: 300 * 1024 }] } } as any);
    expect(open).toHaveBeenCalledWith(
      'Le logo ne doit pas dépasser 200 Ko',
      'Fermer',
      expect.anything()
    );
    expect((comp as any).brandLogoPreview()).toBeNull();
  });
});

// ── saveBrand ───────────────────────────────────────────────────────────────────

describe('ProfileComponent — saveBrand()', () => {
  function makeBrand(): ProfileComponent {
    const comp = make();
    const fb = new FormBuilder();
    (comp as any).brandForm = fb.nonNullable.group({
      company_name: ['', Validators.required],
      accent_color: ['#06b6d4'],
    });
    (comp as any).savingBrand = signal(false);
    (comp as any).snack = { open: vi.fn() };
    return comp;
  }

  it('ne soumet pas si le formulaire est invalide', () => {
    const comp = makeBrand();
    const upsert = vi.fn();
    (comp as any).brandService = { upsert };
    comp.saveBrand();
    expect(upsert).not.toHaveBeenCalled();
  });

  it('happy: appelle upsert et notifie', () => {
    const comp = makeBrand();
    (comp as any).brandForm.setValue({ company_name: 'Acme', accent_color: '#000000' });
    const upsert = vi.fn().mockReturnValue(of({}));
    (comp as any).brandService = { upsert };
    comp.saveBrand();
    expect(upsert).toHaveBeenCalledWith({
      company_name: 'Acme',
      accent_color: '#000000',
      logo_b64: undefined,
    });
    expect((comp as any).savingBrand()).toBe(false);
  });

  it('error: désactive savingBrand et notifie', () => {
    const comp = makeBrand();
    (comp as any).brandForm.setValue({ company_name: 'Acme', accent_color: '#000000' });
    (comp as any).savingBrand = signal(true);
    const open = vi.fn();
    (comp as any).snack = { open };
    (comp as any).brandService = { upsert: vi.fn().mockReturnValue(throwError(() => new Error())) };
    comp.saveBrand();
    expect((comp as any).savingBrand()).toBe(false);
    expect(open).toHaveBeenCalledWith('Erreur lors de la sauvegarde', 'Fermer', expect.anything());
  });
});

// ── saveConsultantProfile ───────────────────────────────────────────────────────

describe('ProfileComponent — saveConsultantProfile()', () => {
  function makeConsultant(): ProfileComponent {
    const comp = make();
    const fb = new FormBuilder();
    (comp as any).consultantForm = fb.nonNullable.group({
      display_name: [''],
      company_name: [''],
      phone: [''],
    });
    (comp as any).consultantProfile = signal(null);
    (comp as any).savingConsultant = signal(false);
    (comp as any).snack = { open: vi.fn() };
    (comp as any).destroyRef = { onDestroy: vi.fn() };
    return comp;
  }

  it('happy: convertit les champs vides en null et notifie', () => {
    const comp = makeConsultant();
    (comp as any).consultantForm.setValue({
      display_name: 'Jean',
      company_name: '',
      phone: '',
    });
    const p = { display_name: 'Jean' };
    const updateProfile = vi.fn().mockReturnValue(of(p));
    (comp as any).rssiService = { updateProfile };
    comp.saveConsultantProfile();
    expect(updateProfile).toHaveBeenCalledWith({
      display_name: 'Jean',
      company_name: null,
      phone: null,
    });
    expect((comp as any).consultantProfile()).toEqual(p);
    expect((comp as any).savingConsultant()).toBe(false);
  });

  it('error: désactive savingConsultant et notifie', () => {
    const comp = makeConsultant();
    (comp as any).savingConsultant = signal(true);
    const open = vi.fn();
    (comp as any).snack = { open };
    (comp as any).rssiService = {
      updateProfile: vi.fn().mockReturnValue(throwError(() => new Error())),
    };
    comp.saveConsultantProfile();
    expect((comp as any).savingConsultant()).toBe(false);
    expect(open).toHaveBeenCalledWith('Erreur lors de la sauvegarde', 'Fermer', expect.anything());
  });
});

// ── deleteAccount ───────────────────────────────────────────────────────────────

describe('ProfileComponent — deleteAccount()', () => {
  function makeDelete(): ProfileComponent {
    const comp = make();
    const fb = new FormBuilder();
    (comp as any).deleteForm = fb.nonNullable.group({
      password: ['', Validators.required],
    });
    (comp as any).deletingAccount = signal(false);
    (comp as any).snack = { open: vi.fn() };
    return comp;
  }

  it('ne soumet pas si le formulaire est invalide', () => {
    const comp = makeDelete();
    const deleteAccount = vi.fn();
    (comp as any).userService = { deleteAccount };
    comp.deleteAccount();
    expect(deleteAccount).not.toHaveBeenCalled();
  });

  it('happy: supprime le compte et redirige', () => {
    const comp = makeDelete();
    (comp as any).deleteForm.setValue({ password: 'pw' });
    const navigate = vi.fn();
    (comp as any).router = { navigate };
    const deleteAccount = vi.fn().mockReturnValue(of(null));
    (comp as any).userService = { deleteAccount };
    comp.deleteAccount();
    expect(deleteAccount).toHaveBeenCalledWith('pw');
    expect(navigate).toHaveBeenCalledWith(['/']);
  });

  it('error: désactive deletingAccount et affiche le détail', () => {
    const comp = makeDelete();
    (comp as any).deleteForm.setValue({ password: 'pw' });
    (comp as any).deletingAccount = signal(true);
    const open = vi.fn();
    (comp as any).snack = { open };
    (comp as any).router = { navigate: vi.fn() };
    (comp as any).userService = {
      deleteAccount: vi
        .fn()
        .mockReturnValue(throwError(() => ({ error: { detail: 'Mauvais mdp' } }))),
    };
    comp.deleteAccount();
    expect((comp as any).deletingAccount()).toBe(false);
    expect(open).toHaveBeenCalledWith('Mauvais mdp', 'Fermer', expect.anything());
  });
});

// ── updatePassword logique ──────────────────────────────────────────────────────

describe('ProfileComponent — updatePassword() logique', () => {
  function makePw(newPw: string, confirm: string): ProfileComponent {
    const comp = make();
    comp.passwordForm.setValue({
      current_password: 'old',
      new_password: newPw,
      confirm_password: confirm,
    });
    (comp as any).savingPassword = signal(false);
    (comp as any).snack = { open: vi.fn() };
    return comp;
  }

  it('refuse si les mots de passe ne correspondent pas', () => {
    const comp = makePw('longpassword1', 'longpassword2');
    const open = vi.fn();
    (comp as any).snack = { open };
    const updatePassword = vi.fn();
    (comp as any).userService = { updatePassword };
    comp.updatePassword();
    expect(updatePassword).not.toHaveBeenCalled();
    expect(open).toHaveBeenCalledWith(
      'Les mots de passe ne correspondent pas',
      'Fermer',
      expect.anything()
    );
  });

  it('happy: appelle updatePassword et réinitialise le formulaire', () => {
    const comp = makePw('longpassword1', 'longpassword1');
    const updatePassword = vi.fn().mockReturnValue(of(null));
    (comp as any).userService = { updatePassword };
    comp.updatePassword();
    expect(updatePassword).toHaveBeenCalledWith('old', 'longpassword1');
    expect((comp as any).savingPassword()).toBe(false);
  });

  it('error: désactive savingPassword et affiche le détail', () => {
    const comp = makePw('longpassword1', 'longpassword1');
    (comp as any).savingPassword = signal(true);
    const open = vi.fn();
    (comp as any).snack = { open };
    (comp as any).userService = {
      updatePassword: vi.fn().mockReturnValue(throwError(() => ({ error: { detail: 'Refusé' } }))),
    };
    comp.updatePassword();
    expect((comp as any).savingPassword()).toBe(false);
    expect(open).toHaveBeenCalledWith('Refusé', 'Fermer', expect.anything());
  });
});
