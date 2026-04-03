import { Injectable, signal } from '@angular/core';

export type Theme = 'dark' | 'light';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly STORAGE_KEY = 'cs_theme';
  theme = signal<Theme>(this.loadTheme());

  private loadTheme(): Theme {
    return (localStorage.getItem(this.STORAGE_KEY) as Theme) ?? 'dark';
  }

  toggle() {
    const next: Theme = this.theme() === 'dark' ? 'light' : 'dark';
    this.theme.set(next);
    localStorage.setItem(this.STORAGE_KEY, next);
    document.documentElement.classList.toggle('light-mode', next === 'light');
  }

  apply() {
    document.documentElement.classList.toggle('light-mode', this.theme() === 'light');
  }
}
