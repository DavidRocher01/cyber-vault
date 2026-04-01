import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { Router } from '@angular/router';
import { NgxSkeletonLoaderModule } from 'ngx-skeleton-loader';

import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-vault-dashboard',
  standalone: true,
  imports: [CommonModule, MatToolbarModule, MatButtonModule, NgxSkeletonLoaderModule],
  templateUrl: './vault-dashboard.component.html',
})
export class VaultDashboardComponent {
  loading = false;

  constructor(private authService: AuthService, private router: Router) {}

  logout() {
    this.authService.logout();
    this.router.navigate(['/auth/login']);
  }
}
