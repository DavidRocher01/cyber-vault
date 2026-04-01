import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';

import { CryptoService } from '../../../core/services/crypto.service';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-master-password',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
  ],
  templateUrl: './master-password.component.html',
})
export class MasterPasswordComponent {
  error: string | null = null;
  loading = false;

  form = this.fb.nonNullable.group({
    masterPassword: ['', [Validators.required, Validators.minLength(8)]],
  });

  constructor(
    private fb: FormBuilder,
    private cryptoService: CryptoService,
    private authService: AuthService,
    private router: Router
  ) {}

  async submit() {
    if (this.form.invalid) return;
    this.loading = true;
    this.error = null;
    const email = this.authService.getCurrentEmail();
    if (!email) {
      this.error = 'Session expirée, reconnectez-vous.';
      this.loading = false;
      return;
    }
    try {
      await this.cryptoService.deriveKey(this.form.getRawValue().masterPassword, email);
      this.router.navigate(['/vault']);
    } catch {
      this.error = 'Erreur lors de la dérivation de la clé.';
    } finally {
      this.loading = false;
    }
  }
}
