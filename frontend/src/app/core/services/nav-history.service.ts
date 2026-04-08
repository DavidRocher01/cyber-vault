import { Injectable, signal, computed } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class NavHistoryService {
  private stack: string[] = [];
  private pos = signal(0);
  private jumping = false;

  readonly canGoBack    = computed(() => this.pos() > 0);
  readonly canGoForward = computed(() => this.pos() < this.stack.length - 1);

  constructor(private router: Router) {
    const initial = this.router.url || '/';
    this.stack = [initial];
    this.pos.set(0);

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
    const target = this.pos() - 1;
    this.pos.set(target);
    this.router.navigateByUrl(this.stack[target])
      .then(() => { this.jumping = false; })
      .catch(() => { this.jumping = false; });
  }

  forward() {
    if (!this.canGoForward() || this.jumping) return;
    this.jumping = true;
    const target = this.pos() + 1;
    this.pos.set(target);
    this.router.navigateByUrl(this.stack[target])
      .then(() => { this.jumping = false; })
      .catch(() => { this.jumping = false; });
  }
}
