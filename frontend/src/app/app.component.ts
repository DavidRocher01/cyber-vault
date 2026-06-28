import { Component, OnInit, OnDestroy, inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { RouterOutlet } from '@angular/router';
import { Subscription } from 'rxjs';
import { NavHistoryService } from './core/services/nav-history.service';
import { CookieBannerComponent } from './shared/cookie-banner/cookie-banner.component';
import { MaintenanceBannerComponent } from './shared/maintenance-banner/maintenance-banner.component';
import { CyberLoaderComponent } from './shared/cyber-loader/cyber-loader.component';
import { MatrixRainComponent } from './shared/easter-eggs/matrix-rain.component';
import { EasterEggService } from './shared/easter-eggs/easter-egg.service';

const MIN_LOADER_MS = 1800;

@Component({
  standalone: true,
  selector: 'app-root',
  imports: [
    RouterOutlet,
    CookieBannerComponent,
    MaintenanceBannerComponent,
    CyberLoaderComponent,
    MatrixRainComponent,
  ],
  template: `
    <app-cyber-loader [visible]="loading" product="CYBERSCAN" />
    @if (!loading) {
      <app-maintenance-banner />
      <router-outlet />
      <app-cookie-banner />
      <app-matrix-rain [visible]="matrixVisible" />
    }
  `,
})
export class AppComponent implements OnInit, OnDestroy {
  loading = true;
  matrixVisible = false;

  private startTime = Date.now();
  private easterEgg = inject(EasterEggService);
  private platformId = inject(PLATFORM_ID);
  private sub!: Subscription;

  constructor() {
    inject(NavHistoryService);
    // During SSR prerendering, skip the loader entirely
    if (!isPlatformBrowser(this.platformId)) {
      this.loading = false;
    }
  }

  ngOnInit(): void {
    if (!isPlatformBrowser(this.platformId)) return;
    const elapsed = Date.now() - this.startTime;
    setTimeout(() => (this.loading = false), Math.max(0, MIN_LOADER_MS - elapsed));

    this.sub = this.easterEgg.matrixTrigger$.subscribe(() => {
      this.matrixVisible = true;
      setTimeout(() => (this.matrixVisible = false), 6500);
    });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }
}
