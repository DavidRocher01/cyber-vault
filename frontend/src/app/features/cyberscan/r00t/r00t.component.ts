import { Component, ElementRef, ViewChild, AfterViewInit, ChangeDetectionStrategy, ChangeDetectorRef, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';

interface Line { type: 'cmd' | 'out' | 'err'; text: string; }

const BANNER = [
  '  ██████╗ ██████╗  ██████╗ ████████╗',
  '  ██╔══██╗╚════██╗██╔═████╗╚══██╔══╝',
  '  ██████╔╝ █████╔╝██║██╔██║   ██║   ',
  '  ██╔══██╗██╔═══╝ ████╔╝██║   ██║   ',
  '  ██║  ██║███████╗╚██████╔╝   ██║   ',
  '  ╚═╝  ╚═╝╚══════╝ ╚═════╝    ╚═╝   ',
  '',
  '  CyberScan Remote Access Terminal v4.2.1',
  '  ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄',
  '  Connexion établie depuis 10.64.0.1 — spiffe://cluster/loader',
  '  Type "help" for available commands.',
  '',
];

const FILES = ['audit.log', 'config.yml', 'scan_results.json', 'vuln_db.sqlite', '.secrets', 'kernel.img'];
const NMAP_LINES = [
  'Starting Nmap 7.95 ( https://nmap.org )',
  'Scanning cyberscanapp.com (10.64.0.1) ...',
  'PORT     STATE SERVICE  VERSION',
  '22/tcp   open  ssh      OpenSSH 9.4 (protocol 2.0)',
  '80/tcp   open  http     nginx 1.25.3',
  '443/tcp  open  https    nginx 1.25.3',
  '8080/tcp filtered http',
  '',
  'Nmap done: 1 IP address (1 host up) scanned in 3.42 seconds',
];

@Component({
  selector: 'app-r00t',
  standalone: true,
  imports: [CommonModule, FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="terminal-root" (click)="focusInput()">
      <div class="terminal-topbar">
        <div class="dots">
          <span class="dot red" (click)="exit(); $event.stopPropagation()" title="Fermer"></span>
          <span class="dot yellow"></span>
          <span class="dot green"></span>
        </div>
        <span class="title">r00t&#64;cyberscan-edge-07:~$</span>
      </div>

      <div class="terminal-body" #body>
        <div *ngFor="let l of lines" [ngClass]="'line line-' + l.type">{{ l.text }}</div>
        <div class="input-row">
          <span class="prompt">{{ prompt }}</span>
          <input #input
                 [(ngModel)]="currentInput"
                 (keydown.enter)="submit()"
                 (keydown.tab)="$event.preventDefault(); autocomplete()"
                 (keydown.arrowup)="$event.preventDefault(); historyPrev()"
                 (keydown.arrowdown)="$event.preventDefault(); historyNext()"
                 autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false"
                 class="term-input" />
          <span class="caret"></span>
        </div>
      </div>
    </div>
  `,
  styles: [`
    :host {
      --bg: #050a05;
      --line: rgba(0,255,70,0.12);
      --green: #00e645;
      --green-dim: #006a20;
      --green-muted: #004015;
      --amber: #f5a623;
      --red: #ff4444;
      --mono: 'JetBrains Mono', 'IBM Plex Mono', ui-monospace, Menlo, monospace;
      display: block; height: 100dvh; background: var(--bg);
    }
    .terminal-root {
      display: flex; flex-direction: column; height: 100%;
      font-family: var(--mono); font-size: 13px;
      background: var(--bg); color: var(--green);
    }
    .terminal-topbar {
      display: flex; align-items: center; gap: 12px;
      padding: 10px 16px; background: #0a110a;
      border-bottom: 1px solid var(--line);
    }
    .dots { display: flex; gap: 6px; }
    .dot { width: 12px; height: 12px; border-radius: 50%; cursor: pointer; }
    .dot.red { background: #ff5f57; }
    .dot.yellow { background: #ffbd2e; }
    .dot.green { background: #28ca41; }
    .title { flex: 1; text-align: center; font-size: 11px; color: var(--green-dim); letter-spacing: 0.1em; }
    .terminal-body {
      flex: 1; overflow-y: auto; padding: 16px 20px;
      scrollbar-width: thin; scrollbar-color: var(--green-muted) transparent;
    }
    .line { line-height: 1.6; white-space: pre; }
    .line-cmd { color: var(--green); }
    .line-out { color: #b0ffcc; }
    .line-err { color: var(--red); }
    .input-row { display: flex; align-items: center; margin-top: 4px; }
    .prompt { color: var(--green); white-space: nowrap; }
    .term-input {
      flex: 1; background: transparent; border: none; outline: none;
      color: var(--green); font-family: var(--mono); font-size: 13px;
      caret-color: transparent; padding: 0 0 0 4px;
    }
    .caret {
      display: inline-block; width: 0.55em; height: 1em;
      background: var(--green); vertical-align: -0.12em;
      animation: blink 1.05s steps(1) infinite;
    }
    @keyframes blink { 50% { opacity: 0; } }
  `],
})
export class R00tComponent implements AfterViewInit {
  @ViewChild('input') inputRef!: ElementRef<HTMLInputElement>;
  @ViewChild('body') bodyRef!: ElementRef<HTMLDivElement>;

  private router = inject(Router);
  private cdr = inject(ChangeDetectorRef);

  prompt = 'r00t@cyberscan-edge-07:~$ ';
  currentInput = '';
  lines: Line[] = BANNER.map(t => ({ type: 'out' as const, text: t }));

  private history: string[] = [];
  private historyIdx = -1;

  ngAfterViewInit(): void {
    this.focusInput();
  }

  focusInput(): void {
    this.inputRef?.nativeElement.focus();
  }

  autocomplete(): void {
    const partial = this.currentInput.trim();
    const cmds = ['help', 'whoami', 'ls', 'cat', 'nmap', 'hack', 'clear', 'exit', 'uname', 'ps', 'date'];
    const match = cmds.find(c => c.startsWith(partial) && c !== partial);
    if (match) this.currentInput = match;
  }

  historyPrev(): void {
    if (this.history.length === 0) return;
    this.historyIdx = Math.min(this.historyIdx + 1, this.history.length - 1);
    this.currentInput = this.history[this.historyIdx];
  }

  historyNext(): void {
    if (this.historyIdx <= 0) { this.historyIdx = -1; this.currentInput = ''; return; }
    this.historyIdx--;
    this.currentInput = this.history[this.historyIdx];
  }

  submit(): void {
    const cmd = this.currentInput.trim();
    if (!cmd) return;
    this.history.unshift(cmd);
    this.historyIdx = -1;
    this.addLine('cmd', `${this.prompt}${cmd}`);
    this.currentInput = '';
    this.execute(cmd);
    this.cdr.markForCheck();
    setTimeout(() => this.scrollBottom(), 0);
  }

  private execute(raw: string): void {
    const [cmd, ...args] = raw.toLowerCase().split(/\s+/);
    switch (cmd) {
      case 'help':
        this.out([
          'Available commands:',
          '  help      — show this help',
          '  whoami    — display current user',
          '  ls        — list files',
          '  cat       — read a file',
          '  nmap      — port scanner',
          '  ps        — running processes',
          '  uname     — system info',
          '  date      — current time',
          '  hack      — initiate hack sequence',
          '  clear     — clear terminal',
          '  exit      — return to safety',
        ]);
        break;
      case 'whoami':
        this.out(['r00t']);
        break;
      case 'uname':
        this.out(['Linux cyberscan-edge-07 6.8.0-cyberscan #1 SMP PREEMPT_RT x86_64 GNU/Linux']);
        break;
      case 'date':
        this.out([new Date().toUTCString()]);
        break;
      case 'ps':
        this.out([
          'PID   TTY   STAT  COMMAND',
          '1     ?     Ss    /sbin/init',
          '48213 pts/0 S+    ./cyberscan-scanner --mode=full',
          '48214 pts/0 S     nginx -g daemon off',
          '48215 pts/0 S     uvicorn app.main:app --workers 4',
          '48216 pts/0 S     postgres -D /var/lib/postgresql/data',
          `${Math.floor(Math.random() * 9000 + 1000)} pts/1 S+    bash`,
        ]);
        break;
      case 'ls':
        this.out([FILES.join('   ')]);
        break;
      case 'cat':
        this.catFile(args[0]);
        break;
      case 'nmap':
        this.out(NMAP_LINES);
        break;
      case 'hack':
        this.hackSequence();
        break;
      case 'clear':
        this.lines = [];
        break;
      case 'exit':
        this.exit();
        break;
      default:
        this.err([`bash: ${cmd}: command not found`]);
    }
  }

  private out(lines: string[]): void { lines.forEach(t => this.addLine('out', t)); }
  private err(lines: string[]): void { lines.forEach(t => this.addLine('err', t)); }
  private addLine(type: Line['type'], text: string): void { this.lines = [...this.lines, { type, text }]; }

  private catFile(name: string): void {
    if (!name) { this.err(['cat: missing operand']); return; }
    if (name === '.secrets') {
      this.err([
        'cat: .secrets: Permission denied',
        'Hint: Tu croyais vraiment que ce serait aussi facile ? 😏',
      ]);
      return;
    }
    if (!FILES.includes(name)) { this.err([`cat: ${name}: No such file or directory`]); return; }
    if (name === 'audit.log') {
      this.out([
        '[2026-04-20 14:31:07] INFO  scan started — target: example.com',
        '[2026-04-20 14:31:09] INFO  SSL/TLS: TLS 1.3, cipher TLS_AES_256_GCM_SHA384',
        '[2026-04-20 14:31:11] WARN  Missing header: Content-Security-Policy',
        '[2026-04-20 14:31:12] INFO  Ports: 80/open, 443/open, others filtered',
        '[2026-04-20 14:31:15] INFO  scan complete — score: 82/100',
      ]);
      return;
    }
    if (name === 'config.yml') {
      this.out([
        'scanner:',
        '  timeout: 30s',
        '  workers: 4',
        '  rules: /etc/sec/rules/owasp.yar',
        'vault:',
        '  address: vault.internal:8200',
        '  auth: kubernetes',
      ]);
      return;
    }
    this.out([`[binary data — ${Math.floor(Math.random() * 512 + 64)}KB]`]);
  }

  private hackSequence(): void {
    const steps = [
      '> Initializing exploit payload…',
      '> Scanning for open vectors…',
      '> CVE-2026-0001 — not vulnerable ✓',
      '> CVE-2025-4421 — not vulnerable ✓',
      '> SQL injection probes — sanitized ✓',
      '> XSS reflection — CSP blocks it ✓',
      '> SSRF bypass attempt — filtered ✓',
      '> Auth bypass — TOTP required ✓',
      '',
      '> ██████████████████████████ 100%',
      '',
      '> RESULT: System is hardened. No breach possible.',
      '> CyberScan does its job well 😉',
    ];
    let i = 0;
    const interval = setInterval(() => {
      this.addLine('out', steps[i]);
      this.cdr.markForCheck();
      setTimeout(() => this.scrollBottom(), 0);
      i++;
      if (i >= steps.length) clearInterval(interval);
    }, 220);
  }

  exit(): void {
    this.router.navigate(['/cyberscan']);
  }

  private scrollBottom(): void {
    const el = this.bodyRef?.nativeElement;
    if (el) el.scrollTop = el.scrollHeight;
  }
}
