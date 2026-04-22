import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const KONAMI = ['ArrowUp','ArrowUp','ArrowDown','ArrowDown','ArrowLeft','ArrowRight','ArrowLeft','ArrowRight','b','a'];

function makeKeyEvent(key: string): KeyboardEvent {
  return { key } as KeyboardEvent;
}

// Minimal stub — avoids Angular DI
class EasterEggServiceStub {
  matrixTrigger$ = { next: vi.fn() };
  private konamiBuffer: string[] = [];
  private typingBuffer = '';
  private logoClicks = 0;
  private logoTimer: any;

  // Expose private handler for testing
  onKey(e: KeyboardEvent) {
    this.konamiBuffer = [...this.konamiBuffer, e.key].slice(-KONAMI.length);
    if (this.konamiBuffer.join(',') === KONAMI.join(',')) {
      this.konamiBuffer = [];
      this.matrixTrigger$.next();
    }
    const SECRET_WORD = 'cyberscan';
    if (e.key.length === 1) {
      this.typingBuffer = (this.typingBuffer + e.key.toLowerCase()).slice(-SECRET_WORD.length);
      if (this.typingBuffer === SECRET_WORD) {
        this.typingBuffer = '';
        this.triggerSystemBreach();
      }
    }
  }

  triggerSystemBreach = vi.fn();

  onLogoClick() {
    this.logoClicks++;
    clearTimeout(this.logoTimer);
    this.logoTimer = setTimeout(() => { this.logoClicks = 0; }, 2000);
    if (this.logoClicks >= 7) {
      this.logoClicks = 0;
      this.triggerGlitch();
    }
  }

  triggerGlitch = vi.fn();

  getLogoClicks() { return this.logoClicks; }
  getTypingBuffer() { return this.typingBuffer; }
  getKonamiBuffer() { return this.konamiBuffer; }
}

describe('EasterEggService — Konami Code', () => {
  let svc: EasterEggServiceStub;

  beforeEach(() => { svc = new EasterEggServiceStub(); });

  it('does not fire matrixTrigger$ on partial sequence', () => {
    KONAMI.slice(0, 5).forEach(k => svc.onKey(makeKeyEvent(k)));
    expect(svc.matrixTrigger$.next).not.toHaveBeenCalled();
  });

  it('fires matrixTrigger$ on complete Konami sequence', () => {
    KONAMI.forEach(k => svc.onKey(makeKeyEvent(k)));
    expect(svc.matrixTrigger$.next).toHaveBeenCalledOnce();
  });

  it('resets buffer after successful Konami trigger', () => {
    KONAMI.forEach(k => svc.onKey(makeKeyEvent(k)));
    expect(svc.getKonamiBuffer()).toHaveLength(0);
  });

  it('keeps only last 10 keys in buffer', () => {
    for (let i = 0; i < 15; i++) svc.onKey(makeKeyEvent('x'));
    expect(svc.getKonamiBuffer()).toHaveLength(KONAMI.length);
  });

  it('fires again on a second complete sequence', () => {
    KONAMI.forEach(k => svc.onKey(makeKeyEvent(k)));
    KONAMI.forEach(k => svc.onKey(makeKeyEvent(k)));
    expect(svc.matrixTrigger$.next).toHaveBeenCalledTimes(2);
  });
});

describe('EasterEggService — "cyberscan" typing detection', () => {
  let svc: EasterEggServiceStub;

  beforeEach(() => { svc = new EasterEggServiceStub(); });

  it('does not trigger breach on partial word', () => {
    'cybers'.split('').forEach(k => svc.onKey(makeKeyEvent(k)));
    expect(svc.triggerSystemBreach).not.toHaveBeenCalled();
  });

  it('triggers breach on exact "cyberscan"', () => {
    'cyberscan'.split('').forEach(k => svc.onKey(makeKeyEvent(k)));
    expect(svc.triggerSystemBreach).toHaveBeenCalledOnce();
  });

  it('is case-insensitive', () => {
    'CYBERSCAN'.split('').forEach(k => svc.onKey(makeKeyEvent(k)));
    expect(svc.triggerSystemBreach).toHaveBeenCalledOnce();
  });

  it('ignores non-printable keys (length > 1)', () => {
    svc.onKey(makeKeyEvent('ArrowUp'));
    expect(svc.getTypingBuffer()).toBe('');
  });

  it('resets typing buffer after trigger', () => {
    'cyberscan'.split('').forEach(k => svc.onKey(makeKeyEvent(k)));
    expect(svc.getTypingBuffer()).toBe('');
  });

  it('sliding window — detects "cyberscan" embedded in longer input', () => {
    'xxxxcyberscan'.split('').forEach(k => svc.onKey(makeKeyEvent(k)));
    expect(svc.triggerSystemBreach).toHaveBeenCalledOnce();
  });
});

describe('EasterEggService — logo click counter', () => {
  let svc: EasterEggServiceStub;

  beforeEach(() => {
    vi.useFakeTimers();
    svc = new EasterEggServiceStub();
  });

  afterEach(() => { vi.useRealTimers(); });

  it('does not trigger glitch before 7 clicks', () => {
    for (let i = 0; i < 6; i++) svc.onLogoClick();
    expect(svc.triggerGlitch).not.toHaveBeenCalled();
  });

  it('triggers glitch at exactly 7 clicks', () => {
    for (let i = 0; i < 7; i++) svc.onLogoClick();
    expect(svc.triggerGlitch).toHaveBeenCalledOnce();
  });

  it('resets counter to 0 after glitch', () => {
    for (let i = 0; i < 7; i++) svc.onLogoClick();
    expect(svc.getLogoClicks()).toBe(0);
  });

  it('resets counter after 2s inactivity', () => {
    for (let i = 0; i < 5; i++) svc.onLogoClick();
    vi.advanceTimersByTime(2001);
    expect(svc.getLogoClicks()).toBe(0);
  });

  it('does not reset counter before 2s', () => {
    for (let i = 0; i < 5; i++) svc.onLogoClick();
    vi.advanceTimersByTime(1999);
    expect(svc.getLogoClicks()).toBe(5);
  });

  it('can trigger glitch again after reset', () => {
    for (let i = 0; i < 7; i++) svc.onLogoClick();
    for (let i = 0; i < 7; i++) svc.onLogoClick();
    expect(svc.triggerGlitch).toHaveBeenCalledTimes(2);
  });
});
