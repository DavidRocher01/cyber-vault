import { Injectable, signal, computed, PLATFORM_ID, Inject } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs';

const STORAGE_KEY = 'cvault_nav_history';

@Injectable({ providedIn: 'root' })
export class NavHistoryService {
  private stack: string[];
  private pos: ReturnType<typeof signal<number>>;
  private jumping = false;

  readonly canGoBack: ReturnType<typeof computed<boolean>>;
  readonly canGoForward: ReturnType<typeof computed<boolean>>;

  constructor(
    private router: Router,
    @Inject(PLATFORM_ID) private platformId: object
  ) {
    this.stack = this.loadStack();
    this.pos = signal(Math.max(0, this.stack.length - 1));
    this.canGoBack = computed(() => this.pos() > 0);
    this.canGoForward = computed(() => this.pos() < this.stack.length - 1);
    this.router.events.pipe(filter(e => e instanceof NavigationEnd)).subscribe((e: any) => {
      if (this.jumping) return;
      const url = e.urlAfterRedirects as string;
      if (this.stack[this.pos()] === url) return;
      const newStack = this.stack.slice(0, this.pos() + 1);
      newStack.push(url);
      this.stack = newStack;
      this.pos.set(newStack.length - 1);
      this.saveStack();
    });
  }

  back() {
    if (!this.canGoBack() || this.jumping) return;
    this.jumping = true;
    const newPos = this.pos() - 1;
    this.pos.set(newPos);
    this.saveStack();
    this.router.navigateByUrl(this.stack[newPos]).then(() => {
      this.jumping = false;
    });
  }

  forward() {
    if (!this.canGoForward() || this.jumping) return;
    this.jumping = true;
    const newPos = this.pos() + 1;
    this.pos.set(newPos);
    this.saveStack();
    this.router.navigateByUrl(this.stack[newPos]).then(() => {
      this.jumping = false;
    });
  }

  private loadStack(): string[] {
    if (!isPlatformBrowser(this.platformId)) return [];
    try {
      const stored = sessionStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  }

  private saveStack(): void {
    if (!isPlatformBrowser(this.platformId)) return;
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(this.stack));
    } catch {}
  }
}
