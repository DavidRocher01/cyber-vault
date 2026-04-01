import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class ClipboardService {
  private clearTimer: ReturnType<typeof setTimeout> | null = null;

  copy(text: string, clearAfterMs = 30000): void {
    navigator.clipboard.writeText(text);
    if (this.clearTimer) clearTimeout(this.clearTimer);
    this.clearTimer = setTimeout(() => navigator.clipboard.writeText(''), clearAfterMs);
  }
}
