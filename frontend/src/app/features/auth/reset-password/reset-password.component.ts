import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AbstractControl, ReactiveFormsModule, FormBuilder, ValidationErrors, Validators } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';

function passwordMatchValidator(control: AbstractControl): ValidationErrors | null {
  const password = control.get('password')?.value;
  const confirm = control.get('confirmPassword')?.value;
  return password && confirm && password !== confirm ? { mismatch: true } : null;
}

@Component({
    selector: 'app-reset-password',
    imports: [
        CommonModule, ReactiveFormsModule, RouterLink,
        MatFormFieldModule, MatInputModule, MatButtonModule,
        MatIconModule, MatProgressSpinnerModule,
    ],
    templateUrl: './reset-password.component.html'
})
export class ResetPasswordComponent implements OnInit {
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);
  private route = inject(ActivatedRoute);

  token: string | null = null;
  showPassword = false;
  loading = false;
  done = false;
  error: string | null = null;

  form = this.fb.nonNullable.group({
    password: ['', [Validators.required, Validators.minLength(8)]],
    confirmPassword: ['', Validators.required],
  }, { validators: passwordMatchValidator });

  ngOnInit() {
    this.token = this.route.snapshot.queryParamMap.get('token');
  }

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
    if (this.form.invalid || !this.token) return;
    this.loading = true;
    this.error = null;
    this.http.post(`${environment.apiUrl}/auth/reset-password`, {
      token: this.token,
      password: this.form.get('password')!.value,
    }).subscribe({
      next: () => { this.done = true; this.loading = false; },
      error: err => {
        this.error = err.error?.detail ?? 'Lien invalide ou expiré.';
        this.loading = false;
      },
    });
  }
}
