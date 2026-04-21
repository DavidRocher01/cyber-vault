import { Component, OnInit, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { CommonModule } from '@angular/common';
import { NavHistoryService } from './core/services/nav-history.service';
import { CookieBannerComponent } from './shared/cookie-banner/cookie-banner.component';
import { CyberLoaderComponent } from './shared/cyber-loader/cyber-loader.component';

const MIN_LOADER_MS = 1800;

@Component({
    standalone: true,
    selector: 'app-root',
    imports: [RouterOutlet, CookieBannerComponent, CyberLoaderComponent, CommonModule],
    template: `
    <app-cyber-loader [visible]="loading" product="CYBERSCAN" />
    @if (!loading) {
      <router-outlet />
      <app-cookie-banner />
    }
  `
})
export class AppComponent implements OnInit {
  loading = true;
  private startTime = Date.now();

  constructor() { inject(NavHistoryService); }

  ngOnInit(): void {
    const elapsed = Date.now() - this.startTime;
    setTimeout(() => this.loading = false, Math.max(0, MIN_LOADER_MS - elapsed));
  }
}
