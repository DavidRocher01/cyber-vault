import { Routes } from '@angular/router';
import { authGuard } from '../../core/guards/auth.guard';

export const CYBERSCAN_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./landing/landing.component').then(m => m.LandingComponent),
    title: 'CyberScan — Audit de sécurité web',
  },
  {
    path: 'dashboard',
    loadComponent: () => import('./dashboard/dashboard.component').then(m => m.DashboardComponent),
    canActivate: [authGuard],
    title: 'Dashboard — CyberScan',
  },
  {
    path: 'scan/:id',
    loadComponent: () => import('./scan-detail/scan-detail.component').then(m => m.ScanDetailComponent),
    canActivate: [authGuard],
    title: 'Résultats du scan — CyberScan',
  },
  {
    path: 'profile',
    loadComponent: () => import('./profile/profile.component').then(m => m.ProfileComponent),
    canActivate: [authGuard],
    title: 'Mon profil — CyberScan',
  },
  {
    path: 'onboarding',
    loadComponent: () => import('./onboarding/onboarding.component').then(m => m.OnboardingComponent),
    canActivate: [authGuard],
    title: 'Démarrage — CyberScan',
  },
  {
    path: 'success',
    loadComponent: () => import('./success/success.component').then(m => m.CheckoutSuccessComponent),
    canActivate: [authGuard],
    title: 'Abonnement activé — CyberScan',
  },
  {
    path: 'ressources',
    loadComponent: () => import('./ressources/ressources.component').then(m => m.RessourcesComponent),
    title: 'Ressources — CyberScan',
  },
  {
    path: 'bonnes-pratiques',
    loadComponent: () => import('./bonnes-pratiques/bonnes-pratiques.component').then(m => m.BonnesPratiquesComponent),
    title: 'Bonnes pratiques — CyberScan',
  },
];
