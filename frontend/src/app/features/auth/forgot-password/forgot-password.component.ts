import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';

@Component({
    selector: 'app-forgot-password',
    imports: [
        CommonModule, ReactiveFormsModule, RouterLink,
        MatFormFieldModule, MatInputModule, MatButtonModule,
        MatIconModule, MatProgressSpinnerModule,
    ],
    templateUrl: './forgot-password.component.html'
})
export class ForgotPasswordComponent {
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);

  form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
  });

  loading = false;
  sent = false;
  error: string | null = null;

  submit() {
    if (this.form.invalid) return;
    this.loading = true;
    this.error = null;
    this.http.post(`${environment.apiUrl}/auth/forgot-password`, this.form.getRawValue()).subscribe({
      next: () => { this.sent = true; this.loading = false; },
      error: () => { this.error = 'Une erreur est survenue. Réessayez.'; this.loading = false; },
    });
  }
}
