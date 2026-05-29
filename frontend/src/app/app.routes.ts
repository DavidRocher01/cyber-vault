import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { cryptoGuard } from './core/guards/crypto.guard';
import { awarenessLearnerGuard } from './core/guards/awareness-learner.guard';

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
    loadChildren: () =>
      import('./features/cyberscan/cyberscan.routes').then(m => m.CYBERSCAN_ROUTES),
  },
  // ── Awareness learner portal (magic-link auth) ──────────────────────────────
  {
    path: 'awareness/login',
    loadComponent: () =>
      import('./features/awareness-learner/awareness-login.component').then(m => m.AwarenessLoginComponent),
    title: 'Connexion — Sensibilisation NIS2',
  },
  {
    path: 'awareness',
    loadComponent: () =>
      import('./features/awareness-learner/awareness-learner.component').then(m => m.AwarenessLearnerComponent),
    canActivate: [awarenessLearnerGuard],
    title: 'Ma formation — NIS2',
  },
  {
    path: 'awareness/module/:enrollmentId',
    loadComponent: () =>
      import('./features/awareness-module/awareness-module.component').then(m => m.AwarenessModuleComponent),
    canActivate: [awarenessLearnerGuard],
    title: 'Module — Sensibilisation NIS2',
  },
  // ── Public certificate verification ────────────────────────────────────────
  {
    path: 'verify-certificate/:publicId',
    loadComponent: () =>
      import('./features/verify-certificate/verify-certificate.component').then(m => m.VerifyCertificateComponent),
    title: 'Vérification attestation — CyberScan',
  },
  { path: '', redirectTo: 'cyberscan', pathMatch: 'full' },
  {
    path: '**',
    loadComponent: () =>
      import('./features/not-found/not-found.component').then(m => m.NotFoundComponent),
  },
];
