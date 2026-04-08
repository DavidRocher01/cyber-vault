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
    this.router.events
      .pipe(filter(e => e instanceof NavigationEnd))
      .subscribe((e: any) => {
        if (this.jumping) return;
        const url = e.urlAfterRedirects as string;
        if (this.stack[this.pos()] === url) return;
        const newStack = this.stack.slice(0, this.pos() + 1);
        newStack.push(url);
        this.stack = newStack;
        this.pos.set(newStack.length - 1);
      });
  }

  back() {
    if (!this.canGoBack() || this.jumping) return;
    this.jumping = true;
    this.pos.set(this.pos() - 1);
    this.location.back();
    setTimeout(() => { this.jumping = false; }, 150);
  }

  forward() {
    if (!this.canGoForward() || this.jumping) return;
    this.jumping = true;
    this.pos.set(this.pos() + 1);
    this.location.forward();
    setTimeout(() => { this.jumping = false; }, 150);
  }
}
