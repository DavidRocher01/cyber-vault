import { Component, ElementRef, ViewChild, AfterViewInit, OnDestroy, NgZone } from '@angular/core';

const DEG = Math.PI / 180;
const TILT = 23.5 * DEG; // Earth's axial tilt

// 33 major cities — attack nodes
const CITIES = [
  { lat: 48.85, lng:   2.35 }, // Paris
  { lat: 40.71, lng: -74.00 }, // New York
  { lat: 35.68, lng: 139.69 }, // Tokyo
  { lat: 51.51, lng:  -0.12 }, // London
  { lat: 39.91, lng: 116.39 }, // Beijing
  { lat:-33.86, lng: 151.20 }, // Sydney
  { lat: 55.75, lng:  37.61 }, // Moscow
  { lat:-23.54, lng: -46.63 }, // São Paulo
  { lat: 25.20, lng:  55.27 }, // Dubai
  { lat:  1.35, lng: 103.82 }, // Singapore
  { lat: 37.77, lng:-122.41 }, // San Francisco
  { lat: 19.07, lng:  72.87 }, // Mumbai
  { lat:-26.20, lng:  28.04 }, // Johannesburg
  { lat: 41.00, lng:  28.95 }, // Istanbul
  { lat: 52.52, lng:  13.40 }, // Berlin
  { lat: 43.65, lng: -79.38 }, // Toronto
  { lat: 37.56, lng: 126.97 }, // Seoul
  { lat: 19.43, lng: -99.13 }, // Mexico City
  { lat: 30.04, lng:  31.24 }, // Cairo
  { lat: 25.03, lng: 121.56 }, // Taipei
  { lat: 52.37, lng:   4.89 }, // Amsterdam
  { lat: 59.33, lng:  18.07 }, // Stockholm
  { lat: 41.87, lng: -87.62 }, // Chicago
  { lat:  6.45, lng:   3.40 }, // Lagos
  { lat: -6.21, lng: 106.84 }, // Jakarta
  { lat:-34.60, lng: -58.38 }, // Buenos Aires
  { lat: 35.69, lng:  51.42 }, // Tehran
  { lat: 24.86, lng:  67.01 }, // Karachi
  { lat: 13.75, lng: 100.52 }, // Bangkok
  { lat: -1.29, lng:  36.82 }, // Nairobi
  { lat: 22.54, lng: 114.06 }, // Hong Kong
  { lat: 48.14, lng:  17.11 }, // Bratislava
  { lat: 45.42, lng: -75.69 }, // Ottawa
];

// Simplified land mask — bounding boxes per region
// Each entry: [minLat, maxLat, minLng, maxLng]
const LAND_BOXES: [number, number, number, number][] = [
  // North America
  [ 25, 72, -140, -55], [ 55, 72, -170, -140],
  [  7, 25,  -92, -77], [ 59, 84,  -55,  -18],
  // South America
  [-56, 12,  -82, -34],
  // Europe
  [ 36, 72,  -10,  32], [ 45, 72,   32,  60],
  [ 57, 72,    4,  32],
  // Africa
  [ 15, 38,  -18,  52], [-35, 15,  -18,  42],
  [-26,-12,   43,  51],
  // Middle East / Central Asia
  [ 12, 30,   43,  60], [ 25, 50,   25,  70],
  // Asia
  [ 50, 75,   60, 140], [ 20, 55,  100, 145],
  [  8, 35,   65,  92], [  5, 28,   97, 110],
  [  5, 20,  117, 127],
  // SE Asia islands
  [-10,  8,   95, 141],
  // Australia / NZ
  [-40,-10,  114, 154], [-47,-34,  166, 178],
  // Antarctica
  [-90,-68, -180, 180],
];

function isLand(lat: number, lng: number): boolean {
  let l = lng;
  if (l > 180) l -= 360;
  return LAND_BOXES.some(([la, lb, la2, lb2]) => lat >= la && lat <= lb && l >= la2 && l <= lb2);
}

// Pre-generate land dot grid at startup
const LAND_DOTS: { lat: number; lng: number }[] = [];
for (let lat = -85; lat <= 85; lat += 2.5) {
  for (let lng = -180; lng <= 177; lng += 3) {
    if (isLand(lat, lng)) LAND_DOTS.push({ lat, lng });
  }
}

const ARC_COLORS: [number, number, number][] = [
  [239, 68, 68],   // red   — attacks
  [239, 68, 68],   // red
  [239, 68, 68],   // red (higher weight)
  [251,146, 60],   // orange — warnings
  [251,146, 60],   // orange
  [250,204, 21],   // yellow — probes
];

interface Arc {
  from: number; to: number;
  progress: number; speed: number;
  color: [number, number, number];
}

interface Impact {
  x: number; y: number;
  t: number;
  color: [number, number, number];
}

interface Star { x: number; y: number; r: number; a: number; }

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
  private attackCount = 8_000 + Math.floor(Math.random() * 4000);

  constructor(private ngZone: NgZone) {}

  ngAfterViewInit() {
    this.ngZone.runOutsideAngular(() => this.boot());
  }

  ngOnDestroy() { cancelAnimationFrame(this.rafId); }

  private boot() {
    const canvas = this.canvasRef.nativeElement;
    const ctx = canvas.getContext('2d')!;
    let W = 0, H = 0;

    const resize = () => {
      const r = canvas.getBoundingClientRect();
      W = r.width; H = r.height;
      canvas.width  = W * devicePixelRatio;
      canvas.height = H * devicePixelRatio;
      ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
      this.stars = Array.from({ length: 150 }, () => ({
        x: Math.random() * W, y: Math.random() * H,
        r: Math.random() * 0.9 + 0.2, a: Math.random() * 0.45 + 0.08,
      }));
    };
    resize();
    window.addEventListener('resize', resize);

    const arcs: Arc[] = Array.from({ length: 22 }, () => this.mkArc());
    const impacts: Impact[] = [];

    // ── Projection with Earth tilt ────────────────────────────────────────
    const proj = (latD: number, lngD: number, R: number, cx: number, cy: number) => {
      const lat = latD * DEG, lng = (lngD + this.rotation) * DEG;
      const px = Math.cos(lat) * Math.sin(lng);
      const py = -Math.sin(lat);
      const pz = Math.cos(lat) * Math.cos(lng);
      // Tilt around X axis
      const ty = py * Math.cos(TILT) - pz * Math.sin(TILT);
      const tz = py * Math.sin(TILT) + pz * Math.cos(TILT);
      return { x: cx + R * px, y: cy + R * ty, z: tz * R };
    };

    const bez = (t: number, ax: number, ay: number, bx: number, by: number, cx2: number, cy2: number) => ({
      x: (1-t)**2*ax + 2*(1-t)*t*bx + t**2*cx2,
      y: (1-t)**2*ay + 2*(1-t)*t*by + t**2*cy2,
    });

    // ── Main draw loop ────────────────────────────────────────────────────
    let lastCounterTick = 0;

    const draw = (ts: number) => {
      this.rafId = requestAnimationFrame(draw);
      const R  = Math.min(W, H) * 0.41;
      const cx = W / 2, cy = H / 2;
      ctx.clearRect(0, 0, W, H);
      this.rotation += 0.045;

      // Randomly increment counter
      if (ts - lastCounterTick > 800 + Math.random() * 600) {
        this.attackCount += Math.floor(Math.random() * 3) + 1;
        lastCounterTick = ts;
      }

      // ── Stars ──────────────────────────────────────────────────────────
      for (const s of this.stars) {
        ctx.globalAlpha = s.a;
        ctx.fillStyle = '#fff';
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;

      // ── Globe base ─────────────────────────────────────────────────────
      const base = ctx.createRadialGradient(cx, cy*0.92, 0, cx, cy, R);
      base.addColorStop(0,   'rgba(10, 25, 47, 0.92)');
      base.addColorStop(0.7, 'rgba(6, 18, 36, 0.96)');
      base.addColorStop(1,   'rgba(2, 8, 20, 0.99)');
      ctx.beginPath();
      ctx.arc(cx, cy, R, 0, Math.PI * 2);
      ctx.fillStyle = base;
      ctx.fill();

      // ── Atmospheric glow ───────────────────────────────────────────────
      const atm = ctx.createRadialGradient(cx, cy, R * 0.87, cx, cy, R * 1.28);
      atm.addColorStop(0,   'rgba(34,211,238,0.18)');
      atm.addColorStop(0.35,'rgba(34,211,238,0.07)');
      atm.addColorStop(0.7, 'rgba(56,189,248,0.02)');
      atm.addColorStop(1,   'rgba(34,211,238,0)');
      ctx.beginPath();
      ctx.arc(cx, cy, R * 1.28, 0, Math.PI * 2);
      ctx.fillStyle = atm;
      ctx.fill();

      // ── Specular highlight (upper-left) ───────────────────────────────
      const spec = ctx.createRadialGradient(cx - R*0.3, cy - R*0.35, 0, cx, cy, R);
      spec.addColorStop(0,   'rgba(147,210,255,0.07)');
      spec.addColorStop(0.4, 'rgba(147,210,255,0.02)');
      spec.addColorStop(1,   'rgba(147,210,255,0)');
      ctx.beginPath();
      ctx.arc(cx, cy, R, 0, Math.PI * 2);
      ctx.fillStyle = spec;
      ctx.fill();

      // ── Land dots ─────────────────────────────────────────────────────
      for (const d of LAND_DOTS) {
        const p = proj(d.lat, d.lng, R, cx, cy);
        if (p.z < 0) continue;
        const depth = Math.max(0, p.z / R);
        ctx.globalAlpha = depth * 0.28;
        ctx.fillStyle = '#4ade80'; // green tint for land
        ctx.beginPath();
        ctx.arc(p.x, p.y, 0.9, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;

      // ── Grid lines ────────────────────────────────────────────────────
      const drawLine = (pts: {x:number,y:number,z:number}[], w: number, alpha: number, color = '34,211,238') => {
        ctx.lineWidth = w;
        let first = true;
        ctx.beginPath();
        for (const p of pts) {
          if (p.z < -R * 0.05) { first = true; continue; }
          const a = Math.max(0, p.z / R) * alpha;
          if (first) { ctx.moveTo(p.x, p.y); first = false; }
          else ctx.lineTo(p.x, p.y);
        }
        ctx.strokeStyle = `rgba(${color},${alpha * 0.6})`;
        ctx.stroke();
      };

      for (let lat = -80; lat <= 80; lat += 20) {
        const pts = [];
        for (let lng = 0; lng <= 360; lng += 2) pts.push(proj(lat, lng, R, cx, cy));
        drawLine(pts, lat === 0 ? 0.7 : 0.35, lat === 0 ? 0.3 : 0.1);
      }
      for (let lng = 0; lng < 360; lng += 20) {
        const pts = [];
        for (let lat = -90; lat <= 90; lat += 2) pts.push(proj(lat, lng, R, cx, cy));
        drawLine(pts, 0.35, 0.08);
      }

      // ── Attack arcs ───────────────────────────────────────────────────
      for (let i = arcs.length - 1; i >= 0; i--) {
        const arc = arcs[i];
        arc.progress += arc.speed;

        if (arc.progress > 1.08) { arcs[i] = this.mkArc(); continue; }

        const t   = Math.min(arc.progress, 1);
        const pf  = proj(CITIES[arc.from].lat, CITIES[arc.from].lng, R, cx, cy);
        const pt  = proj(CITIES[arc.to].lat,   CITIES[arc.to].lng,   R, cx, cy);

        if (pf.z < -R * 0.15 || pt.z < -R * 0.15) continue;

        // Control point — high lift for dramatic arc
        const midX = (pf.x + pt.x) / 2;
        const midY = (pf.y + pt.y) / 2;
        const dist = Math.hypot(pt.x - pf.x, pt.y - pf.y);
        const lift = Math.max(dist * 0.55, R * 0.18);
        const cpX  = midX, cpY = midY - lift;

        const [r, g, b] = arc.color;
        const alpha = Math.sin(Math.min(t, 0.92) * Math.PI) * 0.9;

        // Trail — segment-by-segment with gradient opacity
        const STEPS   = 80;
        const headIdx = Math.floor(STEPS * t);
        const tailLen = 28;
        const tailStart = Math.max(0, headIdx - tailLen);

        for (let s = tailStart; s < headIdx; s++) {
          const ta = s / STEPS, tb = (s + 1) / STEPS;
          const pa = bez(ta, pf.x, pf.y, cpX, cpY, pt.x, pt.y);
          const pb = bez(tb, pf.x, pf.y, cpX, cpY, pt.x, pt.y);
          const ratio = (s - tailStart) / (headIdx - tailStart);

          // Outer bloom
          ctx.beginPath(); ctx.moveTo(pa.x, pa.y); ctx.lineTo(pb.x, pb.y);
          ctx.strokeStyle = `rgba(${r},${g},${b},${ratio * alpha * 0.18})`;
          ctx.lineWidth = 9; ctx.stroke();

          // Mid glow
          ctx.strokeStyle = `rgba(${r},${g},${b},${ratio * alpha * 0.5})`;
          ctx.lineWidth = 3; ctx.stroke();

          // Core
          ctx.strokeStyle = `rgba(255,255,255,${ratio * alpha * 0.7})`;
          ctx.lineWidth = 0.8; ctx.stroke();
        }

        // Arc head glow
        const head = bez(t, pf.x, pf.y, cpX, cpY, pt.x, pt.y);
        const hg = ctx.createRadialGradient(head.x, head.y, 0, head.x, head.y, 14);
        hg.addColorStop(0,   `rgba(${r},${g},${b},${alpha})`);
        hg.addColorStop(0.4, `rgba(${r},${g},${b},${alpha * 0.5})`);
        hg.addColorStop(1,   `rgba(${r},${g},${b},0)`);
        ctx.beginPath(); ctx.arc(head.x, head.y, 14, 0, Math.PI * 2);
        ctx.fillStyle = hg; ctx.fill();

        ctx.beginPath(); ctx.arc(head.x, head.y, 2.2, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255,255,255,${alpha * 0.95})`; ctx.fill();

        // Trigger impact when arc arrives
        if (arc.progress >= 1 && arc.progress - arc.speed < 1) {
          impacts.push({ x: pt.x, y: pt.y, t: 0, color: arc.color });
        }
      }

      // ── Impact ripples ─────────────────────────────────────────────────
      for (let i = impacts.length - 1; i >= 0; i--) {
        const imp = impacts[i];
        imp.t += 0.025;
        if (imp.t > 1) { impacts.splice(i, 1); continue; }

        const [r, g, b] = imp.color;
        const eased = 1 - (1 - imp.t) ** 2;

        for (let ring = 0; ring < 3; ring++) {
          const rt    = Math.max(0, imp.t - ring * 0.2);
          const rEase = 1 - (1 - rt) ** 2;
          const radius = rEase * 28;
          const ringA  = (1 - rEase) * 0.8;
          ctx.beginPath();
          ctx.arc(imp.x, imp.y, radius, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(${r},${g},${b},${ringA})`;
          ctx.lineWidth = 1.5;
          ctx.stroke();
        }

        const flash = ctx.createRadialGradient(imp.x, imp.y, 0, imp.x, imp.y, 10);
        flash.addColorStop(0,  `rgba(${r},${g},${b},${(1-eased)*0.6})`);
        flash.addColorStop(1,  `rgba(${r},${g},${b},0)`);
        ctx.beginPath(); ctx.arc(imp.x, imp.y, 10, 0, Math.PI * 2);
        ctx.fillStyle = flash; ctx.fill();
      }

      // ── City nodes ─────────────────────────────────────────────────────
      const time = Date.now() * 0.001;
      for (const city of CITIES) {
        const p = proj(city.lat, city.lng, R, cx, cy);
        const depth = Math.max(0, (p.z + R * 0.1) / (R * 1.1));
        if (depth <= 0) continue;

        const pulse  = Math.sin(time * 1.8 + city.lat + city.lng) * 0.28 + 0.72;
        const haloSz = 11 * pulse;

        // Double halo
        const h1 = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, haloSz);
        h1.addColorStop(0, `rgba(34,211,238,${0.55*depth*pulse})`);
        h1.addColorStop(1, 'rgba(34,211,238,0)');
        ctx.beginPath(); ctx.arc(p.x, p.y, haloSz, 0, Math.PI * 2);
        ctx.fillStyle = h1; ctx.fill();

        // Core dot
        ctx.beginPath(); ctx.arc(p.x, p.y, 1.8, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255,255,255,${depth*0.95})`; ctx.fill();
      }

      // ── Stats overlay (bottom-right corner) ───────────────────────────
      const count = this.attackCount.toLocaleString('fr-FR');
      ctx.font = 'bold 11px monospace';
      ctx.textAlign = 'right';
      ctx.fillStyle = 'rgba(239,68,68,0.85)';
      ctx.fillText(`● ${count} ATTAQUES DÉTECTÉES`, W - 18, H - 30);

      ctx.font = '10px monospace';
      ctx.fillStyle = 'rgba(251,146,60,0.7)';
      ctx.fillText(`● ${Math.floor(this.attackCount * 0.62).toLocaleString('fr-FR')} TENTATIVES RÉSEAU`, W - 18, H - 16);
    };

    requestAnimationFrame(draw);
  }

  private mkArc(): Arc {
    const from = Math.floor(Math.random() * CITIES.length);
    let to = Math.floor(Math.random() * CITIES.length);
    while (to === from) to = Math.floor(Math.random() * CITIES.length);
    const color = ARC_COLORS[Math.floor(Math.random() * ARC_COLORS.length)];
    return { from, to, progress: Math.random() * 0.4, speed: 0.0014 + Math.random() * 0.0018, color };
  }
}
