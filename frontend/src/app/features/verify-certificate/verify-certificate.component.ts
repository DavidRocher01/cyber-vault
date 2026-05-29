import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { AwarenessService, CertificateVerification } from '../cyberscan/services/awareness.service';

@Component({
  standalone: true,
  selector: 'app-verify-certificate',
  imports: [CommonModule, DatePipe, MatButtonModule, MatIconModule, MatProgressSpinnerModule],
  template: `
    <div class="min-h-screen bg-[#0f172a] flex items-center justify-center p-4">
      <div class="w-full max-w-lg">
        @if (loading()) {
          <div class="text-center">
            <mat-spinner diameter="48" class="mx-auto mb-4" />
            <p class="text-slate-400">Vérification en cours...</p>
          </div>
        }

        @if (!loading() && cert()) {
          <div class="bg-[#1e293b] rounded-2xl p-8 border border-green-500/30 text-center">
            <mat-icon class="text-green-400 text-6xl mb-4">verified</mat-icon>
            <h1 class="text-2xl font-bold text-white mb-2">Attestation valide</h1>
            <p class="text-slate-400 text-sm mb-6">
              Cette attestation est authentique et non falsifiée.
            </p>

            <div class="bg-[#0f172a] rounded-xl p-5 text-left space-y-3">
              <div class="flex justify-between">
                <span class="text-slate-500 text-sm">Titulaire</span>
                <span class="text-white text-sm font-semibold">{{
                  cert()!.learner_name || '—'
                }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-500 text-sm">Programme</span>
                <span class="text-white text-sm">{{ cert()!.program_title }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-500 text-sm">Référence</span>
                <span class="text-cyan-400 text-sm font-mono">{{ cert()!.public_id }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-500 text-sm">Émise le</span>
                <span class="text-white text-sm">{{ cert()!.issued_at | date: 'dd/MM/yyyy' }}</span>
              </div>
              @if (cert()!.expires_at) {
                <div class="flex justify-between">
                  <span class="text-slate-500 text-sm">Valable jusqu'au</span>
                  <span class="text-white text-sm">{{
                    cert()!.expires_at | date: 'dd/MM/yyyy'
                  }}</span>
                </div>
              }
              <div class="flex justify-between">
                <span class="text-slate-500 text-sm">Vérifications</span>
                <span class="text-slate-400 text-sm">{{ cert()!.verification_count }}</span>
              </div>
            </div>

            <div class="mt-6 flex items-center justify-center gap-2 text-green-400 text-sm">
              <mat-icon class="text-sm">lock</mat-icon>
              Signature SHA-256 vérifiée — CyberScan
            </div>
          </div>
        }

        @if (!loading() && !cert()) {
          <div class="bg-[#1e293b] rounded-2xl p-8 border border-red-500/30 text-center">
            <mat-icon class="text-red-400 text-6xl mb-4">gpp_bad</mat-icon>
            <h1 class="text-2xl font-bold text-white mb-2">Attestation invalide</h1>
            <p class="text-slate-400">
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
