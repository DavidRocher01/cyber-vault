import { Component, Input, OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';

interface AxisData {
  label: string;
  score: number;
  lineEnd:   { x: number; y: number };
  labelPos:  { x: number; y: number };
  dataPoint: { x: number; y: number };
  scoreOffset: { x: number; y: number };
}

@Component({
  selector: 'app-radar-chart',
  standalone: true,
  imports: [CommonModule],
  template: `
    <svg viewBox="0 0 300 300" class="w-full h-full">

      <!-- Grid polygons -->
      @for (level of gridLevels; track level) {
        <polygon [attr.points]="gridPolygon(level)"
                 fill="none" stroke="#374151"
                 [attr.stroke-width]="level === 100 ? 1 : 0.5"
                 [attr.opacity]="level === 100 ? 0.8 : 0.4"/>
      }

      <!-- Grid labels (%) -->
      <text [attr.x]="cx" [attr.y]="cy - radius * 0.5 - 3"
            text-anchor="middle" fill="#4b5563" font-size="7">50</text>
      <text [attr.x]="cx" [attr.y]="cy - radius - 3"
            text-anchor="middle" fill="#4b5563" font-size="7">100</text>

      <!-- Axis lines -->
      @for (axis of axes; track axis.label) {
        <line [attr.x1]="cx" [attr.y1]="cy"
              [attr.x2]="axis.lineEnd.x" [attr.y2]="axis.lineEnd.y"
              stroke="#374151" stroke-width="1" opacity="0.6"/>
      }

      <!-- Data fill -->
      <polygon [attr.points]="dataPolygon"
               fill="rgba(6,182,212,0.12)" stroke="none"/>

      <!-- Data border -->
      <polygon [attr.points]="dataPolygon"
               fill="none" stroke="#06b6d4" stroke-width="2"
               stroke-linejoin="round"/>

      <!-- Data points + score bubbles -->
      @for (axis of axes; track axis.label) {
        <circle [attr.cx]="axis.dataPoint.x" [attr.cy]="axis.dataPoint.y"
                r="4" fill="#06b6d4" stroke="#0e7490" stroke-width="1.5"/>
        <!-- Score value -->
        <text [attr.x]="axis.dataPoint.x + axis.scoreOffset.x"
              [attr.y]="axis.dataPoint.y + axis.scoreOffset.y"
              text-anchor="middle" dominant-baseline="middle"
              font-size="8" font-weight="bold"
              [attr.fill]="scoreColor(axis.score)">{{ axis.score }}</text>
      }

      <!-- Category labels -->
      @for (axis of axes; track axis.label) {
        <text [attr.x]="axis.labelPos.x" [attr.y]="axis.labelPos.y"
              text-anchor="middle" dominant-baseline="middle"
              fill="#9ca3af" font-size="10" font-weight="500">
          {{ axis.label }}
        </text>
      }

      <!-- Center dot -->
      <circle [attr.cx]="cx" [attr.cy]="cy" r="3" fill="#374151"/>
    </svg>
  `,
})
export class RadarChartComponent implements OnChanges {
  @Input() scores: number[] = [];
  @Input() labels: string[] = [];

  readonly cx = 150;
  readonly cy = 150;
  readonly radius = 85;
  readonly labelRadius = 110;
  readonly gridLevels = [25, 50, 75, 100];

  axes: AxisData[] = [];
  dataPolygon = '';

  ngOnChanges() {
    const n = this.labels.length;
    if (n === 0) return;

    this.axes = this.labels.map((label, i) => {
      const angle = -Math.PI / 2 + (i * 2 * Math.PI / n);
      const score = this.scores[i] ?? 0;
      const r = (score / 100) * this.radius;
      const dx = Math.cos(angle);
      const dy = Math.sin(angle);
      const len = Math.sqrt(dx * dx + dy * dy) || 1;
      return {
        label,
        score,
        lineEnd:   { x: this.cx + this.radius * dx,      y: this.cy + this.radius * dy },
        labelPos:  { x: this.cx + this.labelRadius * dx,  y: this.cy + this.labelRadius * dy },
        dataPoint: { x: this.cx + r * dx,                 y: this.cy + r * dy },
        scoreOffset: { x: (dx / len) * 12, y: (dy / len) * 12 },
      };
    });

    this.dataPolygon = this.axes.map(a => `${a.dataPoint.x},${a.dataPoint.y}`).join(' ');
  }

  gridPolygon(level: number): string {
    const n = this.labels.length;
    return Array.from({ length: n }, (_, i) => {
      const angle = -Math.PI / 2 + (i * 2 * Math.PI / n);
      const r = (level / 100) * this.radius;
      return `${this.cx + r * Math.cos(angle)},${this.cy + r * Math.sin(angle)}`;
    }).join(' ');
  }

  scoreColor(score: number): string {
    if (score >= 75) return '#4ade80';
    if (score >= 50) return '#facc15';
    return '#f87171';
  }
}
