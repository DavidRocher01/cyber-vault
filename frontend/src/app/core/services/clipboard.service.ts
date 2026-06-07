import { Injectable, PLATFORM_ID, inject } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

@Injectable({ providedIn: 'root' })
export class ClipboardService {
  private readonly isBrowser = isPlatformBrowser(inject(PLATFORM_ID));
  private clearTimer: ReturnType<typeof setTimeout> | null = null;

  copy(text: string, clearAfterMs = 30000): void {
    // SSR-safe: navigator n'existe pas au prerendering
    if (!this.isBrowser || !navigator?.clipboard) return;
    navigator.clipboard.writeText(text);
    if (this.clearTimer) clearTimeout(this.clearTimer);
    this.clearTimer = setTimeout(() => navigator.clipboard.writeText(''), clearAfterMs);
  }
}
