import { Injectable, inject, OnDestroy } from '@angular/core';
import { Router } from '@angular/router';
import { Subject } from 'rxjs';

const KONAMI = ['ArrowUp','ArrowUp','ArrowDown','ArrowDown','ArrowLeft','ArrowRight','ArrowLeft','ArrowRight','b','a'];
const SECRET_WORD = 'cyberscan';

@Injectable({ providedIn: 'root' })
export class EasterEggService implements OnDestroy {
  private router = inject(Router);

  readonly matrixTrigger$ = new Subject<void>();

  private konamiBuffer: string[] = [];
  private typingBuffer = '';
  private logoClicks = 0;
  private logoTimer: any;

  private onKey = (e: KeyboardEvent) => {
    // Konami Code
    this.konamiBuffer = [...this.konamiBuffer, e.key].slice(-KONAMI.length);
    if (this.konamiBuffer.join(',') === KONAMI.join(',')) {
      this.konamiBuffer = [];
      this.matrixTrigger$.next();
    }

    // "cyberscan" typing
    if (e.key.length === 1) {
      this.typingBuffer = (this.typingBuffer + e.key.toLowerCase()).slice(-SECRET_WORD.length);
      if (this.typingBuffer === SECRET_WORD) {
        this.typingBuffer = '';
        this.triggerSystemBreach();
      }
    }
  };

  constructor() {
    window.addEventListener('keydown', this.onKey);
  }

  ngOnDestroy(): void {
    window.removeEventListener('keydown', this.onKey);
  }

  onLogoClick(): void {
    this.logoClicks++;
    clearTimeout(this.logoTimer);
    this.logoTimer = setTimeout(() => { this.logoClicks = 0; }, 2000);
    if (this.logoClicks >= 7) {
      this.logoClicks = 0;
      this.triggerGlitch();
    }
  }

  private triggerSystemBreach(): void {
    const overlay = document.createElement('div');
    overlay.style.cssText = `
      position:fixed;inset:0;z-index:99999;
      background:rgba(0,0,0,0.92);
      display:flex;flex-direction:column;align-items:center;justify-content:center;
      font-family:'JetBrains Mono',monospace;color:#ff0040;
      animation:fadeIn 0.3s ease;
    `;
    overlay.innerHTML = `
      <style>@keyframes fadeIn{from{opacity:0}to{opacity:1}}</style>
      <div style="font-size:clamp(1.5rem,4vw,3rem);font-weight:700;letter-spacing:0.15em;text-shadow:0 0 20px #ff0040,0 0 40px #ff0040;animation:pulse 0.5s infinite alternate">
        ⚠ SYSTEM BREACH DETECTED ⚠
      </div>
      <div style="margin-top:1.5rem;font-size:0.9rem;color:#ff6080;letter-spacing:0.08em;opacity:0.8">
        Unauthorized access attempt logged — IP flagged — initiating countermeasures…
      </div>
      <div style="margin-top:0.5rem;font-size:0.75rem;color:#660020;letter-spacing:0.06em">
        jk, tu es des nôtres 🤝
      </div>
      <style>@keyframes pulse{from{opacity:0.7}to{opacity:1}}</style>
    `;
    overlay.addEventListener('click', () => overlay.remove());
    document.body.appendChild(overlay);
    setTimeout(() => overlay.remove(), 4000);
  }

  private triggerGlitch(): void {
    const targets = document.querySelectorAll<HTMLElement>('h1, h2, .text-cyan-400');
    const originals = Array.from(targets).map(el => el.style.cssText);
    const glitchChars = '!@#$%^&*<>?/\\|';
    let count = 0;
    const interval = setInterval(() => {
      targets.forEach(el => {
        el.style.transform = `skewX(${(Math.random() - 0.5) * 8}deg)`;
        el.style.filter = `hue-rotate(${Math.random() * 360}deg)`;
        el.style.textShadow = `${(Math.random()-0.5)*6}px 0 #ff0040, ${(Math.random()-0.5)*6}px 0 #00ffff`;
      });
      count++;
      if (count > 14) {
        clearInterval(interval);
        targets.forEach((el, i) => el.style.cssText = originals[i]);
        this.showGlitchMessage();
      }
    }, 80);
  }

  private showGlitchMessage(): void {
    const overlay = document.createElement('div');
    overlay.style.cssText = `
      position:fixed;bottom:2rem;left:50%;transform:translateX(-50%);z-index:99999;
      background:#0a0a0a;border:1px solid #00ff9d;
      padding:1rem 2rem;font-family:'JetBrains Mono',monospace;
      color:#00ff9d;font-size:0.85rem;letter-spacing:0.1em;
      box-shadow:0 0 20px #00ff9d40;
      animation:slideUp 0.4s ease;
    `;
    overlay.innerHTML = `
      <style>@keyframes slideUp{from{opacity:0;transform:translateX(-50%) translateY(20px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}</style>
      > GLITCH_OVERRIDE confirmed — you found a hidden path.
    `;
    document.body.appendChild(overlay);
    setTimeout(() => overlay.remove(), 3000);
  }
}
