import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { cryptoGuard } from './core/guards/crypto.guard';

export const routes: Routes = [
  {
    path: 'auth',
    loadChildren: () => import('./features/auth/auth.routes').then(m => m.AUTH_ROUTES),
  },
  {
    path: 'vault',
    loadChildren: () => import('./features/vault/vault.routes').then(m => m.VAULT_ROUTES),
    canActivate: [authGuard, cryptoGuard],
  },
  {
    path: 'cyberscan',
    loadChildren: () => import('./features/cyberscan/cyberscan.routes').then(m => m.CYBERSCAN_ROUTES),
  },
  { path: '', redirectTo: 'cyberscan', pathMatch: 'full' },
  { path: '**', redirectTo: 'cyberscan' },
];
