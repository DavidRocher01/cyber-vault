import { Routes } from '@angular/router';

export const VAULT_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./vault-dashboard/vault-dashboard.component').then(m => m.VaultDashboardComponent),
  },
];
