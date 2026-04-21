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
    path: 'url-scanner',
    loadComponent: () => import('./url-scanner/url-scanner.component').then(m => m.UrlScannerComponent),
    canActivate: [authGuard],
    title: 'Scanner URL suspecte — CyberScan',
  },
  {
    path: 'code-scan',
    loadComponent: () => import('./code-scan/code-scan.component').then(m => m.CodeScanComponent),
    canActivate: [authGuard],
    title: 'Analyse de code — CyberScan',
  },
  {
    path: 'site/:id',
    loadComponent: () => import('./site-detail/site-detail.component').then(m => m.SiteDetailComponent),
    canActivate: [authGuard],
    title: 'Page site — CyberScan',
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
    path: 'nis2',
    loadComponent: () => import('./nis2/nis2.component').then(m => m.Nis2Component),
    canActivate: [authGuard],
    title: 'Conformité NIS2 — CyberScan',
  },
  {
    path: 'iso27001',
    loadComponent: () => import('./iso27001/iso27001.component').then(m => m.Iso27001Component),
    canActivate: [authGuard],
    title: 'Conformité ISO 27001:2022 — CyberScan',
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
  {
    path: 'cgu',
    loadComponent: () => import('./cgu/cgu.component').then(m => m.CguComponent),
    title: 'CGU — CyberScan',
  },
  {
    path: 'politique-confidentialite',
    loadComponent: () => import('./politique-confidentialite/politique-confidentialite.component').then(m => m.PolitiqueConfidentialiteComponent),
    title: 'Politique de confidentialité — CyberScan',
  },
  {
    path: 'mentions-legales',
    loadComponent: () => import('./mentions-legales/mentions-legales.component').then(m => m.MentionsLegalesComponent),
    title: 'Mentions légales — CyberScan',
  },
  {
    path: 'demo-result/:token',
    loadComponent: () => import('./demo-result/demo-result.component').then(m => m.DemoResultComponent),
    title: 'Résultat demo — CyberScan',
  },
  {
    path: 'subdomains/:id',
    loadComponent: () => import('./subdomains/subdomains.component').then(m => m.SubdomainsComponent),
    canActivate: [authGuard],
    title: 'Sous-domaines — CyberScan',
  },
  {
    path: 'admin/newsletter',
    loadComponent: () => import('./newsletter-admin/newsletter-admin.component').then(m => m.NewsletterAdminComponent),
    title: 'Admin Newsletter — CyberScan',
  },
  {
    path: 'newsletter/confirm',
    loadComponent: () => import('./newsletter-confirm/newsletter-confirm.component').then(m => m.NewsletterConfirmComponent),
    title: 'Confirmation newsletter — CyberScan',
  },
  {
    path: 'newsletter/unsubscribe',
    loadComponent: () => import('./newsletter-unsubscribe/newsletter-unsubscribe.component').then(m => m.NewsletterUnsubscribeComponent),
    title: 'Désabonnement newsletter — CyberScan',
  },
];
