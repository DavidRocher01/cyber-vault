import { Injectable, signal, computed } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class NavHistoryService {
  private history: string[] = [];
  private navigating = false;

  private _cursor = signal(-1);

  readonly canGoBack  = computed(() => this._cursor() > 0);
  readonly canGoForward = computed(() => this._cursor() < this.history.length - 1);

  constructor(private router: Router) {
    if (this.router.url) {
      this.history.push(this.router.url);
      this._cursor.set(0);
    }

    this.router.events
      .pipe(filter(e => e instanceof NavigationEnd))
      .subscribe((e: any) => {
        if (this.navigating) return;
        const cursor = this._cursor();
        if (this.history[cursor] === e.urlAfterRedirects) return;
        this.history = this.history.slice(0, cursor + 1);
        this.history.push(e.urlAfterRedirects);
        this._cursor.set(this.history.length - 1);
      });
  }

  back() {
    if (!this.canGoBack()) return;
    this.navigating = true;
    this._cursor.update(c => c - 1);
    this.router.navigateByUrl(this.history[this._cursor()]).then(() => {
      this.navigating = false;
    });
  }

  forward() {
    if (!this.canGoForward()) return;
    this.navigating = true;
    this._cursor.update(c => c + 1);
    this.router.navigateByUrl(this.history[this._cursor()]).then(() => {
      this.navigating = false;
    });
  }
}
