import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { AwarenessService } from '../cyberscan/services/awareness.service';

@Component({
  standalone: true,
  selector: 'app-awareness-login',
  imports: [
    CommonModule, FormsModule,
    MatButtonModule, MatFormFieldModule, MatInputModule,
    MatIconModule, MatProgressSpinnerModule,
  ],
  template: `
    <div class="min-h-screen bg-[#0f172a] flex items-center justify-center p-4">
      <div class="w-full max-w-md">

        <!-- Logo / Title -->
        <div class="text-center mb-8">
          <mat-icon class="text-cyan-400 text-5xl mb-3">school</mat-icon>
          <h1 class="text-2xl font-bold text-white">Sensibilisation NIS2</h1>
          <p class="text-slate-400 text-sm mt-1">Votre portail de formation cybersécurité</p>
        </div>

        <!-- Token auto-verify from URL -->
        @if (verifying()) {
          <div class="bg-[#1e293b] rounded-xl p-8 text-center border border-slate-700">
            <mat-spinner diameter="40" class="mx-auto mb-4" />
            <p class="text-slate-300">Vérification de votre lien...</p>
          </div>
        } @else if (error()) {
          <div class="bg-red-500/10 border border-red-500/30 rounded-xl p-6 text-center mb-4">
            <mat-icon class="text-red-400 text-3xl mb-2">error_outline</mat-icon>
            <p class="text-red-400 font-semibold">Lien invalide ou expiré</p>
            <p class="text-slate-400 text-sm mt-1">Demandez un nouveau lien à votre administrateur.</p>
          </div>
        } @else {
          <!-- Manual token input (fallback) -->
          <div class="bg-[#1e293b] rounded-xl p-6 border border-slate-700">
            <h2 class="text-white font-semibold mb-4">Accéder à ma formation</h2>
            <p class="text-slate-400 text-sm mb-4">
              Vous avez reçu un lien de connexion par email. Copiez le code de vérification ici.
            </p>
            <mat-form-field appearance="outline" class="w-full">
              <mat-label>Code de vérification</mat-label>
              <input matInput [(ngModel)]="token" placeholder="Collez votre code ici" />
            </mat-form-field>
            <button mat-raised-button color="primary" class="w-full mt-2"
                    (click)="verifyToken()" [disabled]="!token.trim() || loading()">
              @if (loading()) { <mat-spinner diameter="18" /> } @else { Accéder à ma formation }
            </button>
          </div>
        }
      </div>
    </div>
  `,
})
export class AwarenessLoginComponent implements OnInit {
  private svc = inject(AwarenessService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  token = '';
  verifying = signal(false);
  loading = signal(false);
  error = signal(false);

  ngOnInit() {
    // If already logged in, redirect
    if (this.svc.learnerSession()) {
      this.router.navigate(['/awareness']);
      return;
    }

    // Auto-verify token from URL query params
    const tokenParam = this.route.snapshot.queryParamMap.get('token');
    if (tokenParam) {
      this.verifying.set(true);
      this.svc.verifyMagicLink(tokenParam).subscribe({
        next: () => this.router.navigate(['/awareness']),
        error: () => { this.verifying.set(false); this.error.set(true); },
      });
    }
  }

  verifyToken() {
    const t = this.token.trim();
    if (!t) return;
    this.loading.set(true);
    this.svc.verifyMagicLink(t).subscribe({
      next: () => this.router.navigate(['/awareness']),
      error: () => { this.loading.set(false); this.error.set(true); },
    });
  }
}
