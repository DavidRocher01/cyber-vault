import { Component, inject, OnInit, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { AwarenessService, CertificateVerification } from '../cyberscan/services/awareness.service';

@Component({
  standalone: true,
  selector: 'app-verify-certificate',
  imports: [DatePipe, MatButtonModule, MatIconModule, MatProgressSpinnerModule],
  template: `
    <div class="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div class="w-full max-w-lg">
        <!-- Logo -->
        <div class="text-center mb-6">
          <div class="flex items-center justify-center gap-2 mb-1">
            <mat-icon class="text-cyan-400 !text-[1.4rem] !w-[1.4rem] !h-[1.4rem]">shield</mat-icon>
            <span class="font-bold text-white">Cyber<span class="text-cyan-400">Scan</span></span>
          </div>
          <p class="text-gray-500 text-xs">Vérification d'attestation NIS2</p>
        </div>

        @if (loading()) {
          <div class="rounded-xl border border-gray-800 bg-gray-900 p-10 text-center">
            <mat-spinner diameter="40" class="mx-auto mb-4" />
            <p class="text-gray-400">Vérification en cours...</p>
          </div>
        }

        @if (!loading() && cert()) {
          <div class="rounded-2xl border border-green-700/40 bg-gray-900 p-8 text-center">
            <div
              class="w-14 h-14 rounded-2xl bg-green-500/10 border border-green-500/20 flex items-center justify-center mx-auto mb-4"
            >
              <mat-icon class="text-green-400 !text-[2rem] !w-[2rem] !h-[2rem]">verified</mat-icon>
            </div>
            <h1
              class="text-2xl font-bold bg-gradient-to-r from-green-400 to-cyan-400 bg-clip-text text-transparent mb-1"
            >
              Attestation valide
            </h1>
            <p class="text-gray-400 text-sm mb-6">
              Cette attestation est authentique et non falsifiée.
            </p>

            <div
              class="rounded-xl border border-gray-800 bg-gray-950 p-5 text-left flex flex-col gap-3"
            >
              <div class="flex justify-between items-center">
                <span class="text-gray-500 text-sm">Titulaire</span>
                <span class="text-white text-sm font-semibold">{{
                  cert()!.learner_name || '—'
                }}</span>
              </div>
              <div class="flex justify-between items-center border-t border-gray-800 pt-3">
                <span class="text-gray-500 text-sm">Programme</span>
                <span class="text-white text-sm">{{ cert()!.program_title }}</span>
              </div>
              <div class="flex justify-between items-center border-t border-gray-800 pt-3">
                <span class="text-gray-500 text-sm">Référence</span>
                <span class="text-cyan-400 text-sm font-mono">{{ cert()!.public_id }}</span>
              </div>
              <div class="flex justify-between items-center border-t border-gray-800 pt-3">
                <span class="text-gray-500 text-sm">Émise le</span>
                <span class="text-white text-sm">{{ cert()!.issued_at | date: 'dd/MM/yyyy' }}</span>
              </div>
              @if (cert()!.expires_at) {
                <div class="flex justify-between items-center border-t border-gray-800 pt-3">
                  <span class="text-gray-500 text-sm">Valable jusqu'au</span>
                  <span class="text-white text-sm">{{
                    cert()!.expires_at | date: 'dd/MM/yyyy'
                  }}</span>
                </div>
              }
              <div class="flex justify-between items-center border-t border-gray-800 pt-3">
                <span class="text-gray-500 text-sm">Vérifications</span>
                <span class="text-gray-400 text-sm">{{ cert()!.verification_count }}</span>
              </div>
            </div>

            <div class="mt-5 flex items-center justify-center gap-2 text-green-400 text-xs">
              <mat-icon class="!text-[1rem] !w-[1rem] !h-[1rem]">lock</mat-icon>
              Signature SHA-256 vérifiée — Rocher Cybersécurité
            </div>
          </div>
        }

        @if (!loading() && !cert()) {
          <div class="rounded-2xl border border-red-700/40 bg-gray-900 p-8 text-center">
            <div
              class="w-14 h-14 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-4"
            >
              <mat-icon class="text-red-400 !text-[2rem] !w-[2rem] !h-[2rem]">gpp_bad</mat-icon>
            </div>
            <h1 class="text-2xl font-bold text-white mb-2">Attestation invalide</h1>
            <p class="text-gray-400 text-sm">
              Cette attestation est introuvable, révoquée ou expirée.<br />
              Elle ne peut pas être considérée comme valide.
            </p>
          </div>
        }
      </div>
    </div>
  `,
})
export class VerifyCertificateComponent implements OnInit {
  private svc = inject(AwarenessService);
  private route = inject(ActivatedRoute);

  cert = signal<CertificateVerification | null>(null);
  loading = signal(true);

  ngOnInit() {
    const publicId = this.route.snapshot.paramMap.get('publicId') ?? '';
    const token = this.route.snapshot.queryParamMap.get('token') ?? '';

    if (!publicId || !token) {
      this.loading.set(false);
      return;
    }

    this.svc.verifyCertificate(publicId, token).subscribe({
      next: c => {
        this.cert.set(c);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }
}
