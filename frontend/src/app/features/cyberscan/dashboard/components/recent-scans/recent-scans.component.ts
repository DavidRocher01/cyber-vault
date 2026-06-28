import { Component, Input, Output, EventEmitter } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { SkeletonComponent } from '../../../../../shared/skeleton/skeleton.component';
import { Scan } from '../../../services/cyberscan.service';
import { computeScore, getScoreColor } from '../../../../../shared/score-utils';

@Component({
  standalone: true,
  selector: 'app-recent-scans',
  imports: [
    RouterLink,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatPaginatorModule,
    SkeletonComponent,
  ],
  template: `
    <div class="px-5 py-3">
      @if (loading) {
        <div class="py-3">
          <div class="flex items-center gap-2.5 mb-3 px-1">
            <div class="relative w-4 h-4 flex-shrink-0">
              <span class="radar-ring absolute inset-0 rounded-full bg-cyan-500/30"></span>
              <span
                class="relative flex w-4 h-4 rounded-full bg-cyan-500/10 border border-cyan-500/40 items-center justify-center"
              >
                <mat-icon class="text-cyan-400 !text-[0.6rem] !w-[0.6rem] !h-[0.6rem]"
                  >radar</mat-icon
                >
              </span>
            </div>
            <span class="text-xs text-gray-500 animate-pulse tracking-wide"
              >Récupération des scans…</span
            >
          </div>
          <div class="scan-skeleton-grid pb-2 mb-1 border-b border-gray-700/40">
            @for (w of ['55%', '45%', '40%', '35%', '30%']; track w) {
              <app-skeleton height="0.55rem" [width]="w" cssClass="rounded-full"></app-skeleton>
            }
          </div>
          @for (row of [1, 2, 3]; track row) {
            <div class="scan-skeleton-grid py-2.5 border-b border-gray-700/20 last:border-0">
              <app-skeleton height="0.7rem" cssClass="rounded-full"></app-skeleton>
              <div class="flex items-center gap-1.5">
                <app-skeleton
                  height="0.7rem"
                  width="0.7rem"
                  cssClass="!rounded-full"
                ></app-skeleton>
                <app-skeleton height="0.7rem" cssClass="rounded-full"></app-skeleton>
              </div>
              <app-skeleton
                height="0.7rem"
                [width]="row === 2 ? '65%' : '82%'"
                cssClass="rounded-full"
              ></app-skeleton>
              <app-skeleton height="0.7rem" width="45%" cssClass="rounded-full"></app-skeleton>
              <div class="flex justify-end gap-1">
                <app-skeleton height="1.4rem" width="1.4rem" cssClass="rounded-md"></app-skeleton>
                <app-skeleton height="1.4rem" width="1.4rem" cssClass="rounded-md"></app-skeleton>
              </div>
            </div>
          }
        </div>
      } @else if (scans.length === 0) {
        <p class="text-sm text-gray-500 text-center py-5">
          {{ emptyMessage }}
        </p>
      } @else {
        <table class="w-full text-sm">
          <thead>
            <tr class="text-gray-500 text-xs border-b border-gray-700/50">
              <th class="text-left py-2 pb-2.5 font-medium">Date</th>
              <th class="text-left py-2 pb-2.5 font-medium">Statut</th>
              <th class="text-left py-2 pb-2.5 font-medium">Résultat</th>
              <th class="text-left py-2 pb-2.5 font-medium">Score</th>
              <th class="text-right py-2 pb-2.5 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            @for (scan of scans; track scan.id) {
              <tr
                class="border-b border-gray-700/30 last:border-0 hover:bg-gray-700/20 transition-colors"
              >
                <td class="py-2.5 text-gray-400 text-xs">
                  {{ formatDate(scan.created_at) }}
                </td>
                <td class="py-2.5">
                  <span class="flex items-center gap-1 text-xs" [class]="statusColor(scan.status)">
                    <mat-icon class="!text-[0.85rem] !w-[0.85rem] !h-[0.85rem]">{{
                      statusIcon(scan.status)
                    }}</mat-icon>
                    {{ scan.status }}
                  </span>
                </td>
                <td class="py-2.5">
                  @if (scan.overall_status) {
                    <span
                      class="flex items-center gap-1 text-xs font-semibold"
                      [class]="statusColor(scan.overall_status)"
                    >
                      <mat-icon class="!text-[0.85rem] !w-[0.85rem] !h-[0.85rem]">{{
                        statusIcon(scan.overall_status)
                      }}</mat-icon>
                      {{ scan.overall_status }}
                    </span>
                  } @else {
                    <span class="text-gray-600 text-xs">—</span>
                  }
                </td>
                <td class="py-2.5">
                  @if (getScanScore(scan); as score) {
                    <span class="font-bold text-sm" [style.color]="getScoreColor(score)">
                      {{ score }}<span class="text-gray-600 font-normal text-xs">/100</span>
                    </span>
                  } @else {
                    <span class="text-gray-600 text-xs">—</span>
                  }
                </td>
                <td class="py-2.5 text-right">
                  <a
                    [routerLink]="['/cyberscan/scan', scan.id]"
                    mat-icon-button
                    class="!text-gray-400 hover:!text-cyan-400 !w-7 !h-7"
                  >
                    <mat-icon class="!text-[1rem]">open_in_new</mat-icon>
                  </a>
                  @if (scan.pdf_path) {
                    <button
                      mat-icon-button
                      type="button"
                      (click)="downloadPdf.emit(scan.id)"
                      class="!text-cyan-400 !w-7 !h-7"
                    >
                      <mat-icon class="!text-[1rem]">picture_as_pdf</mat-icon>
                    </button>
                  }
                </td>
              </tr>
            }
          </tbody>
        </table>
        @if (total > perPage) {
          <mat-paginator
            [length]="total"
            [pageSize]="perPage"
            [pageIndex]="currentPage"
            [pageSizeOptions]="[10, 20]"
            (page)="pageChange.emit($event)"
            class="bg-transparent text-gray-400 mt-1"
          >
          </mat-paginator>
        }
      }
    </div>
  `,
})
export class RecentScansComponent {
  @Input() scans: Scan[] = [];
  @Input() loading = false;
  @Input() total = 0;
  @Input() perPage = 10;
  @Input() currentPage = 0;
  @Input() emptyMessage = 'Aucun scan pour ce site';

  @Output() downloadPdf = new EventEmitter<number>();
  @Output() pageChange = new EventEmitter<PageEvent>();

  getScoreColor = getScoreColor;

  getScanScore(scan: Scan): number | null {
    return computeScore(scan.results_json ?? null);
  }

  statusColor(s: string | null): string {
    switch (s) {
      case 'OK':
        return 'text-green-400';
      case 'WARNING':
        return 'text-yellow-400';
      case 'CRITICAL':
      case 'error':
        return 'text-red-400';
      case 'done':
        return 'text-green-400';
      case 'pending':
      case 'running':
        return 'text-blue-400';
      default:
        return 'text-gray-400';
    }
  }

  statusIcon(s: string | null): string {
    switch (s) {
      case 'OK':
        return 'verified_user';
      case 'WARNING':
        return 'warning';
      case 'CRITICAL':
        return 'gpp_bad';
      case 'done':
        return 'check_circle';
      case 'pending':
        return 'schedule';
      case 'running':
        return 'sync';
      case 'error':
        return 'cancel';
      default:
        return 'help_outline';
    }
  }

  formatDate(d: string | null): string {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
}
