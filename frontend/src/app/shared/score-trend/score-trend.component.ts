import { Component, Input, OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';

export interface ScoreTrendPoint {
  date: string;   // ISO string
  score: number;  // 0-100
}

interface ChartPoint {
  x: number;
  y: number;
  score: number;
  label: string;
}

@Component({
    selector: 'app-score-trend',
    imports: [CommonModule],
    template: `
    @if (points.length < 2) {
      <div class="flex items-center justify-center h-full text-gray-500 text-sm">
        Pas encore assez de scans pour afficher la tendance.
      </div>
    } @else {
      <svg [attr.viewBox]="'0 0 ' + W + ' ' + H" class="w-full h-full overflow-visible">
        <defs>
          <linearGradient id="trend-area-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stop-color="#22d3ee" stop-opacity="0.25"/>
            <stop offset="100%" stop-color="#22d3ee" stop-opacity="0.02"/>
          </linearGradient>
        </defs>

        <!-- Y grid lines & labels -->
        @for (tick of yTicks; track tick) {
          <line [attr.x1]="PAD_L" [attr.x2]="W - PAD_R"
                [attr.y1]="yScale(tick)" [attr.y2]="yScale(tick)"
                stroke="rgba(255,255,255,0.06)" stroke-width="1"/>
          <text [attr.x]="PAD_L - 6" [attr.y]="yScale(tick) + 4"
                text-anchor="end" font-size="9" fill="rgba(255,255,255,0.35)">{{ tick }}</text>
        }

        <!-- Area fill -->
        <path [attr.d]="areaPath" fill="url(#trend-area-grad)"/>

        <!-- Line -->
        <path [attr.d]="linePath" fill="none" stroke="#22d3ee" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>

        <!-- Data points -->
        @for (p of points; track p.label) {
          <circle [attr.cx]="p.x" [attr.cy]="p.y" r="4"
                  [attr.fill]="dotColor(p.score)" stroke="#0f172a" stroke-width="2"/>
          <!-- X-axis date label -->
          <text [attr.x]="p.x" [attr.y]="H - PAD_B + 14"
                text-anchor="middle" font-size="9" fill="rgba(255,255,255,0.35)">{{ p.label }}</text>
          <!-- Score tooltip on hover via title -->
          <title>{{ p.score }}/100 — {{ p.label }}</title>
        }
      </svg>
    }
  `
})
export class ScoreTrendComponent implements OnChanges {
  @Input() data: ScoreTrendPoint[] = [];

  readonly W = 500;
  readonly H = 140;
  readonly PAD_L = 30;
  readonly PAD_R = 10;
  readonly PAD_T = 12;
  readonly PAD_B = 20;

  readonly yTicks = [0, 25, 50, 75, 100];

  points: ChartPoint[] = [];
  linePath = '';
  areaPath = '';

  ngOnChanges() {
    if (this.data.length < 2) { this.points = []; return; }

    const sorted = [...this.data].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
    const n = sorted.length;
    const xStep = (this.W - this.PAD_L - this.PAD_R) / (n - 1);

    this.points = sorted.map((d, i) => ({
      x: this.PAD_L + i * xStep,
      y: this.yScale(d.score),
      score: d.score,
      label: new Date(d.date).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' }),
    }));

    this.linePath = this.points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ');

    const bottom = this.H - this.PAD_B;
    this.areaPath = [
      this.linePath,
      `L${this.points[n - 1].x},${bottom}`,
      `L${this.points[0].x},${bottom}`,
      'Z',
    ].join(' ');
  }

  yScale(score: number): number {
    const chartH = this.H - this.PAD_T - this.PAD_B;
    return this.PAD_T + chartH * (1 - score / 100);
  }

  dotColor(score: number): string {
    if (score >= 75) return '#4ade80';
    if (score >= 50) return '#facc15';
    return '#f87171';
  }
}
