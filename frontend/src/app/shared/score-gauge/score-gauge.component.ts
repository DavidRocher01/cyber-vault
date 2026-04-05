import { Component, Input, OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { getGrade, getScoreColor } from '../score-utils';

@Component({
  selector: 'app-score-gauge',
  standalone: true,
  imports: [CommonModule],
  template: `
    <svg viewBox="0 0 120 120" class="w-full h-full" style="overflow:visible">
      <!-- Outer glow ring -->
      <circle cx="60" cy="60" r="52" fill="none" [attr.stroke]="color"
              stroke-width="1" opacity="0.15"/>
      <!-- Track -->
      <circle cx="60" cy="60" r="46" fill="none" stroke="#1f2937" stroke-width="10"/>
      <!-- Score arc -->
      <circle cx="60" cy="60" r="46"
              fill="none"
              [attr.stroke]="color"
              stroke-width="10"
              stroke-linecap="round"
              [attr.stroke-dasharray]="dashArray"
              transform="rotate(-90 60 60)"
              style="transition: stroke-dasharray 1s cubic-bezier(.4,0,.2,1)"/>
      <!-- Grade badge background -->
      <circle cx="60" cy="60" r="32" fill="#111827"/>
      <!-- Score number -->
      <text x="60" y="56" text-anchor="middle" dominant-baseline="middle"
            font-size="22" font-weight="bold" [attr.fill]="color">{{ score }}</text>
      <!-- Grade letter -->
      <text x="60" y="74" text-anchor="middle" dominant-baseline="middle"
            font-size="11" fill="#6b7280" font-weight="600">{{ grade }}</text>
    </svg>
  `,
})
export class ScoreGaugeComponent implements OnChanges {
  @Input() score: number = 0;

  color = '#4ade80';
  dashArray = '0 289';

  private readonly circumference = 2 * Math.PI * 46;

  ngOnChanges() {
    this.color = getScoreColor(this.score);
    const filled = (this.score / 100) * this.circumference;
    this.dashArray = `${filled} ${this.circumference - filled}`;
  }

  get grade(): string { return getGrade(this.score); }
}
