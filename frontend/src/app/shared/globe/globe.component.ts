import { Component, ElementRef, ViewChild, AfterViewInit, OnDestroy, NgZone } from '@angular/core';

const DEG = Math.PI / 180;

const CITIES = [
  { lat: 48.85,  lng:   2.35 }, // Paris
  { lat: 40.71,  lng: -74.00 }, // New York
  { lat: 35.68,  lng: 139.69 }, // Tokyo
  { lat: 51.51,  lng:  -0.12 }, // London
  { lat: 39.91,  lng: 116.39 }, // Beijing
  { lat: -33.86, lng: 151.20 }, // Sydney
  { lat: 55.75,  lng:  37.61 }, // Moscow
  { lat: -23.54, lng: -46.63 }, // São Paulo
  { lat: 25.20,  lng:  55.27 }, // Dubai
  { lat:  1.35,  lng: 103.82 }, // Singapore
  { lat: 37.77,  lng:-122.41 }, // San Francisco
  { lat: 19.07,  lng:  72.87 }, // Mumbai
  { lat: -26.20, lng:  28.04 }, // Johannesburg
  { lat: 41.00,  lng:  28.95 }, // Istanbul
  { lat: 52.52,  lng:  13.40 }, // Berlin
  { lat: 43.65,  lng: -79.38 }, // Toronto
  { lat: 37.56,  lng: 126.97 }, // Seoul
  { lat: 19.43,  lng: -99.13 }, // Mexico City
  { lat: 30.04,  lng:  31.24 }, // Cairo
  { lat: 25.03,  lng: 121.56 }, // Taipei
  { lat: 52.37,  lng:   4.89 }, // Amsterdam
  { lat: 59.33,  lng:  18.07 }, // Stockholm
  { lat: 41.87,  lng: -87.62 }, // Chicago
  { lat:  6.45,  lng:   3.40 }, // Lagos
  { lat: -6.21,  lng: 106.84 }, // Jakarta
  { lat:-34.60,  lng: -58.38 }, // Buenos Aires
  { lat: 35.69,  lng:  51.42 }, // Tehran
  { lat: 24.86,  lng:  67.01 }, // Karachi
  { lat: 13.75,  lng: 100.52 }, // Bangkok
  { lat: -1.29,  lng:  36.82 }, // Nairobi
  { lat: 45.50,  lng:  -73.57 }, // Montreal
  { lat: 48.14,  lng:  17.11 }, // Bratislava
  { lat: 22.54,  lng: 114.06 }, // Hong Kong
];

// Arc severity: 0 = red attack, 1 = orange warning, 2 = yellow probe
const ARC_TYPES = [
  { color: [239, 68, 68],   trail: [220, 38, 38],   weight: 5 }, // red (attacks)
  { color: [251, 146, 60],  trail: [234, 88, 12],    weight: 3 }, // orange (warnings)
  { color: [250, 204, 21],  trail: [202, 138, 4],    weight: 2 }, // yellow (probes)
];

interface Arc {
  from: number;
  to: number;
  progress: number;
  speed: number;
  type: number;
}

interface Star {
  x: number;
  y: number;
  r: number;
  opacity: number;
}

@Component({
  selector: 'app-globe',
  standalone: true,
  template: `<canvas #canvas style="display:block;width:100%;height:100%"></canvas>`,
})
export class GlobeComponent implements AfterViewInit, OnDestroy {
  @ViewChild('canvas') canvasRef!: ElementRef<HTMLCanvasElement>;

  private rafId = 0;
  private rotation = 0;
  private stars: Star[] = [];

  constructor(private ngZone: NgZone) {}

  ngAfterViewInit() {
    this.ngZone.runOutsideAngular(() => this.init());
  }

  ngOnDestroy() {
    cancelAnimationFrame(this.rafId);
  }

  private init() {
    const canvas = this.canvasRef.nativeElement;
    const ctx = canvas.getContext('2d')!;
    let W = 0, H = 0;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      W = rect.width;
      H = rect.height;
      canvas.width  = W * window.devicePixelRatio;
      canvas.height = H * window.devicePixelRatio;
      ctx.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);
      this.generateStars(W, H);
    };
    resize();
    window.addEventListener('resize', resize);

    // Generate arcs
    const arcs: Arc[] = Array.from({ length: 18 }, () => this.randomArc());

    const project = (latDeg: number, lngDeg: number, R: number) => {
      const lat = latDeg * DEG;
      const lng = (lngDeg + this.rotation) * DEG;
      const x = R * Math.cos(lat) * Math.sin(lng);
      const y = -R * Math.sin(lat);
      const z = R * Math.cos(lat) * Math.cos(lng);
      return { x: W / 2 + x, y: H / 2 + y, z };
    };

    const bez = (t: number, ax: number, ay: number, bx: number, by: number, cx: number, cy: number) => ({
      x: (1-t)**2*ax + 2*(1-t)*t*bx + t**2*cx,
      y: (1-t)**2*ay + 2*(1-t)*t*by + t**2*cy,
    });

    const draw = () => {
      const R = Math.min(W, H) * 0.4;
      const cx = W / 2, cy = H / 2;

      ctx.clearRect(0, 0, W, H);
      this.rotation += 0.04; // degrees/frame

      // 1. Stars
      for (const s of this.stars) {
        ctx.globalAlpha = s.opacity;
        ctx.fillStyle = '#fff';
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;

      // 2. Atmospheric glow
      const glow = ctx.createRadialGradient(cx, cy, R * 0.88, cx, cy, R * 1.25);
      glow.addColorStop(0,   'rgba(34,211,238,0.12)');
      glow.addColorStop(0.4, 'rgba(34,211,238,0.05)');
      glow.addColorStop(1,   'rgba(34,211,238,0)');
      ctx.beginPath();
      ctx.arc(cx, cy, R * 1.25, 0, Math.PI * 2);
      ctx.fillStyle = glow;
      ctx.fill();

      // Inner ambient
      const inner = ctx.createRadialGradient(cx, cy, 0, cx, cy, R);
      inner.addColorStop(0,   'rgba(17,24,39,0)');
      inner.addColorStop(0.7, 'rgba(17,24,39,0)');
      inner.addColorStop(1,   'rgba(17,24,39,0.5)');
      ctx.beginPath();
      ctx.arc(cx, cy, R, 0, Math.PI * 2);
      ctx.fillStyle = inner;
      ctx.fill();

      // 3. Globe wireframe — latitude lines
      for (let lat = -80; lat <= 80; lat += 20) {
        ctx.beginPath();
        let first = true;
        for (let lng = 0; lng <= 360; lng += 2) {
          const p = project(lat, lng, R);
          const alpha = Math.max(0, p.z / R) * 0.18 + 0.03;
          if (p.z > -R * 0.1) {
            if (first) { ctx.moveTo(p.x, p.y); first = false; }
            else ctx.lineTo(p.x, p.y);
          } else {
            first = true;
          }
        }
        ctx.strokeStyle = `rgba(34,211,238,${lat === 0 ? 0.22 : 0.09})`;
        ctx.lineWidth = lat === 0 ? 0.8 : 0.4;
        ctx.stroke();
      }

      // Longitude lines
      for (let lng = 0; lng < 360; lng += 20) {
        ctx.beginPath();
        let first = true;
        for (let lat = -90; lat <= 90; lat += 2) {
          const p = project(lat, lng, R);
          if (p.z > -R * 0.1) {
            if (first) { ctx.moveTo(p.x, p.y); first = false; }
            else ctx.lineTo(p.x, p.y);
          } else {
            first = true;
          }
        }
        ctx.strokeStyle = 'rgba(34,211,238,0.07)';
        ctx.lineWidth = 0.4;
        ctx.stroke();
      }

      // 4. Attack arcs
      for (let i = 0; i < arcs.length; i++) {
        const arc = arcs[i];
        arc.progress += arc.speed;
        if (arc.progress > 1.05) arcs[i] = this.randomArc();

        const t = Math.min(arc.progress, 1);
        const pf = project(CITIES[arc.from].lat, CITIES[arc.from].lng, R);
        const pt = project(CITIES[arc.to].lat,   CITIES[arc.to].lng,   R);

        if (pf.z < -R * 0.2 && pt.z < -R * 0.2) continue;

        const midX = (pf.x + pt.x) / 2;
        const midY = (pf.y + pt.y) / 2;
        const dist  = Math.hypot(pt.x - pf.x, pt.y - pf.y);
        const lift  = Math.max(dist * 0.45, R * 0.15);
        const cpX   = midX;
        const cpY   = midY - lift;

        const type  = ARC_TYPES[arc.type];
        const [r, g, b] = type.color;
        const fadeAlpha = Math.sin(Math.min(t, 0.95) * Math.PI) * 0.85;

        // Trail — draw segments, fading near start
        const STEPS = 60;
        const headStep = Math.floor(STEPS * t);
        const trailStart = Math.max(0, headStep - 20);

        for (let s = trailStart; s < headStep; s++) {
          const ta = s / STEPS;
          const tb = (s + 1) / STEPS;
          const pa = bez(ta, pf.x, pf.y, cpX, cpY, pt.x, pt.y);
          const pb = bez(tb, pf.x, pf.y, cpX, cpY, pt.x, pt.y);
          const segAlpha = ((s - trailStart) / (headStep - trailStart)) * fadeAlpha;

          ctx.beginPath();
          ctx.moveTo(pa.x, pa.y);
          ctx.lineTo(pb.x, pb.y);
          // Outer glow
          ctx.strokeStyle = `rgba(${r},${g},${b},${segAlpha * 0.25})`;
          ctx.lineWidth = 5;
          ctx.stroke();
          // Core
          ctx.strokeStyle = `rgba(${r},${g},${b},${segAlpha})`;
          ctx.lineWidth = 1.2;
          ctx.stroke();
        }

        // Arc head glow
        const head = bez(t, pf.x, pf.y, cpX, cpY, pt.x, pt.y);
        const headGrad = ctx.createRadialGradient(head.x, head.y, 0, head.x, head.y, 10);
        headGrad.addColorStop(0, `rgba(${r},${g},${b},${fadeAlpha})`);
        headGrad.addColorStop(0.4, `rgba(${r},${g},${b},${fadeAlpha * 0.4})`);
        headGrad.addColorStop(1, `rgba(${r},${g},${b},0)`);
        ctx.beginPath();
        ctx.arc(head.x, head.y, 10, 0, Math.PI * 2);
        ctx.fillStyle = headGrad;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(head.x, head.y, 2, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255,255,255,${fadeAlpha})`;
        ctx.fill();
      }

      // 5. City nodes
      const time = Date.now() * 0.001;
      for (const city of CITIES) {
        const p = project(city.lat, city.lng, R);
        const depthFade = Math.max(0, (p.z + R * 0.3) / (R * 1.3));
        if (depthFade <= 0) continue;

        const pulse = Math.sin(time * 2 + city.lat + city.lng) * 0.3 + 0.7;

        // Outer halo
        const halo = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, 9);
        halo.addColorStop(0,   `rgba(34,211,238,${0.35 * depthFade * pulse})`);
        halo.addColorStop(0.5, `rgba(34,211,238,${0.1 * depthFade})`);
        halo.addColorStop(1,   'rgba(34,211,238,0)');
        ctx.beginPath();
        ctx.arc(p.x, p.y, 9, 0, Math.PI * 2);
        ctx.fillStyle = halo;
        ctx.fill();

        // Core dot
        ctx.beginPath();
        ctx.arc(p.x, p.y, 2, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(34,211,238,${0.9 * depthFade})`;
        ctx.fill();
      }

      this.rafId = requestAnimationFrame(draw);
    };

    draw();
  }

  private generateStars(W: number, H: number) {
    this.stars = Array.from({ length: 120 }, () => ({
      x: Math.random() * W,
      y: Math.random() * H,
      r: Math.random() * 0.8 + 0.2,
      opacity: Math.random() * 0.5 + 0.1,
    }));
  }

  private randomArc(): Arc {
    const from = Math.floor(Math.random() * CITIES.length);
    let to = Math.floor(Math.random() * CITIES.length);
    while (to === from) to = Math.floor(Math.random() * CITIES.length);

    // Weighted type selection
    const roll = Math.random() * 10;
    const type = roll < 5 ? 0 : roll < 8 ? 1 : 2;

    return {
      from,
      to,
      progress: Math.random() * 0.3, // stagger starts
      speed: 0.0018 + Math.random() * 0.0022,
      type,
    };
  }
}
