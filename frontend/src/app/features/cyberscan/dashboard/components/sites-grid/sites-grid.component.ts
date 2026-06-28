import { Component, Input, Output, EventEmitter } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ScoreGaugeComponent } from '../../../../../shared/score-gauge/score-gauge.component';
import { Site } from '../../../services/cyberscan.service';

export interface SiteBadgeInfo {
  cssClass: string;
  label: string;
  icon: string;
}

@Component({
  standalone: true,
  selector: 'app-sites-grid',
  imports: [
    RouterLink,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    ScoreGaugeComponent,
  ],
  template: `
    @for (site of sites; track site.id) {
      <div class="rounded-2xl border border-gray-700/60 bg-gray-800/40 overflow-hidden">
        <!-- Site Header -->
        <div
          class="flex items-center justify-between px-5 py-4 border-b border-gray-700/50 flex-wrap gap-3"
        >
          <div class="flex items-center gap-4">
            @if (getLastScore(site.id); as score) {
              <div class="flex flex-col items-center gap-0.5 flex-shrink-0">
                <div class="w-12 h-12">
                  <app-score-gauge [score]="score"></app-score-gauge>
                </div>
                @if (getTrend(site.id); as trend) {
                  <span
                    class="text-[10px] font-bold flex items-center gap-0.5"
                    [class.text-green-400]="trend > 0"
                    [class.text-red-400]="trend < 0"
                    [class.text-gray-500]="trend === 0"
                  >
                    <mat-icon class="!text-[0.65rem] !w-[0.65rem] !h-[0.65rem]">
                      {{
                        trend > 0 ? 'trending_up' : trend < 0 ? 'trending_down' : 'trending_flat'
                      }}
                    </mat-icon>
                    {{ trend > 0 ? '+' : '' }}{{ trend }}
                  </span>
                }
              </div>
            }
            <div>
              <div class="flex items-center gap-2 flex-wrap">
                <a
                  [routerLink]="['/site', site.id]"
                  class="font-bold text-white hover:text-cyan-400 transition-colors"
                  >{{ site.name }}</a
                >
                <span
                  class="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border font-medium"
                  [class]="getBadge(site.id).cssClass"
                >
                  <mat-icon class="!text-[0.7rem] !w-[0.7rem] !h-[0.7rem]">{{
                    getBadge(site.id).icon
                  }}</mat-icon>
                  {{ getBadge(site.id).label }}
                </span>
              </div>
              <a
                [href]="site.url"
                target="_blank"
                class="text-xs text-cyan-500/80 hover:text-cyan-400 hover:underline transition-colors mt-0.5 block"
              >
                {{ site.url }}
              </a>
              <!-- SSL expiry warning -->
              @if (getSslDaysRemaining(site.id); as days) {
                @if (days <= 30) {
                  <span
                    class="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full font-semibold mt-1"
                    [class]="
                      days <= 7
                        ? 'bg-red-500/15 text-red-400 border border-red-700/40'
                        : days <= 14
                          ? 'bg-orange-500/15 text-orange-400 border border-orange-700/40'
                          : 'bg-yellow-500/15 text-yellow-400 border border-yellow-700/40'
                    "
                  >
                    <mat-icon class="!text-[0.65rem] !w-[0.65rem] !h-[0.65rem]"
                      >lock_clock</mat-icon
                    >
                    SSL expire dans {{ days }}j
                  </span>
                }
              }
            </div>
          </div>
          <div class="flex items-center gap-1.5">
            <a
              [routerLink]="['/subdomains', site.id]"
              class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-teal-700/40 text-teal-400 hover:bg-teal-500/10 hover:border-teal-500 transition-all"
            >
              <mat-icon class="!text-[0.85rem] !w-[0.85rem] !h-[0.85rem]">dns</mat-icon>
              DNS
            </a>
            <a
              [routerLink]="['/site', site.id]"
              class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/10 hover:border-cyan-400 transition-all"
            >
              <mat-icon class="!text-[0.85rem] !w-[0.85rem] !h-[0.85rem]">arrow_forward</mat-icon>
              Détails
            </a>
            <button
              mat-flat-button
              type="button"
              color="primary"
              class="!text-xs"
              [disabled]="isTriggering(site.id)"
              (click)="triggerScan.emit(site.id)"
            >
              @if (isTriggering(site.id)) {
                <mat-spinner diameter="14" class="mr-1"></mat-spinner>
              } @else {
                <mat-icon class="!text-[0.9rem] !w-[0.9rem] !h-[0.9rem] mr-1">play_arrow</mat-icon>
              }
              Scanner
            </button>
            <button
              mat-icon-button
              type="button"
              (click)="deleteSite.emit(site)"
              class="!text-gray-500 hover:!text-red-400 !w-8 !h-8"
            >
              <mat-icon class="!text-[1rem]">delete</mat-icon>
            </button>
          </div>
        </div>

        <!-- Progress bar -->
        @if (hasActiveScans(site.id)) {
          <div class="h-0.5 w-full bg-gray-700">
            <div class="h-full bg-cyan-500 animate-pulse w-full"></div>
          </div>
        }
      </div>
    }
  `,
})
export class SitesGridComponent {
  @Input() sites: Site[] = [];
  /** Map siteId → last score */
  @Input() lastScores: Record<number, number | null> = {};
  /** Map siteId → trend delta */
  @Input() trends: Record<number, number | null> = {};
  /** Map siteId → SSL days remaining */
  @Input() sslDays: Record<number, number | null> = {};
  /** Map siteId → triggering flag */
  @Input() triggeringScansMap: Record<number, boolean> = {};
  /** Map siteId → has active scans */
  @Input() activeScansMap: Record<number, boolean> = {};
  /** Map siteId → last scan status string */
  @Input() lastScanStatuses: Record<number, string | null> = {};

  @Output() triggerScan = new EventEmitter<number>();
  @Output() deleteSite = new EventEmitter<Site>();

  getLastScore(siteId: number): number | null {
    return this.lastScores[siteId] ?? null;
  }

  getTrend(siteId: number): number | null {
    return this.trends[siteId] ?? null;
  }

  getSslDaysRemaining(siteId: number): number | null {
    return this.sslDays[siteId] ?? null;
  }

  isTriggering(siteId: number): boolean {
    return this.triggeringScansMap[siteId] ?? false;
  }

  hasActiveScans(siteId: number): boolean {
    return this.activeScansMap[siteId] ?? false;
  }

  getBadge(siteId: number): SiteBadgeInfo {
    if (this.hasActiveScans(siteId)) {
      return {
        cssClass: 'bg-blue-500/20 text-blue-300 border-blue-600',
        label: 'En cours...',
        icon: 'sync',
      };
    }
    const status = this.lastScanStatuses[siteId] ?? null;
    switch (status) {
      case 'OK':
        return {
          cssClass: 'bg-green-500/20 text-green-300 border-green-600',
          label: 'OK',
          icon: 'verified_user',
        };
      case 'WARNING':
        return {
          cssClass: 'bg-yellow-500/20 text-yellow-300 border-yellow-600',
          label: 'WARNING',
          icon: 'warning',
        };
      case 'CRITICAL':
        return {
          cssClass: 'bg-red-500/20 text-red-300 border-red-600',
          label: 'CRITICAL',
          icon: 'gpp_bad',
        };
      default:
        return {
          cssClass: 'bg-gray-700 text-gray-400 border-gray-600',
          label: 'Aucun scan',
          icon: 'help_outline',
        };
    }
  }
}
