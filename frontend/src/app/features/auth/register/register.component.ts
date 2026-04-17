import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AbstractControl, ReactiveFormsModule, FormBuilder, ValidationErrors, Validators } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { switchMap } from 'rxjs';

import { AuthService } from '../../../core/services/auth.service';

function passwordMatchValidator(control: AbstractControl): ValidationErrors | null {
  const password = control.get('password')?.value;
  const confirm = control.get('confirmPassword')?.value;
  return password && confirm && password !== confirm ? { mismatch: true } : null;
}

@Component({
    standalone: true,
    selector: 'app-register',
    imports: [
        CommonModule, ReactiveFormsModule, RouterLink,
        MatCardModule, MatFormFieldModule, MatInputModule,
        MatButtonModule, MatIconModule, MatProgressSpinnerModule,
    ],
    templateUrl: './register.component.html'
})
export class RegisterComponent {
  private fb = inject(FormBuilder);
  private authService = inject(AuthService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  get returnUrl(): string | null {
    const url = this.route.snapshot.queryParamMap.get('returnUrl');
    return url?.startsWith('/cyberscan/') ? url : null;
  }

  form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
    confirmPassword: ['', Validators.required],
  }, { validators: passwordMatchValidator });

  error: string | null = null;
  loading = false;
  showPassword = false;

  benefits = [
    { icon: 'security', text: 'Scan SSL, headers HTTP, CVE — non intrusif' },
    { icon: 'picture_as_pdf', text: 'Rapport PDF complet après chaque scan' },
    { icon: 'notifications_active', text: 'Alerte email si vulnérabilité critique détectée' },
    { icon: 'lock', text: 'Vos données ne quittent jamais nos serveurs' },
  ];

  get passwordStrength(): number {
    const pw = this.form.get('password')?.value ?? '';
    let score = 0;
    if (pw.length >= 8) score++;
    if (/[A-Z]/.test(pw)) score++;
    if (/[0-9]/.test(pw)) score++;
    if (/[^A-Za-z0-9]/.test(pw)) score++;
    return score;
  }

  get strengthLabel(): string {
    const s = this.passwordStrength;
    if (s <= 1) return 'Faible';
    if (s === 2) return 'Moyen';
    if (s === 3) return 'Fort';
    return 'Très fort';
  }

  submit() {
    if (this.form.invalid) return;
    this.loading = true;
    const { email, password } = this.form.getRawValue();
    this.authService.register(email, password).pipe(
      switchMap(() => this.authService.login(email, password))
    ).subscribe({
      next: () => this.router.navigateByUrl(this.returnUrl || '/cyberscan/onboarding'),
      error: err => { this.error = err.error?.detail ?? 'Erreur inscription'; this.loading = false; },
    });
  }
}
