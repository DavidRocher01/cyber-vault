import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { CryptoService } from '../../../core/services/crypto.service';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-master-password',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule, RouterLink,
    MatIconModule, MatProgressSpinnerModule,
  ],
  templateUrl: './master-password.component.html',
  styles: [`
    .mp-bg {
      background: #080d1a;
    }
    .mp-left {
      background: linear-gradient(160deg, #080d1a 0%, #0a1628 100%);
    }
    .mp-dot-grid {
      background-image: radial-gradient(rgba(6,182,212,0.12) 1px, transparent 1px);
      background-size: 28px 28px;
    }
    .mp-glow {
      background: radial-gradient(circle, rgba(6,182,212,0.07) 0%, transparent 70%);
    }
    .mp-separator {
      background: linear-gradient(to bottom, transparent, rgba(6,182,212,0.15) 30%, rgba(6,182,212,0.15) 70%, transparent);
    }
    .mp-right {
      background: #080d1a;
    }
    .mp-input {
      background: rgba(255,255,255,0.03);
    }
    .mp-btn {
      background: linear-gradient(135deg, #06b6d4, #0284c7);
      color: white;
    }
    .mp-btn:hover:not(:disabled) {
      background: linear-gradient(135deg, #22d3ee, #0ea5e9);
      box-shadow: 0 0 24px rgba(6,182,212,0.35);
    }
  `],
})
export class MasterPasswordComponent {
  private fb = inject(FormBuilder);
  private cryptoService = inject(CryptoService);
  private authService = inject(AuthService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  error: string | null = null;
  loading = false;
  showPassword = false;

  form = this.fb.nonNullable.group({
    masterPassword: ['', [Validators.required, Validators.minLength(8)]],
  });

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
      const returnUrl = this.route.snapshot.queryParamMap.get('returnUrl') || '/vault';
      this.router.navigateByUrl(returnUrl);
    } catch {
      this.error = 'Erreur lors de la dérivation de la clé.';
    } finally {
      this.loading = false;
    }
  }
}
