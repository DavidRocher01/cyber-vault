import { Component, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { CyberscanService } from '../../../services/cyberscan.service';
import { extractApiError } from '../../../../../core/http-error';

@Component({
  standalone: true,
  selector: 'app-demo-scan',
  imports: [MatIconModule, MatProgressSpinnerModule],
  template: `
    <section class="px-6 py-14 -mt-6 relative z-20">
      <div class="max-w-2xl mx-auto">
        <div
          class="rounded-2xl border border-cyan-500/25 bg-gray-800/80 backdrop-blur-sm p-8 shadow-2xl shadow-cyan-900/20"
        >
          <div class="text-center mb-6">
            <span
              class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-400 text-xs font-semibold border border-cyan-700/40 mb-3"
            >
              <span class="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse"></span>
              Scan gratuit — sans compte
            </span>
            <h2 class="text-2xl font-bold text-white">Testez votre site maintenant</h2>
            <p class="text-gray-400 text-sm mt-1">SSL · Headers · DNS · CORS · CMS · WAF · Email</p>
          </div>

          <div class="flex gap-2">
            <input
              type="url"
              placeholder="https://monsite.com"
              [value]="demoUrl()"
              (input)="demoUrl.set($any($event.target).value)"
              (keydown.enter)="submit()"
              class="flex-1 bg-gray-900/80 border border-gray-700 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-500
                          focus:outline-none focus:ring-1 focus:ring-cyan-500/50 focus:border-cyan-500/60 transition-all"
            />
            <button
              type="button"
              (click)="submit()"
              [disabled]="demoLoading() || !demoUrl()"
              class="flex items-center gap-2 px-5 py-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-bold transition-all
                           disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0"
            >
              @if (demoLoading()) {
                <mat-spinner diameter="16" color="warn"></mat-spinner>
              } @else {
                <mat-icon class="!text-[1rem] !w-[1rem] !h-[1rem]">radar</mat-icon>
              }
              Scanner
            </button>
          </div>

          @if (demoError()) {
            <p class="text-red-400 text-xs mt-3 flex items-center gap-1.5">
              <mat-icon class="!text-[0.85rem] !w-[0.85rem] !h-[0.85rem]">error</mat-icon>
              {{ demoError() }}
            </p>
          }

          <p class="text-center text-xs text-gray-600 mt-4">
            3 scans gratuits par heure · Aucune donnée stockée au-delà de 7 jours
          </p>
        </div>
      </div>
    </section>
  `,
})
export class DemoScanComponent {
  private cyberscan = inject(CyberscanService);
  private router = inject(Router);

  demoUrl = signal('');
  demoLoading = signal(false);
  demoError = signal<string | null>(null);

  submit() {
    let url = this.demoUrl().trim();
    if (!url) return;
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'https://' + url;
    }
    this.demoLoading.set(true);
    this.demoError.set(null);
    this.cyberscan.createPublicScan(url).subscribe({
      next: res => {
        this.demoLoading.set(false);
        this.router.navigate(['/demo-result', res.token]);
      },
      error: err => {
        this.demoLoading.set(false);
        this.demoError.set(extractApiError(err, 'Erreur lors du lancement du scan. Réessayez.'));
      },
    });
  }
}
