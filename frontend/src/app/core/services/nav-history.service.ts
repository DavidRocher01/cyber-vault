import { Injectable, signal, computed } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { Location } from '@angular/common';
import { filter } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class NavHistoryService {
  private stack: string[] = [];
  private pos = signal(0);
  private jumping = false;

  readonly canGoBack    = computed(() => this.pos() > 0);
  readonly canGoForward = computed(() => this.pos() < this.stack.length - 1);

  constructor(private router: Router, private location: Location) {
    // Seed with initial URL
    const initial = this.router.url || '/';
    this.stack.push(initial);
    this.pos.set(0);

    this.router.events
      .pipe(filter(e => e instanceof NavigationEnd))
      .subscribe((e: any) => {
        if (this.jumping) return;
        const url = e.urlAfterRedirects as string;
        const current = this.stack[this.pos()];
        if (current === url) return;                         // same page, skip
        const newStack = this.stack.slice(0, this.pos() + 1);
        newStack.push(url);
        this.stack = newStack;
        this.pos.set(this.stack.length - 1);
      });
  }

  back() {
    if (!this.canGoBack()) return;
    this.jumping = true;
    const next = this.pos() - 1;
    this.pos.set(next);
    this.router.navigateByUrl(this.stack[next]).finally(() => {
      this.jumping = false;
    });
  }

  forward() {
    if (!this.canGoForward()) return;
    this.jumping = true;
    const next = this.pos() + 1;
    this.pos.set(next);
    this.router.navigateByUrl(this.stack[next]).finally(() => {
      this.jumping = false;
    });
  }
}
