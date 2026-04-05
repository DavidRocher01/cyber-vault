import { Routes } from '@angular/router';
import { authGuard } from '../../core/guards/auth.guard';

export const AUTH_ROUTES: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./login/login.component').then(m => m.LoginComponent),
  },
  {
    path: 'register',
    loadComponent: () => import('./register/register.component').then(m => m.RegisterComponent),
  },
  {
    path: 'forgot-password',
    loadComponent: () => import('./forgot-password/forgot-password.component').then(m => m.ForgotPasswordComponent),
    title: 'Mot de passe oublié — CyberScan',
  },
  {
    path: 'reset-password',
    loadComponent: () => import('./reset-password/reset-password.component').then(m => m.ResetPasswordComponent),
    title: 'Nouveau mot de passe — CyberScan',
  },
  {
    path: 'master-password',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./master-password/master-password.component').then(m => m.MasterPasswordComponent),
  },
  { path: '', redirectTo: 'login', pathMatch: 'full' },
];
