import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDividerModule } from '@angular/material/divider';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { Title } from '@angular/platform-browser';

import { UserService, UserProfile, TwoFactorSetup, NotificationPreferences } from '../services/user.service';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import { OtpInputComponent } from '../../../shared/otp-input/otp-input.component';

@Component({
    selector: 'app-profile',
    imports: [
        CommonModule, ReactiveFormsModule, RouterLink,
        MatButtonModule, MatCardModule, MatIconModule,
        MatFormFieldModule, MatInputModule, MatSnackBarModule, MatDividerModule, MatProgressSpinnerModule, MatTooltipModule, MatSlideToggleModule, NavButtonsComponent, OtpInputComponent,
    ],
    templateUrl: './profile.component.html',
    styles: [`.twofa-glow { background: radial-gradient(ellipse at 80% 0%, rgba(34,197,94,.4), transparent 60%); }`]
})
export class ProfileComponent implements OnInit {
  private userService = inject(UserService);
  private fb = inject(FormBuilder);
  private snack = inject(MatSnackBar);
  private title = inject(Title);
  private router = inject(Router);

  profile = signal<UserProfile | null>(null);
  loading = signal(true);
  savingEmail = signal(false);
  savingPassword = signal(false);

  showCurrentPw = signal(false);
  showNewPw = signal(false);
  showConfirmPw = signal(false);
  showEmailPw = signal(false);

  // Notification preferences
  notifPrefs = signal<NotificationPreferences | null>(null);
  savingNotifs = signal(false);

  // 2FA state
  twoFaSetup = signal<TwoFactorSetup | null>(null);
  twoFaStep = signal<'idle' | 'setup' | 'confirm' | 'disable'>('idle');
  twoFaLoading = signal(false);
  twoFaCode = signal('');
  twoFaDisablePw = signal('');
  twoFaDisableCode = signal('');
  otpClear = 0;
  otpDisableClear = 0;

  get initials(): string {
    const email = this.profile()?.email ?? '';
    return email.slice(0, 2).toUpperCase();
  }

  get passwordStrength(): { label: string; width: string; color: string } {
    const pw = this.passwordForm.controls.new_password.value ?? '';
    if (pw.length === 0) return { label: '', width: '0%', color: '' };
    let score = 0;
    if (pw.length >= 8) score++;
    if (pw.length >= 12) score++;
    if (/[A-Z]/.test(pw)) score++;
    if (/[0-9]/.test(pw)) score++;
    if (/[^A-Za-z0-9]/.test(pw)) score++;
    if (score <= 1) return { label: 'Faible', width: '20%', color: 'bg-red-500' };
    if (score <= 2) return { label: 'Moyen', width: '50%', color: 'bg-yellow-500' };
    if (score <= 3) return { label: 'Bon', width: '75%', color: 'bg-blue-500' };
    return { label: 'Fort', width: '100%', color: 'bg-green-500' };
  }

  emailForm = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    current_password: ['', Validators.required],
  });

  passwordForm = this.fb.nonNullable.group({
    current_password: ['', Validators.required],
    new_password: ['', [Validators.required, Validators.minLength(8)]],
    confirm_password: ['', Validators.required],
  });

  ngOnInit() {
    this.title.setTitle('Mon profil — CyberScan');
    this.userService.getProfile().subscribe({
      next: p => {
        this.profile.set(p);
        this.emailForm.patchValue({ email: p.email });
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
    this.userService.getNotificationPreferences().subscribe({
      next: prefs => this.notifPrefs.set(prefs),
    });
  }

  toggleNotif(key: keyof NotificationPreferences) {
    const current = this.notifPrefs();
    if (!current) return;
    this.notifPrefs.set({ ...current, [key]: !current[key] });
  }

  saveNotifPrefs() {
    const prefs = this.notifPrefs();
    if (!prefs) return;
    this.savingNotifs.set(true);
    this.userService.updateNotificationPreferences(prefs).subscribe({
      next: saved => {
        this.notifPrefs.set(saved);
        this.savingNotifs.set(false);
        this.snack.open('Préférences enregistrées', 'OK', { duration: 3000 });
      },
      error: () => {
        this.savingNotifs.set(false);
        this.snack.open('Erreur lors de la sauvegarde', 'Fermer', { duration: 4000 });
      },
    });
  }

  updateEmail() {
    if (this.emailForm.invalid) return;
    this.savingEmail.set(true);
    const { email, current_password } = this.emailForm.getRawValue();
    this.userService.updateEmail(email, current_password).subscribe({
      next: p => {
        this.profile.set(p);
        this.emailForm.patchValue({ current_password: '' });
        this.savingEmail.set(false);
        this.snack.open('Email mis à jour', 'OK', { duration: 3000 });
      },
      error: err => {
        this.savingEmail.set(false);
        this.snack.open(err.error?.detail || 'Erreur', 'Fermer', { duration: 4000 });
      },
    });
  }

  startSetup2FA() {
    this.twoFaLoading.set(true);
    this.userService.setup2FA().subscribe({
      next: setup => {
        this.twoFaSetup.set(setup);
        this.twoFaStep.set('confirm');
        this.twoFaLoading.set(false);
      },
      error: () => {
        this.twoFaLoading.set(false);
        this.snack.open('Erreur lors de la configuration', 'Fermer', { duration: 4000 });
      },
    });
  }

  confirm2FA() {
    if (this.twoFaCode().length !== 6) return;
    this.twoFaLoading.set(true);
    this.userService.enable2FA(this.twoFaCode()).subscribe({
      next: p => {
        this.profile.set(p);
        this.twoFaStep.set('idle');
        this.twoFaSetup.set(null);
        this.twoFaCode.set('');
        this.twoFaLoading.set(false);
        this.snack.open('Double authentification activée ✅', 'OK', { duration: 4000 });
      },
      error: err => {
        this.twoFaLoading.set(false);
        this.snack.open(err.error?.detail || 'Code invalide', 'Fermer', { duration: 4000 });
      },
    });
  }

  disable2FA() {
    if (!this.twoFaDisablePw() || this.twoFaDisableCode().length !== 6) return;
    this.twoFaLoading.set(true);
    this.userService.disable2FA(this.twoFaDisablePw(), this.twoFaDisableCode()).subscribe({
      next: p => {
        this.profile.set(p);
        this.twoFaStep.set('idle');
        this.twoFaDisablePw.set('');
        this.twoFaDisableCode.set('');
        this.twoFaLoading.set(false);
        this.snack.open('Double authentification désactivée', 'OK', { duration: 4000 });
      },
      error: err => {
        this.twoFaLoading.set(false);
        this.snack.open(err.error?.detail || 'Erreur', 'Fermer', { duration: 4000 });
      },
    });
  }

  // ── RGPD ──────────────────────────────────────────────────────────────────
  showDeleteConfirm = signal(false);
  deletingAccount = signal(false);

  deleteForm = this.fb.nonNullable.group({
    password: ['', Validators.required],
  });

  exportingData = signal(false);

  exportUrl(): string {
    return this.userService.exportMyData();
  }

  exportData() {
    this.exportingData.set(true);
    this.userService.exportMyDataBlob().subscribe({
      next: blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `cyberscan_mes_donnees_${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
        this.exportingData.set(false);
        this.snack.open('Export téléchargé', 'OK', { duration: 3000 });
      },
      error: () => {
        this.exportingData.set(false);
        this.snack.open('Erreur lors de l\'export', 'Fermer', { duration: 4000 });
      },
    });
  }

  deleteAccount() {
    if (this.deleteForm.invalid) return;
    this.deletingAccount.set(true);
    this.userService.deleteAccount(this.deleteForm.getRawValue().password).subscribe({
      next: () => {
        this.snack.open('Compte supprimé. Au revoir !', 'OK', { duration: 5000 });
        this.router.navigate(['/cyberscan']);
      },
      error: err => {
        this.deletingAccount.set(false);
        this.snack.open(err.error?.detail || 'Mot de passe incorrect', 'Fermer', { duration: 4000 });
      },
    });
  }

  cancelTwoFa() {
    this.twoFaStep.set('idle');
    this.twoFaSetup.set(null);
    this.twoFaCode.set('');
    this.twoFaDisablePw.set('');
    this.twoFaDisableCode.set('');
    this.otpClear++;
    this.otpDisableClear++;
  }

  updatePassword() {
    const { new_password, confirm_password, current_password } = this.passwordForm.getRawValue();
    if (this.passwordForm.invalid) return;
    if (new_password !== confirm_password) {
      this.snack.open('Les mots de passe ne correspondent pas', 'Fermer', { duration: 4000 });
      return;
    }
    this.savingPassword.set(true);
    this.userService.updatePassword(current_password, new_password).subscribe({
      next: () => {
        this.passwordForm.reset();
        this.savingPassword.set(false);
        this.snack.open('Mot de passe mis à jour', 'OK', { duration: 3000 });
      },
      error: err => {
        this.savingPassword.set(false);
        this.snack.open(err.error?.detail || 'Erreur', 'Fermer', { duration: 4000 });
      },
    });
  }
}
