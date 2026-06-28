import { Injectable, signal, PLATFORM_ID, inject } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { DOCUMENT } from '@angular/common';

export type Theme = 'dark' | 'light';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly STORAGE_KEY = 'cs_theme';
  private platformId = inject(PLATFORM_ID);
  private doc = inject(DOCUMENT);

  theme = signal<Theme>(this.loadTheme());

  private loadTheme(): Theme {
    if (!isPlatformBrowser(this.platformId)) return 'dark';
    return (localStorage.getItem(this.STORAGE_KEY) as Theme) ?? 'dark';
  }

  toggle() {
    const next: Theme = this.theme() === 'dark' ? 'light' : 'dark';
    this.theme.set(next);
    if (isPlatformBrowser(this.platformId)) {
      localStorage.setItem(this.STORAGE_KEY, next);
      this.doc.documentElement.classList.toggle('light-mode', next === 'light');
    }
  }

  apply() {
    if (isPlatformBrowser(this.platformId)) {
      this.doc.documentElement.classList.toggle('light-mode', this.theme() === 'light');
    }
  }
}
