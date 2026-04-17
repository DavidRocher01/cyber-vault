import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { NavHistoryService } from './core/services/nav-history.service';
import { CookieBannerComponent } from './shared/cookie-banner/cookie-banner.component';

@Component({
    selector: 'app-root',
    imports: [RouterOutlet, CookieBannerComponent],
    template: `
    <router-outlet />
    <app-cookie-banner />
  `
})
export class AppComponent {
  // Eagerly instantiate so it captures ALL navigation events from app start
  constructor() { inject(NavHistoryService); }
}
