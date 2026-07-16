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
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <div class="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div class="w-full max-w-md">
        <!-- Logo / Title -->
        <div class="text-center mb-8">
          <div
            class="w-16 h-16 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center mx-auto mb-4"
          >
            <mat-icon class="text-cyan-400 !text-[2rem] !w-[2rem] !h-[2rem]">school</mat-icon>
          </div>
          <h1
            class="text-2xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent"
          >
            Sensibilisation NIS2
          </h1>
          <p class="text-gray-400 text-sm mt-1">Votre portail de formation cybersécurité</p>
        </div>

        <!-- Token auto-verify from URL -->
        @if (verifying()) {
          <div class="rounded-xl p-8 text-center border border-gray-800 bg-gray-900">
            <mat-spinner diameter="40" class="mx-auto mb-4" />
            <p class="text-gray-300">Vérification de votre lien...</p>
          </div>
        } @else if (error()) {
          <div class="bg-red-500/10 border border-red-500/30 rounded-xl p-6 text-center mb-4">
            <mat-icon class="text-red-400 !text-[2rem] !w-[2rem] !h-[2rem] mb-2"
              >error_outline</mat-icon
            >
            <p class="text-red-400 font-semibold">Lien invalide ou expiré</p>
            <p class="text-gray-400 text-sm mt-1">
              Demandez un nouveau lien à votre administrateur.
            </p>
          </div>
        } @else {
          <!-- Manual token input (fallback) -->
          <div class="rounded-xl p-6 border border-gray-800 bg-gray-900">
            <h2 class="text-white font-semibold mb-1">Accéder à ma formation</h2>
            <p class="text-gray-400 text-sm mb-5">
              Vous avez reçu un lien de connexion par email. Copiez le code de vérification ici.
            </p>
            <mat-form-field appearance="outline" class="w-full">
              <mat-label>Code de vérification</mat-label>
              <input
                matInput
                [(ngModel)]="token"
                (ngModelChange)="tokenError.set(false)"
                placeholder="Collez votre code ici"
                [class.border-red-500]="tokenError()"
              />
            </mat-form-field>
            @if (tokenError()) {
              <p class="mt-1 text-xs text-red-400">Le code d'accès est requis.</p>
            }
            <button
              mat-flat-button
              class="w-full !rounded-xl !bg-cyan-600 hover:!bg-cyan-500 !text-white mt-2"
              (click)="verifyToken()"
              [disabled]="loading()"
            >
              @if (loading()) {
                <mat-spinner diameter="18" />
              } @else {
                Accéder à ma formation
              }
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
  tokenError = signal(false);

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
        error: () => {
          this.verifying.set(false);
          this.error.set(true);
        },
      });
    }
  }

  verifyToken() {
    const t = this.token.trim();
    if (!t) {
      this.tokenError.set(true);
      return;
    }
    this.tokenError.set(false);
    this.loading.set(true);
    this.svc.verifyMagicLink(t).subscribe({
      next: () => this.router.navigate(['/awareness']),
      error: () => {
        this.loading.set(false);
        this.error.set(true);
      },
    });
  }
}
