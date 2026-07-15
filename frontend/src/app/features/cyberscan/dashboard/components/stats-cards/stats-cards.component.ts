import { Component, Input } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { ScoreGaugeComponent } from '../../../../../shared/score-gauge/score-gauge.component';
import { getGrade, getScoreColor } from '../../../../../shared/score-utils';
import { Subscription as UserSubscription } from '../../../services/cyberscan.service';

@Component({
  standalone: true,
  selector: 'app-stats-cards',
  imports: [MatIconModule, ScoreGaugeComponent],
  template: `
    @if (averageScore !== null) {
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div class="dashboard-stat-card col-span-2 md:col-span-1 flex items-center gap-4">
          <div class="w-14 h-14 flex-shrink-0">
            <app-score-gauge [score]="averageScore!"></app-score-gauge>
          </div>
          <div>
            <p class="text-xs text-gray-500 uppercase tracking-wider mb-0.5">Score moyen</p>
            <p class="font-bold text-white">{{ getGrade(averageScore!) }}</p>
            <p class="text-xs text-gray-400">{{ averageScore }}/100</p>
          </div>
        </div>
        <div class="dashboard-stat-card flex items-center gap-3">
          <div
            class="w-9 h-9 rounded-lg bg-cyan-500/10 flex items-center justify-center flex-shrink-0"
          >
            <mat-icon class="text-cyan-400 !text-[1.1rem] !w-[1.1rem] !h-[1.1rem]"
              >language</mat-icon
            >
          </div>
          <div>
            <p class="text-2xl font-bold">{{ sitesCount }}</p>
            <p class="text-xs text-gray-500">
              site{{ sitesCount > 1 ? 's' : '' }} surveillé{{ sitesCount > 1 ? 's' : '' }}
            </p>
          </div>
        </div>
        <div class="dashboard-stat-card flex items-center gap-3">
          <div
            class="w-9 h-9 rounded-lg bg-green-500/10 flex items-center justify-center flex-shrink-0"
          >
            <mat-icon class="text-green-400 !text-[1.1rem] !w-[1.1rem] !h-[1.1rem]"
              >analytics</mat-icon
            >
          </div>
          <div>
            <p class="text-2xl font-bold">{{ totalScans }}</p>
            <p class="text-xs text-gray-500">scans effectués</p>
          </div>
        </div>
        <div class="dashboard-stat-card flex items-center gap-3">
          <div
            class="w-9 h-9 rounded-lg bg-yellow-500/10 flex items-center justify-center flex-shrink-0"
          >
            <mat-icon class="text-yellow-400 !text-[1.1rem] !w-[1.1rem] !h-[1.1rem]"
              >schedule</mat-icon
            >
          </div>
          <div>
            <p class="text-2xl font-bold">
              {{ subscription?.plan?.scan_interval_days || '—' }}
            </p>
            <p class="text-xs text-gray-500">
              {{
                subscription?.plan?.scan_interval_days ? 'jours entre scans' : 'scan à la demande'
              }}
            </p>
          </div>
        </div>
      </div>
    }
  `,
})
export class StatsCardsComponent {
  @Input() averageScore: number | null = null;
  @Input() sitesCount = 0;
  @Input() totalScans = 0;
  @Input() subscription: UserSubscription | null = null;

  getGrade = getGrade;
  getScoreColor = getScoreColor;
}
