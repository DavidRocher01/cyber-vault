import { Routes } from '@angular/router';
import { authGuard } from '../../core/guards/auth.guard';

export const CYBERSCAN_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./landing/landing.component').then(m => m.LandingComponent),
  },
  {
    path: 'dashboard',
    loadComponent: () => import('./dashboard/dashboard.component').then(m => m.DashboardComponent),
    canActivate: [authGuard],
  },
  {
    path: 'scan/:id',
    loadComponent: () => import('./scan-detail/scan-detail.component').then(m => m.ScanDetailComponent),
    canActivate: [authGuard],
  },
];
