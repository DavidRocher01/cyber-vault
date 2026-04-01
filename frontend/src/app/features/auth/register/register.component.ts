import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, MatCardModule, MatFormFieldModule, MatInputModule, MatButtonModule, RouterLink],
  templateUrl: './register.component.html',
})
export class RegisterComponent {
  form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
  });
  error: string | null = null;
  loading = false;

  constructor(private fb: FormBuilder, private authService: AuthService, private router: Router) {}

  submit() {
    if (this.form.invalid) return;
    this.loading = true;
    const { email, password } = this.form.getRawValue();
    this.authService.register(email, password).subscribe({
      next: () => this.router.navigate(['/auth/login']),
      error: err => { this.error = err.error?.detail ?? 'Erreur inscription'; this.loading = false; },
    });
  }
}
