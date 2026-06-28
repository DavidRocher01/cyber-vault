import { Component, signal, PLATFORM_ID, inject, OnInit } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import { catchError, of } from 'rxjs';

/**
 * Bandeau d'annonce de maintenance, piloté AU RUNTIME par `assets/maintenance.json`.
 *
 * Activer/désactiver sans rebuild : éditer le JSON dans le bucket S3 puis invalider
 * `/maintenance.json` sur CloudFront (cf. docs/RELEASE_RUNBOOK.md § Maintenance).
 *
 * Schéma attendu :
 *   { "active": bool, "level": "warning"|"critical"|"info", "message": str, "until": ISO|null }
 */
interface MaintenanceConfig {
  active: boolean;
  level?: 'info' | 'warning' | 'critical';
  message?: string;
  until?: string | null;
}

const DISMISS_KEY = 'cyberscan_maintenance_dismissed';

@Component({
  standalone: true,
  selector: 'app-maintenance-banner',
  imports: [MatIconModule],
  template: `
    @if (visible()) {
      <div
        role="status"
        aria-live="polite"
        class="fixed top-0 left-0 right-0 z-[60] px-4 py-3 border-b backdrop-blur-sm"
        [class]="barClasses()"
      >
        <div class="max-w-5xl mx-auto flex items-center gap-3">
          <mat-icon class="flex-shrink-0">{{ icon() }}</mat-icon>
          <div class="flex-1 text-sm">
            <span class="font-semibold">{{ message() }}</span>
            @if (untilLabel()) {
              <span class="opacity-80 ml-1">{{ untilLabel() }}</span>
            }
          </div>
          <button
            type="button"
            (click)="dismiss()"
            aria-label="Masquer l'annonce de maintenance"
            class="flex-shrink-0 opacity-70 hover:opacity-100 transition-opacity"
          >
            <mat-icon>close</mat-icon>
          </button>
        </div>
      </div>
    }
  `,
})
export class MaintenanceBannerComponent implements OnInit {
  private platformId = inject(PLATFORM_ID);
  private http = inject(HttpClient);

  visible = signal(false);
  message = signal('');
  untilLabel = signal('');
  level = signal<'info' | 'warning' | 'critical'>('warning');

  icon = () =>
    this.level() === 'critical' ? 'error' : this.level() === 'info' ? 'info' : 'warning';

  barClasses = () => {
    switch (this.level()) {
      case 'critical':
        return 'bg-red-900/95 border-red-700 text-red-100';
      case 'info':
        return 'bg-cyan-900/95 border-cyan-700 text-cyan-100';
      default:
        return 'bg-amber-900/95 border-amber-700 text-amber-100';
    }
  };

  ngOnInit(): void {
    // Runtime-only : pas de fetch pendant le prerendering SSR.
    if (!isPlatformBrowser(this.platformId)) return;

    this.http
      .get<MaintenanceConfig>('assets/maintenance.json', {
        // cache-buster léger : l'invalidation CloudFront reste la source de vérité
        params: { _t: String(Date.now()) },
      })
      .pipe(catchError(() => of(null)))
      .subscribe(cfg => {
        if (!cfg?.active || !cfg.message) return;
        if (this.isDismissed(cfg.message)) return;
        this.level.set(cfg.level ?? 'warning');
        this.message.set(cfg.message);
        this.untilLabel.set(this.formatUntil(cfg.until));
        this.visible.set(true);
      });
  }

  dismiss(): void {
    if (isPlatformBrowser(this.platformId)) {
      // Dismissal lié au message courant : un nouveau message ré-affiche le bandeau.
      localStorage.setItem(DISMISS_KEY, this.message());
    }
    this.visible.set(false);
  }

  private isDismissed(message: string): boolean {
    return localStorage.getItem(DISMISS_KEY) === message;
  }

  private formatUntil(until?: string | null): string {
    if (!until) return '';
    const d = new Date(until);
    if (isNaN(d.getTime())) return '';
    return `(jusqu'à ${d.toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })})`;
  }
}
