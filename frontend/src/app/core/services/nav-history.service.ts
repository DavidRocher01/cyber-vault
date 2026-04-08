import { Injectable } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class NavHistoryService {
  private history: string[] = [];
  private cursor = -1;
  private navigating = false;

  constructor(private router: Router) {
    // Seed with the current URL so the very first page is in history
    if (this.router.url) {
      this.history.push(this.router.url);
      this.cursor = 0;
    }

    this.router.events
      .pipe(filter(e => e instanceof NavigationEnd))
      .subscribe((e: any) => {
        if (this.navigating) return;
        // Avoid duplicate if the seed URL matches the first NavigationEnd
        if (this.history[this.cursor] === e.urlAfterRedirects) return;
        this.history = this.history.slice(0, this.cursor + 1);
        this.history.push(e.urlAfterRedirects);
        this.cursor = this.history.length - 1;
      });
  }

  get canGoBack(): boolean {
    return this.cursor > 0;
  }

  get canGoForward(): boolean {
    return this.cursor < this.history.length - 1;
  }

  back() {
    if (!this.canGoBack) return;
    this.navigating = true;
    this.cursor--;
    this.router.navigateByUrl(this.history[this.cursor]).then(() => {
      this.navigating = false;
    });
  }

  forward() {
    if (!this.canGoForward) return;
    this.navigating = true;
    this.cursor++;
    this.router.navigateByUrl(this.history[this.cursor]).then(() => {
      this.navigating = false;
    });
  }
}
