import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { NavHistoryService } from './core/services/nav-history.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  template: '<router-outlet />',
})
export class AppComponent {
  // Eagerly instantiate so it captures ALL navigation events from app start
  constructor() { inject(NavHistoryService); }
}
