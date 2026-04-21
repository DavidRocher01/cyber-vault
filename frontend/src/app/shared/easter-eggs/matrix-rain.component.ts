import { Component, Input, OnChanges, OnDestroy, ElementRef, ViewChild, AfterViewInit, ChangeDetectionStrategy, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';

const CHARS = 'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン0123456789ABCDEF<>/\\|{}[]';

@Component({
  selector: 'app-matrix-rain',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div *ngIf="visible" class="matrix-overlay" (click)="onClose()" title="Cliquer pour fermer">
      <canvas #canvas></canvas>
      <div class="matrix-hint">[ cliquer pour fermer ]</div>
    </div>
  `,
  styles: [`
    .matrix-overlay {
      position: fixed; inset: 0; z-index: 99998;
      background: #000; cursor: pointer;
    }
    canvas { display: block; width: 100%; height: 100%; }
    .matrix-hint {
      position: absolute; bottom: 1.5rem; left: 50%; transform: translateX(-50%);
      font-family: 'JetBrains Mono', monospace;
      color: rgba(0,255,70,0.5); font-size: 0.75rem; letter-spacing: 0.12em;
      pointer-events: none;
    }
  `],
})
export class MatrixRainComponent implements OnChanges, AfterViewInit, OnDestroy {
  @Input() visible = false;
  @ViewChild('canvas') canvasRef!: ElementRef<HTMLCanvasElement>;

  private rafId = 0;
  private drops: number[] = [];
  private autoClose: any;
  closeRequested = false;

  ngAfterViewInit(): void {
    if (this.visible) this.start();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['visible']) {
      if (this.visible) {
        setTimeout(() => this.start(), 0);
      } else {
        this.stop();
      }
    }
  }

  onClose(): void {
    this.closeRequested = true;
    this.stop();
  }

  private start(): void {
    this.closeRequested = false;
    const canvas = this.canvasRef?.nativeElement;
    if (!canvas) return;

    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    const cols = Math.floor(canvas.width / 16);
    this.drops = Array.from({ length: cols }, () => Math.random() * -canvas.height / 16);

    const ctx = canvas.getContext('2d')!;

    const draw = () => {
      ctx.fillStyle = 'rgba(0,0,0,0.05)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      for (let i = 0; i < this.drops.length; i++) {
        const ch = CHARS[Math.floor(Math.random() * CHARS.length)];
        const y = this.drops[i] * 16;
        const brightness = Math.random();
        ctx.fillStyle = brightness > 0.95 ? '#ffffff' : brightness > 0.7 ? '#00ff46' : '#007a22';
        ctx.font = `${14 + Math.random() * 4}px 'JetBrains Mono', monospace`;
        ctx.fillText(ch, i * 16, y);
        if (y > canvas.height && Math.random() > 0.975) {
          this.drops[i] = 0;
        }
        this.drops[i] += 0.5 + Math.random() * 0.5;
      }
      this.rafId = requestAnimationFrame(draw);
    };

    this.rafId = requestAnimationFrame(draw);
    this.autoClose = setTimeout(() => this.stop(), 6000);
  }

  private stop(): void {
    cancelAnimationFrame(this.rafId);
    clearTimeout(this.autoClose);
  }

  ngOnDestroy(): void {
    this.stop();
  }
}
