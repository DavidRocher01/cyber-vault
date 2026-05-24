import { Component, inject, signal } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, Validators, AbstractControl, ValidationErrors } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { switchMap } from 'rxjs';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { AuthService } from '../../../../../core/services/auth.service';
import { OtpInputComponent } from '../../../../../shared/otp-input/otp-input.component';

@Component({
  standalone: true,
  selector: 'app-auth-modal',
  imports: [ReactiveFormsModule, RouterLink, MatIconModule, MatProgressSpinnerModule, OtpInputComponent],
  templateUrl: './auth-modal.component.html',
})
export class AuthModalComponent {
  private auth = inject(AuthService);
  private router = inject(Router);
  private fb = inject(FormBuilder);

  authPanel   = signal<'closed' | 'login' | 'register'>('closed');
  auth2faStep = signal(false);

  pendingEmail    = '';
  pendingPassword = '';
  authOtpCode     = '';
  authOtpClear    = 0;
  authLoading     = false;
  authError: string | null = null;
  showAuthPassword = false;

  loginForm = this.fb.nonNullable.group({
    email:    ['', [Validators.required, Validators.email]],
    password: ['', Validators.required],
  });

  registerForm = this.fb.nonNullable.group({
    email:           ['', [Validators.required, Validators.email]],
    password:        ['', [Validators.required, Validators.minLength(8)]],
    confirmPassword: ['', Validators.required],
  }, { validators: (g: AbstractControl): ValidationErrors | null => {
    const pw = g.get('password')?.value;
    const cp = g.get('confirmPassword')?.value;
    return pw && cp && pw !== cp ? { mismatch: true } : null;
  }});

  open(mode: 'login' | 'register') {
    this.authError = null;
    this.authLoading = false;
    this.auth2faStep.set(false);
    this.loginForm.reset();
    this.registerForm.reset();
    this.authPanel.set(mode);
  }

  openTab(mode: 'login' | 'register') {
    this.authError = null;
    this.authPanel.set(mode);
  }

  close() {
    this.authPanel.set('closed');
    this.auth2faStep.set(false);
    this.pendingEmail = '';
    this.pendingPassword = '';
  }

  submitLogin() {
    if (this.loginForm.invalid || this.authLoading) return;
    this.authLoading = true;
    this.authError = null;
    const { email, password } = this.loginForm.getRawValue();
    this.auth.login(email, password).subscribe({
      next: res => {
        if ('requires_2fa' in res) {
          this.pendingEmail = email;
          this.pendingPassword = password;
          this.auth2faStep.set(true);
          this.authOtpClear++;
          this.authLoading = false;
        } else {
          this.close();
          this.router.navigate(['/cyberscan']);
        }
      },
      error: err => {
        this.authError = err.error?.detail ?? 'Identifiants incorrects.';
        this.authLoading = false;
      },
    });
  }

  submitLoginTotp() {
    if (this.authOtpCode.length !== 6) return;
    this.authLoading = true;
    this.authError = null;
    this.auth.login(this.pendingEmail, this.pendingPassword, this.authOtpCode).subscribe({
      next: () => { this.close(); this.router.navigate(['/cyberscan']); },
      error: err => {
        this.authError = err.error?.detail ?? 'Code invalide.';
        this.authLoading = false;
        this.authOtpClear++;
      },
    });
  }

  cancelAuth2fa() {
    this.auth2faStep.set(false);
    this.authError = null;
    this.authOtpCode = '';
  }

  submitRegister() {
    if (this.registerForm.invalid || this.authLoading) return;
    this.authLoading = true;
    this.authError = null;
    const { email, password } = this.registerForm.getRawValue();
    this.auth.register(email, password).pipe(
      switchMap(() => this.auth.login(email, password))
    ).subscribe({
      next: () => { this.close(); this.router.navigate(['/cyberscan/onboarding']); },
      error: err => {
        this.authError = err.error?.detail ?? 'Erreur lors de la création du compte.';
        this.authLoading = false;
      },
    });
  }

  get registerPasswordStrength(): number {
    const pw = this.registerForm.get('password')?.value ?? '';
    let score = 0;
    if (pw.length >= 8) score++;
    if (/[A-Z]/.test(pw)) score++;
    if (/[0-9]/.test(pw)) score++;
    if (/[^A-Za-z0-9]/.test(pw)) score++;
    return score;
  }

  get registerStrengthLabel(): string {
    const s = this.registerPasswordStrength;
    if (s <= 1) return 'Faible';
    if (s === 2) return 'Moyen';
    if (s === 3) return 'Fort';
    return 'Très fort';
  }
}
