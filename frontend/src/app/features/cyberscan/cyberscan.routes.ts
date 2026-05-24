import { Routes } from '@angular/router';
import { authGuard } from '../../core/guards/auth.guard';
import { rssiGuard } from '../../core/guards/rssi.guard';

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
    path: 'factures',
    loadComponent: () => import('./invoices/invoices.component').then(m => m.InvoicesComponent),
    canActivate: [authGuard],
    title: 'Mes factures — CyberScan',
  },
  {
    path: 'consultant',
    loadComponent: () => import('./consultant-dashboard/consultant-dashboard.component').then(m => m.ConsultantDashboardComponent),
    canActivate: [rssiGuard],
    title: 'RSSI Externalisé — CyberScan',
  },
  {
    path: 'consultant/profile',
    loadComponent: () => import('./consultant-profile/consultant-profile.component').then(m => m.ConsultantProfileComponent),
    canActivate: [rssiGuard],
    title: 'Mon profil consultant — CyberScan',
  },
  {
    path: 'consultant/clients/:id',
    loadComponent: () => import('./client-detail/client-detail.component').then(m => m.ClientDetailComponent),
    canActivate: [rssiGuard],
    title: 'Détail client — CyberScan',
  },
  {
    path: 'sensibilisation',
    loadComponent: () => import('./sensibilisation/sensibilisation.component').then(m => m.SensibilisationComponent),
    canActivate: [authGuard],
    title: 'Sensibilisation — CyberScan',
  },
  {
    path: 'pca',
    loadComponent: () => import('./pca/pca.component').then(m => m.PcaComponent),
    canActivate: [authGuard],
    title: 'PCA Light — CyberScan',
  },
  {
    path: 'darkweb',
    loadComponent: () => import('./darkweb/darkweb.component').then(m => m.DarkwebComponent),
    canActivate: [authGuard],
    title: 'Surveillance Dark Web — CyberScan',
  },
  {
    path: 'darkweb-dossier',
    loadComponent: () => import('./darkweb-dossier/darkweb-dossier.component').then(m => m.DarkwebDossierComponent),
    canActivate: [authGuard],
    title: 'Dark Web Dossier B2B — CyberScan',
  },
  {
    path: 'darkweb-dossier/new',
    loadComponent: () => import('./darkweb-dossier-new/darkweb-dossier-new.component').then(m => m.DarkwebDossierNewComponent),
    canActivate: [authGuard],
    title: 'Nouveau dossier dark web — CyberScan',
  },
  {
    path: 'darkweb-dossier/:id',
    loadComponent: () => import('./darkweb-dossier-detail/darkweb-dossier-detail.component').then(m => m.DarkwebDossierDetailComponent),
    canActivate: [authGuard],
    title: 'Résultats dossier dark web — CyberScan',
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
    path: 'r/:token',
    redirectTo: ({ params }) => `/cyberscan/demo-result/${params['token']}`,
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
  {
    path: 'r00t',
    loadComponent: () => import('./r00t/r00t.component').then(m => m.R00tComponent),
    title: 'r00t@cyberscan — terminal',
  },
  {
    path: 'simulation-phishing',
    loadComponent: () => import('./phishing/phishing.component').then(m => m.PhishingComponent),
    title: 'Simulation de Phishing PME — Test et Sensibilisation | CyberScan',
  },
  {
    path: 'phishing/campaigns',
    loadComponent: () => import('./phishing-campaigns/phishing-campaigns.component').then(m => m.PhishingCampaignsComponent),
    canActivate: [authGuard],
    title: 'Mes campagnes phishing — CyberScan',
  },
  {
    path: 'phishing/new',
    loadComponent: () => import('./phishing-campaign-creator/phishing-campaign-creator.component').then(m => m.PhishingCampaignCreatorComponent),
    canActivate: [authGuard],
    title: 'Nouvelle campagne phishing — CyberScan',
  },
  {
    path: 'phishing/campaigns/:id',
    loadComponent: () => import('./phishing-campaign-detail/phishing-campaign-detail.component').then(m => m.PhishingCampaignDetailComponent),
    canActivate: [authGuard],
    title: 'Résultats campagne — CyberScan',
  },
  {
    path: 'phishing/campaigns/:id/edit',
    loadComponent: () => import('./phishing-campaign-edit/phishing-campaign-edit.component').then(m => m.PhishingCampaignEditComponent),
    canActivate: [authGuard],
    title: 'Configurer campagne — CyberScan',
  },
  {
    path: 'scan-gratuit',
    loadComponent: () => import('./scan-gratuit/scan-gratuit.component').then(m => m.ScanGratuitComponent),
    title: 'Scan de sécurité gratuit — Audit en 90 secondes | CyberScan',
  },
  {
    path: 'contact',
    loadComponent: () => import('./contact/contact.component').then(m => m.ContactComponent),
    title: 'Contact — Réserver un audit cybersécurité | CyberScan',
  },
  {
    path: 'collab/accept/:token',
    loadComponent: () => import('./collab-accept/collab-accept.component').then(m => m.CollabAcceptComponent),
    title: 'Accepter l\'invitation — CyberScan',
  },
  {
    path: 'cout-cyberattaque',
    loadComponent: () => import('./cost-calculator/cost-calculator.component').then(m => m.CostCalculatorComponent),
    title: 'Calculateur coût cyberattaque PME — CyberScan',
  },
  {
    path: 'quiz-maturite',
    loadComponent: () => import('./quiz/quiz.component').then(m => m.QuizComponent),
    title: 'Quiz maturité cybersécurité NIS2 / ISO 27001 — CyberScan',
  },
  {
    path: 'blog',
    loadComponent: () => import('./blog/blog-list.component').then(m => m.BlogListComponent),
    title: 'Blog cybersécurité — Conseils & analyses | CyberScan',
  },
  {
    path: 'blog/:slug',
    loadComponent: () => import('./blog/blog-article.component').then(m => m.BlogArticleComponent),
    title: 'Blog | CyberScan',
  },
  {
    path: 'devis/:token/accepter',
    loadComponent: () => import('./quote-action/quote-action.component').then(m => m.QuoteActionComponent),
    title: 'Acceptation du devis — CyberScan',
  },
  {
    path: 'devis/:token/refuser',
    loadComponent: () => import('./quote-action/quote-action.component').then(m => m.QuoteActionComponent),
    title: 'Refus du devis — CyberScan',
  },
  {
    path: 'reserver',
    loadComponent: () => import('./booking/booking.component').then(m => m.BookingComponent),
    title: 'Réserver un créneau — CyberScan',
  },
  {
    path: 'reserver/annuler',
    loadComponent: () => import('./booking/booking.component').then(m => m.BookingComponent),
    title: 'Annulation réservation — CyberScan',
  },
  {
    path: 'admin/ba61c5a60113/agenda',
    loadComponent: () => import('./booking-admin/booking-admin.component').then(m => m.BookingAdminComponent),
    title: 'Admin — Agenda | CyberScan',
  },
  {
    path: 'admin',
    loadComponent: () => import('./admin/admin-shell.component').then(m => m.AdminShellComponent),
    children: [
      {
        path: '',
        pathMatch: 'full',
        loadComponent: () => import('./admin/dashboard/admin-dashboard.component').then(m => m.AdminDashboardComponent),
        title: 'Admin — Vue d\'ensemble | CyberScan',
      },
      {
        path: 'contacts',
        loadComponent: () => import('./admin/contacts/admin-contacts.component').then(m => m.AdminContactsComponent),
        title: 'Admin — Contacts | CyberScan',
      },
      {
        path: 'blog',
        loadComponent: () => import('./admin/blog/admin-blog.component').then(m => m.AdminBlogComponent),
        title: 'Admin — Blog | CyberScan',
      },
      {
        path: 'users',
        loadComponent: () => import('./admin/users/admin-users.component').then(m => m.AdminUsersComponent),
        title: 'Admin — Utilisateurs | CyberScan',
      },
      {
        path: 'scans',
        loadComponent: () => import('./admin/scans/admin-scans.component').then(m => m.AdminScansComponent),
        title: 'Admin — Scans | CyberScan',
      },
      {
        path: 'invoices',
        loadComponent: () => import('./admin/invoices/admin-invoices.component').then(m => m.AdminInvoicesComponent),
        title: 'Admin — Factures | CyberScan',
      },
      {
        path: 'quotes',
        loadComponent: () => import('./admin/quotes/admin-quotes.component').then(m => m.AdminQuotesComponent),
        title: 'Admin — Devis | CyberScan',
      },
    ],
  },
];
