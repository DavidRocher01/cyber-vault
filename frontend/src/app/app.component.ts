import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';
import { NavHistoryService } from './core/services/nav-history.service';
import { CookieBannerComponent } from './shared/cookie-banner/cookie-banner.component';
import { CyberLoaderComponent } from './shared/cyber-loader/cyber-loader.component';
import { MatrixRainComponent } from './shared/easter-eggs/matrix-rain.component';
import { EasterEggService } from './shared/easter-eggs/easter-egg.service';

const MIN_LOADER_MS = 1800;

@Component({
    standalone: true,
    selector: 'app-root',
    imports: [RouterOutlet, CookieBannerComponent, CyberLoaderComponent, MatrixRainComponent, CommonModule],
    template: `
    <app-cyber-loader [visible]="loading" product="CYBERSCAN" />
    @if (!loading) {
      <router-outlet />
      <app-cookie-banner />
      <app-matrix-rain [visible]="matrixVisible" />
    }
  `
})
export class AppComponent implements OnInit, OnDestroy {
  loading = true;
  matrixVisible = false;

  private startTime = Date.now();
  private easterEgg = inject(EasterEggService);
  private sub!: Subscription;

  constructor() { inject(NavHistoryService); }

  ngOnInit(): void {
    const elapsed = Date.now() - this.startTime;
    setTimeout(() => this.loading = false, Math.max(0, MIN_LOADER_MS - elapsed));

    this.sub = this.easterEgg.matrixTrigger$.subscribe(() => {
      this.matrixVisible = true;
      setTimeout(() => this.matrixVisible = false, 6500);
    });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }
}
