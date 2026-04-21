import { Component, Input, OnDestroy, OnInit, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';

interface LogLine { lvl: 'INF' | 'WRN' | 'ERR'; msg: string; }

const LOG_POOL: LogLine[] = [
  { lvl: 'INF', msg: 'TLS 1.3 handshake complete with edge-07.fr3 — cipher TLS_AES_256_GCM_SHA384' },
  { lvl: 'INF', msg: 'negotiating X25519 key exchange — peer fingerprint verified' },
  { lvl: 'INF', msg: 'certificate chain validated (depth=3) — OCSP stapling ok' },
  { lvl: 'INF', msg: 'pulling signature db rev 2026.04.19.1142 — 41832 rules' },
  { lvl: 'INF', msg: 'loading YARA ruleset /etc/sec/rules/apt.yar (1184 rules)' },
  { lvl: 'INF', msg: 'connecting to vault via mTLS — spiffe://cluster/loader' },
  { lvl: 'INF', msg: 'sha256 ok  loader.bin  9f3c8a…b71e' },
  { lvl: 'INF', msg: 'sha256 ok  kernel.img  a21fe7…0cd4' },
  { lvl: 'INF', msg: 'ed25519 signature verified — issuer: ops-ca/2024' },
  { lvl: 'INF', msg: 'entropy pool seeded from 3 sources — 512 bits' },
  { lvl: 'INF', msg: 'spawned sandbox pid=48213 uid=65534 caps=cap_net_bind' },
  { lvl: 'INF', msg: 'establishing WireGuard tunnel wg0 — 10.64.0.1:51820' },
  { lvl: 'INF', msg: 'DNS-over-HTTPS resolver 1.1.1.1 — rtt 8.3ms' },
  { lvl: 'WRN', msg: 'deprecated TLS extension 0x0017 observed on legacy client' },
  { lvl: 'INF', msg: 'applying seccomp filter — 214 syscalls allowed' },
  { lvl: 'INF', msg: 'mounting overlayfs /containers/sec/rootfs ro' },
  { lvl: 'INF', msg: 'starting audit subsystem — ring buffer 64 MiB' },
  { lvl: 'INF', msg: 'AES-256-GCM session key derived via HKDF-SHA384' },
  { lvl: 'INF', msg: 'BGP session up with AS64512 — 862k prefixes received' },
  { lvl: 'WRN', msg: 'clock drift 11ms — resyncing via NTS pool' },
  { lvl: 'INF', msg: 'WAF engine loaded — OWASP CRS 4.2.0' },
  { lvl: 'INF', msg: 'memory-scan pass 1/3 — 4.2 GiB hashed in 312ms' },
];

const CHECK_ITEMS = [
  'secure boot — tpm pcr[0..7] verified',
  'kernel module signatures — 212/212 ok',
  'disk encryption — luks2 unlocked',
  'network policy — egress rules applied',
  'identity — oidc token refreshed',
  'vault seal — 3-of-5 shares unsealed',
  'sandbox — seccomp profile attached',
  'telemetry — otlp endpoint reachable',
  'waf — owasp crs loaded (4.2.0)',
  'ids signatures — 41832 rules synced',
  'threat intel — feed miso.04.2026 ingested',
  'audit log — append-only stream open',
];

function mulberry32(seed: number) {
  return () => {
    seed = (seed + 0x6D2B79F5) | 0;
    let t = seed;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function hexBlock(len: number, seed: number) {
  const r = mulberry32(seed);
  const chars = '0123456789abcdef';
  let s = '';
  for (let i = 0; i < len; i++) s += chars[Math.floor(r() * 16)];
  return s;
}
function pad(n: number, w = 2) { return String(n).padStart(w, '0'); }

@Component({
  selector: 'app-cyber-loader',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="stage crt" *ngIf="visible" role="status" aria-label="Chargement sécurisé">
      <div class="screen">
        <div class="topbar">
          <div><span class="dot"></span>{{ product }} · secure-boot v4.2.1</div>
          <div class="topbar-right">
            <span>node: edge-07.fr3</span>
            <span>sess: 0x{{ sessionId }}</span>
            <span>{{ tStr }} UTC</span>
          </div>
        </div>

        <div class="main">
          <div class="logs">
            <div class="section-title">── event stream ────────────────────────────────</div>
            <div class="log-list">
              <div *ngFor="let l of rollingLogs; let i = index"
                   class="log-line"
                   [style.opacity]="0.35 + (i / rollingLogs.length) * 0.65">
                <span class="log-ts">{{ logTs(i) }}</span>
                <span class="log-lvl" [class.wrn]="l.lvl === 'WRN'" [class.err]="l.lvl === 'ERR'">[{{ l.lvl }}]</span>
                <span>{{ l.msg }}</span>
              </div>
              <div class="log-line log-waiting phos-glow">
                <span class="log-ts">{{ tStr }}</span>
                <span class="log-lvl">[---]</span>
                <span>waiting<span class="caret"></span></span>
              </div>
            </div>
            <div class="fade-top"></div>
          </div>

          <div class="checks">
            <div class="section-title">── integrity checks ────────────────────</div>
            <div class="check-list">
              <div *ngFor="let c of CHECKS; let i = index"
                   class="check-line"
                   [ngClass]="checkState(i)">
                <span class="mark" [class.phos-glow]="checkState(i) === 'ok'">
                  {{ checkMark(i) }}
                </span>
                <span class="check-label">{{ c }}</span>
                <span class="check-time">{{ checkTime(i) }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="footer">
          <div class="footer-head">
            <span class="phos-glow pct">[{{ pctStr }}%] bootstrapping secure runtime</span>
            <span class="eta">loading…</span>
          </div>
          <div class="bar"><div class="bar-fill" [style.width.%]="loopPct * 100"></div></div>
          <div class="hash">sha256: {{ hash }}</div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    :host {
      --bg-0: #030604;
      --bg-1: #060b07;
      --line: rgba(120, 255, 160, 0.12);
      --line-strong: rgba(120, 255, 160, 0.28);
      --phosphor: oklch(0.88 0.22 145);
      --phosphor-dim: oklch(0.68 0.18 145);
      --phosphor-muted: oklch(0.48 0.12 145);
      --phosphor-deep: oklch(0.28 0.08 145);
      --amber: oklch(0.82 0.16 75);
      --red: oklch(0.68 0.22 28);
      --mono: "JetBrains Mono", "IBM Plex Mono", ui-monospace, Menlo, monospace;
    }
    .stage {
      position: fixed; inset: 0;
      display: flex; align-items: center; justify-content: center;
      background: var(--bg-0);
      color: var(--phosphor);
      font-family: var(--mono);
      font-size: 13px;
      z-index: 9999;
    }
    .screen {
      position: relative;
      width: min(1400px, 96vw);
      height: min(860px, 92vh);
      background: var(--bg-0);
      border: 1px solid var(--line);
      display: flex; flex-direction: column;
      overflow: hidden;
    }
    .crt::after {
      content: ""; position: absolute; inset: 0;
      background: repeating-linear-gradient(to bottom,
        rgba(0,0,0,0) 0, rgba(0,0,0,0) 2px,
        rgba(0,0,0,0.18) 3px, rgba(0,0,0,0) 4px);
      pointer-events: none; z-index: 30; mix-blend-mode: multiply;
    }
    .crt::before {
      content: ""; position: absolute; inset: 0;
      background: radial-gradient(ellipse at center, rgba(0,0,0,0) 50%, rgba(0,0,0,0.55) 100%);
      pointer-events: none; z-index: 31;
    }
    .phos-glow {
      text-shadow: 0 0 6px currentColor, 0 0 14px oklch(0.8 0.2 145 / 0.45);
    }
    .topbar {
      display: flex; justify-content: space-between; align-items: center;
      padding: 10px 18px;
      border-bottom: 1px solid var(--line);
      font-size: 11px; color: var(--phosphor-dim);
      letter-spacing: 0.12em; text-transform: uppercase;
      background: linear-gradient(to bottom, rgba(120,255,160,0.04), transparent);
    }
    .topbar-right { display: flex; gap: 22px; }
    .dot {
      width: 8px; height: 8px; border-radius: 50%;
      background: var(--phosphor); display: inline-block; margin-right: 8px;
      box-shadow: 0 0 8px var(--phosphor);
      animation: blink 1.2s infinite;
    }
    @keyframes blink { 50% { opacity: 0.2; } }
    .caret {
      display: inline-block; width: 0.55em; height: 1em;
      background: var(--phosphor); vertical-align: -0.12em;
      margin-left: 2px;
      animation: caret 1.05s steps(1) infinite;
      box-shadow: 0 0 6px var(--phosphor);
    }
    @keyframes caret { 50% { opacity: 0; } }
    .main {
      flex: 1; display: grid;
      grid-template-columns: 1.4fr 1fr;
      gap: 1px; background: var(--line);
      min-height: 0;
    }
    .logs, .checks { padding: 18px 22px; position: relative; overflow: hidden; }
    .logs { background: var(--bg-0); }
    .checks { background: var(--bg-1); }
    .section-title {
      font-size: 10px; letter-spacing: 0.16em; text-transform: uppercase;
      color: var(--phosphor-muted); margin-bottom: 14px;
    }
    .log-line {
      font-size: 12px; line-height: 1.65; color: var(--phosphor-dim);
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .log-ts { color: var(--phosphor-deep); }
    .log-lvl { margin: 0 10px; font-weight: 500; }
    .log-lvl.wrn { color: var(--amber); }
    .log-lvl.err { color: var(--red); }
    .log-waiting { color: var(--phosphor); opacity: 1 !important; }
    .fade-top {
      position: absolute; top: 44px; left: 0; right: 0; height: 40px;
      background: linear-gradient(to bottom, var(--bg-0), transparent);
      pointer-events: none;
    }
    .check-list { font-size: 12px; line-height: 2.0; }
    .check-line { display: flex; gap: 14px; }
    .check-line.pending { opacity: 0.4; color: var(--phosphor-deep); }
    .check-line.ok { color: var(--phosphor); }
    .check-line.run { color: var(--amber); }
    .mark { width: 14px; text-align: center; }
    .check-label { flex: 1; }
    .check-time { font-size: 10px; color: var(--phosphor-muted); }
    .footer {
      padding: 18px 22px;
      border-top: 1px solid var(--line);
      background: var(--bg-1);
    }
    .footer-head {
      display: flex; justify-content: space-between;
      margin-bottom: 10px; font-size: 11px;
    }
    .pct { color: var(--phosphor); }
    .eta { color: var(--phosphor-muted); }
    .bar {
      height: 10px;
      background: rgba(120,255,160,0.06);
      border: 1px solid var(--line-strong);
      position: relative; overflow: hidden;
    }
    .bar-fill {
      position: absolute; inset: 0 auto 0 0;
      background: var(--phosphor-dim);
      box-shadow: 0 0 10px var(--phosphor);
      transition: width 0.1s linear;
    }
    .hash {
      margin-top: 10px; font-size: 10px;
      color: var(--phosphor-muted); letter-spacing: 0.08em;
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
  `],
})
export class CyberLoaderComponent implements OnInit, OnDestroy {
  @Input() visible = true;
  @Input() product = 'CYBERSCAN';
  @Input() loopSec = 12;

  readonly CHECKS = CHECK_ITEMS;

  rollingLogs: LogLine[] = [];
  tick = 0;
  loopPct = 0;
  private rafId = 0;
  private logTimer: any;
  private startTime = performance.now();
  private logIdx = 0;

  constructor(private cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    const frame = (now: number) => {
      const elapsed = ((now - this.startTime) / 1000) % this.loopSec;
      this.loopPct = elapsed / this.loopSec;
      this.tick = Math.floor((now - this.startTime) / 50);
      this.cdr.markForCheck();
      this.rafId = requestAnimationFrame(frame);
    };
    this.rafId = requestAnimationFrame(frame);

    this.logTimer = setInterval(() => {
      this.rollingLogs = [...this.rollingLogs, LOG_POOL[this.logIdx % LOG_POOL.length]].slice(-14);
      this.logIdx++;
      this.cdr.markForCheck();
    }, 220);
  }

  ngOnDestroy(): void {
    cancelAnimationFrame(this.rafId);
    clearInterval(this.logTimer);
  }

  get tStr(): string {
    const d = new Date(Date.UTC(2026, 3, 20, 14, 32, 0) + this.tick * 50);
    return `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}.${pad(d.getUTCMilliseconds() % 1000, 3)}`;
  }
  get sessionId(): string { return hexBlock(12, Math.floor(this.tick / 40) + 1); }
  get hash(): string { return hexBlock(64, Math.floor(this.tick / 4) + 1); }
  get pctStr(): string { return String(Math.floor(this.loopPct * 100)).padStart(3, '0'); }

  logTs(i: number): string {
    const offset = (this.rollingLogs.length - i) * 0.22;
    const d = new Date(Date.UTC(2026, 3, 20, 14, 32, 0) + (this.tick * 50) - offset * 1000);
    return `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}.${pad(d.getUTCMilliseconds() % 1000, 3)}`;
  }

  checkState(i: number): 'ok' | 'run' | 'pending' {
    const visible = Math.floor(this.loopPct * (CHECK_ITEMS.length + 2));
    if (i < visible) return 'ok';
    if (i === visible) return 'run';
    return 'pending';
  }
  checkMark(i: number): string {
    const s = this.checkState(i);
    return s === 'ok' ? '✓' : s === 'run' ? '›' : '·';
  }
  checkTime(i: number): string {
    const s = this.checkState(i);
    return s === 'ok' ? `${12 + i * 3}ms` : s === 'run' ? '…' : '';
  }
}
