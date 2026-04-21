import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

const RESPONSES: Record<string, string[]> = {
  help: ['Commandes : scan, ping, trace, whoami, hint, clear'],
  whoami: ['inconnu — accès refusé à cette zone'],
  ping: ['PING 404.cyberscan.local: 56 data bytes', 'Request timeout — cette page n\'existe pas'],
  trace: ['1  *  *  *', '2  *  *  *', '3  nowhere.internal  999ms', 'Destination unreachable'],
  hint: ['Essaie /cyberscan/r00t 👀'],
  scan: [
    'Scanning 404 space…',
    'ERROR_CODE    : 0x404 PAGE_NOT_FOUND',
    'LAST_SEEN     : jamais',
    'LOCATION      : limbes du web',
    'RECOMMENDATION: retourner à l\'accueil',
  ],
};

@Component({
  standalone: true,
  selector: 'app-not-found',
  imports: [RouterLink, MatButtonModule, MatIconModule, CommonModule, FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="min-h-screen bg-gray-900 text-white flex flex-col items-center justify-center gap-6 text-center px-8">
      <mat-icon class="!text-[6rem] !w-[6rem] !h-[6rem] text-cyan-400">gpp_bad</mat-icon>
      <h1 class="text-8xl font-extrabold text-cyan-400" style="font-family:'JetBrains Mono',monospace">404</h1>
      <p class="text-2xl font-semibold">Page introuvable</p>
      <p class="text-gray-400 max-w-md">
        La page que vous cherchez n'existe pas ou a été déplacée.
      </p>

      <!-- Mini terminal easter egg -->
      <div class="terminal-box" [class.expanded]="termOpen">
        <button class="term-toggle" (click)="termOpen = !termOpen; cdr.markForCheck()">
          <span style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:#00e645;letter-spacing:0.1em">
            {{ termOpen ? '▼ terminal — cliquer pour fermer' : '▶ ouvrir un terminal de secours…' }}
          </span>
        </button>
        @if (termOpen) {
          <div class="term-body">
            <div *ngFor="let l of termLines" class="term-line" [class.term-cmd]="l.isCmd">{{ l.text }}</div>
            <div class="term-input-row">
              <span style="color:#00e645">$&nbsp;</span>
              <input #termInput [(ngModel)]="termCurrent" (keydown.enter)="termSubmit()"
                     autocomplete="off" spellcheck="false" class="term-field"
                     placeholder="help" />
            </div>
          </div>
        }
      </div>

      <a routerLink="/cyberscan" mat-flat-button color="primary" class="px-8 py-3 text-lg">
        Retour à l'accueil
      </a>

      <p class="text-gray-700 text-xs mt-4" style="font-family:'JetBrains Mono',monospace">
        <!-- tu cherches quelque chose ? /cyberscan/r00t -->
      </p>
    </div>
  `,
  styles: [`
    .terminal-box {
      width: 100%; max-width: 480px;
      background: #050a05; border: 1px solid rgba(0,255,70,0.2);
      border-radius: 8px; overflow: hidden;
      transition: all 0.3s ease;
    }
    .term-toggle {
      width: 100%; padding: 10px 16px; background: transparent;
      border: none; cursor: pointer; text-align: left;
    }
    .term-body { padding: 12px 16px; max-height: 220px; overflow-y: auto; }
    .term-line {
      font-family: 'JetBrains Mono', monospace; font-size: 12px;
      color: #b0ffcc; line-height: 1.6; white-space: pre;
    }
    .term-cmd { color: #00e645; }
    .term-input-row { display: flex; align-items: center; margin-top: 4px; }
    .term-field {
      flex: 1; background: transparent; border: none; outline: none;
      font-family: 'JetBrains Mono', monospace; font-size: 12px;
      color: #00e645; caret-color: #00e645;
    }
  `]
})
export class NotFoundComponent {
  termOpen = false;
  termCurrent = '';
  termLines: { text: string; isCmd: boolean }[] = [
    { text: 'Bienvenue dans la zone 404.', isCmd: false },
    { text: 'Tape "help" pour les commandes disponibles.', isCmd: false },
  ];

  constructor(readonly cdr: ChangeDetectorRef) {}

  termSubmit(): void {
    const cmd = this.termCurrent.trim().toLowerCase();
    if (!cmd) return;
    this.termLines.push({ text: `$ ${cmd}`, isCmd: true });
    const response = RESPONSES[cmd] ?? [`bash: ${cmd}: command not found`];
    response.forEach(t => this.termLines.push({ text: t, isCmd: false }));
    if (cmd === 'clear') this.termLines = [];
    this.termCurrent = '';
    this.cdr.markForCheck();
  }
}
