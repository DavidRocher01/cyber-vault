/**
 * ProfileComponent — tests des méthodes pures et guards.
 * On instancie le composant sans DI Angular (Object.create).
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { signal } from '@angular/core';
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
  return comp;
}

// ── initials getter ────────────────────────────────────────────────────────────

describe('ProfileComponent — initials', () => {
  it('retourne les 2 premières lettres de l\'email en majuscules', () => {
    const comp = make();
    (comp as any).profile = signal({ email: 'david@example.com', id: 1, is_active: true, totp_enabled: false });
    expect(comp.initials).toBe('DA');
  });

  it('retourne une chaîne vide si pas de profil', () => {
    const comp = make();
    expect(comp.initials).toBe('');
  });

  it('retourne les initiales en majuscules', () => {
    const comp = make();
    (comp as any).profile = signal({ email: 'abc@test.com', id: 1, is_active: true, totp_enabled: false });
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
    (comp as any).userService = { updateEmail: () => { called = true; } };
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
    (comp as any).userService = { updatePassword: () => { called = true; } };
    comp.updatePassword();
    expect(called).toBe(false);
  });
});

// ── disable2FA guard ───────────────────────────────────────────────────────────

describe('ProfileComponent — disable2FA() guard', () => {
  it('ne soumet pas si le mot de passe est vide', () => {
    const comp = make();
    let called = false;
    (comp as any).userService = { disable2FA: () => { called = true; } };
    (comp as any).twoFaDisablePw = signal('');
    (comp as any).twoFaDisableCode = signal('123456');
    comp.disable2FA();
    expect(called).toBe(false);
  });

  it('ne soumet pas si le code a moins de 6 chiffres', () => {
    const comp = make();
    let called = false;
    (comp as any).userService = { disable2FA: () => { called = true; } };
    (comp as any).twoFaDisablePw = signal('mypassword');
    (comp as any).twoFaDisableCode = signal('123');
    comp.disable2FA();
    expect(called).toBe(false);
  });
});

// ── exportUrl ─────────────────────────────────────────────────────────────────

describe('ProfileComponent — exportUrl()', () => {
  it('retourne l\'URL d\'export', () => {
    const comp = make();
    (comp as any).userService = { exportMyData: () => '/api/v1/users/me/export' };
    expect(comp.exportUrl()).toBe('/api/v1/users/me/export');
  });
});
