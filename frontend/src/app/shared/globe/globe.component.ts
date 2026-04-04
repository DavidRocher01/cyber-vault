import { Component, ElementRef, ViewChild, AfterViewInit, OnDestroy, NgZone } from '@angular/core';

interface Point {
  lat: number;
  lng: number;
  size: number;
  opacity: number;
  pulse: number;
}

interface Arc {
  from: number;
  to: number;
  progress: number;
  speed: number;
}

@Component({
  selector: 'app-globe',
  standalone: true,
  template: `<canvas #canvas class="w-full h-full"></canvas>`,
})
export class GlobeComponent implements AfterViewInit, OnDestroy {
  @ViewChild('canvas') canvasRef!: ElementRef<HTMLCanvasElement>;

  private animationId = 0;
  private rotation = 0;

  constructor(private ngZone: NgZone) {}

  ngAfterViewInit() {
    this.ngZone.runOutsideAngular(() => this.init());
  }

  ngOnDestroy() {
    cancelAnimationFrame(this.animationId);
  }

  private init() {
    const canvas = this.canvasRef.nativeElement;
    const ctx = canvas.getContext('2d')!;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * window.devicePixelRatio;
      canvas.height = rect.height * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    };
    resize();
    window.addEventListener('resize', resize);

    const points: Point[] = Array.from({ length: 70 }, () => ({
      lat: (Math.random() - 0.5) * Math.PI,
      lng: Math.random() * Math.PI * 2,
      size: Math.random() * 1.5 + 0.8,
      opacity: Math.random() * 0.5 + 0.3,
      pulse: Math.random() * Math.PI * 2,
    }));

    const arcs: Arc[] = Array.from({ length: 14 }, () => ({
      from: Math.floor(Math.random() * points.length),
      to: Math.floor(Math.random() * points.length),
      progress: Math.random(),
      speed: 0.0015 + Math.random() * 0.002,
    }));

    const project = (lat: number, lng: number, W: number, H: number, R: number) => {
      const x = R * Math.cos(lat) * Math.cos(lng + this.rotation);
      const y = R * Math.sin(lat);
      const z = R * Math.cos(lat) * Math.sin(lng + this.rotation);
      return { x: W / 2 + x, y: H / 2 - y, z };
    };

    const bezier = (t: number, x0: number, y0: number, cx: number, cy: number, x1: number, y1: number) => ({
      x: (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x1,
      y: (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y1,
    });

    const draw = () => {
      const W = canvas.width / window.devicePixelRatio;
      const H = canvas.height / window.devicePixelRatio;
      const R = Math.min(W, H) * 0.38;

      ctx.clearRect(0, 0, W, H);
      this.rotation += 0.0015;
      const time = Date.now() * 0.001;

      // Grid lines
      ctx.lineWidth = 0.5;

      for (let lat = -Math.PI / 2; lat <= Math.PI / 2; lat += Math.PI / 7) {
        ctx.beginPath();
        ctx.strokeStyle = 'rgba(34, 211, 238, 0.07)';
        let first = true;
        for (let lng = 0; lng <= Math.PI * 2 + 0.05; lng += 0.04) {
          const p = project(lat, lng, W, H, R);
          if (p.z > 0) {
            first ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y);
            first = false;
          } else {
            first = true;
          }
        }
        ctx.stroke();
      }

      for (let lng = 0; lng < Math.PI * 2; lng += Math.PI / 7) {
        ctx.beginPath();
        ctx.strokeStyle = 'rgba(34, 211, 238, 0.07)';
        let first = true;
        for (let lat = -Math.PI / 2; lat <= Math.PI / 2; lat += 0.04) {
          const p = project(lat, lng, W, H, R);
          if (p.z > 0) {
            first ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y);
            first = false;
          } else {
            first = true;
          }
        }
        ctx.stroke();
      }

      // Arcs
      arcs.forEach(arc => {
        arc.progress += arc.speed;
        if (arc.progress > 1) {
          arc.progress = 0;
          arc.from = Math.floor(Math.random() * points.length);
          arc.to = Math.floor(Math.random() * points.length);
        }

        const pf = points[arc.from];
        const pt = points[arc.to];
        const from = project(pf.lat, pf.lng, W, H, R);
        const to = project(pt.lat, pt.lng, W, H, R);

        if (from.z < 0 || to.z < 0) return;

        const midX = (from.x + to.x) / 2;
        const midY = (from.y + to.y) / 2;
        const dist = Math.hypot(to.x - from.x, to.y - from.y);
        const cpX = midX;
        const cpY = midY - dist * 0.35;

        const alpha = Math.sin(arc.progress * Math.PI) * 0.7;
        ctx.beginPath();
        ctx.strokeStyle = `rgba(34, 211, 238, ${alpha})`;
        ctx.lineWidth = 1;

        const steps = 40;
        for (let i = 0; i <= Math.floor(steps * arc.progress); i++) {
          const t = i / steps;
          const pos = bezier(t, from.x, from.y, cpX, cpY, to.x, to.y);
          i === 0 ? ctx.moveTo(pos.x, pos.y) : ctx.lineTo(pos.x, pos.y);
        }
        ctx.stroke();

        // Arc head dot
        const head = bezier(arc.progress, from.x, from.y, cpX, cpY, to.x, to.y);
        ctx.beginPath();
        ctx.arc(head.x, head.y, 2.5, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(34, 211, 238, ${alpha + 0.2})`;
        ctx.fill();
      });

      // Points
      points.forEach(p => {
        const proj = project(p.lat, p.lng, W, H, R);
        if (proj.z <= 0) return;

        const pulse = Math.sin(time * 1.5 + p.pulse) * 0.25 + 0.75;
        const size = p.size * pulse;
        const glowR = size * 4;

        const glow = ctx.createRadialGradient(proj.x, proj.y, 0, proj.x, proj.y, glowR);
        glow.addColorStop(0, `rgba(34, 211, 238, ${p.opacity * pulse * 0.8})`);
        glow.addColorStop(1, 'rgba(34, 211, 238, 0)');
        ctx.beginPath();
        ctx.arc(proj.x, proj.y, glowR, 0, Math.PI * 2);
        ctx.fillStyle = glow;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(proj.x, proj.y, size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(34, 211, 238, ${p.opacity})`;
        ctx.fill();
      });

      this.animationId = requestAnimationFrame(draw);
    };

    draw();
  }
}
