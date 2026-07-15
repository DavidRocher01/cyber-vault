import { Routes } from '@angular/router';
import { authGuard } from '../../core/guards/auth.guard';
import { rssiGuard } from '../../core/guards/rssi.guard';

export const CYBERSCAN_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./landing/landing.component').then(m => m.LandingComponent),
    title: 'Rocher Cybersécurité — Audit de sécurité web',
  },
  {
    path: 'dashboard',
    loadComponent: () => import('./dashboard/dashboard.component').then(m => m.DashboardComponent),
    canActivate: [authGuard],
    title: 'Dashboard — Rocher Cybersécurité',
  },
  {
    path: 'scan/:id',
    loadComponent: () =>
      import('./scan-detail/scan-detail.component').then(m => m.ScanDetailComponent),
    canActivate: [authGuard],
    title: 'Résultats du scan — Rocher Cybersécurité',
  },
  {
    path: 'url-scanner',
    loadComponent: () =>
      import('./url-scanner/url-scanner.component').then(m => m.UrlScannerComponent),
    canActivate: [authGuard],
    title: 'Scanner URL suspecte — Rocher Cybersécurité',
  },
  {
    path: 'code-scan',
    loadComponent: () => import('./code-scan/code-scan.component').then(m => m.CodeScanComponent),
    canActivate: [authGuard],
    title: 'Analyse de code — Rocher Cybersécurité',
  },
  {
    path: 'site/:id',
    loadComponent: () =>
      import('./site-detail/site-detail.component').then(m => m.SiteDetailComponent),
    canActivate: [authGuard],
    title: 'Page site — Rocher Cybersécurité',
  },
  {
    path: 'profile',
    loadComponent: () => import('./profile/profile.component').then(m => m.ProfileComponent),
    canActivate: [authGuard],
    title: 'Mon profil — Rocher Cybersécurité',
  },
  {
    path: 'factures',
    loadComponent: () => import('./invoices/invoices.component').then(m => m.InvoicesComponent),
    canActivate: [authGuard],
    title: 'Mes factures — Rocher Cybersécurité',
  },
  {
    path: 'consultant',
    loadComponent: () =>
      import('./consultant-dashboard/consultant-dashboard.component').then(
        m => m.ConsultantDashboardComponent
      ),
    canActivate: [rssiGuard],
    title: 'RSSI Externalisé — Rocher Cybersécurité',
  },
  {
    path: 'consultant/profile',
    loadComponent: () =>
      import('./consultant-profile/consultant-profile.component').then(
        m => m.ConsultantProfileComponent
      ),
    canActivate: [rssiGuard],
    title: 'Mon profil consultant — Rocher Cybersécurité',
  },
  {
    path: 'consultant/clients/:id',
    loadComponent: () =>
      import('./client-detail/client-detail.component').then(m => m.ClientDetailComponent),
    canActivate: [rssiGuard],
    title: 'Détail client — Rocher Cybersécurité',
  },
  {
    path: 'sensibilisation',
    loadComponent: () =>
      import('./sensibilisation/sensibilisation.component').then(m => m.SensibilisationComponent),
    canActivate: [authGuard],
    title: 'Sensibilisation — Rocher Cybersécurité',
  },
  {
    path: 'awareness-pricing',
    loadComponent: () =>
      import('./awareness-pricing/awareness-pricing.component').then(
        m => m.AwarenessPricingComponent
      ),
    canActivate: [authGuard],
    title: 'Tarifs Sensibilisation NIS2 — Rocher Cybersécurité',
  },
  {
    path: 'awareness',
    loadComponent: () =>
      import('./awareness-admin/awareness-admin.component').then(m => m.AwarenessAdminComponent),
    canActivate: [authGuard],
    title: 'Sensibilisation NIS2 — Admin',
  },
  {
    path: 'awareness/org/:id',
    loadComponent: () =>
      import('./awareness-org-detail/awareness-org-detail.component').then(
        m => m.AwarenessOrgDetailComponent
      ),
    canActivate: [authGuard],
    title: 'Organisation — Sensibilisation NIS2',
  },
  {
    path: 'pca',
    loadComponent: () => import('./pca/pca.component').then(m => m.PcaComponent),
    canActivate: [authGuard],
    title: 'PCA Light — Rocher Cybersécurité',
  },
  {
    path: 'darkweb',
    loadComponent: () => import('./darkweb/darkweb.component').then(m => m.DarkwebComponent),
    canActivate: [authGuard],
    title: 'Surveillance Dark Web — Rocher Cybersécurité',
  },
  {
    path: 'darkweb-dossier',
    loadComponent: () =>
      import('./darkweb-dossier/darkweb-dossier.component').then(m => m.DarkwebDossierComponent),
    canActivate: [authGuard],
    title: 'Dark Web Dossier B2B — Rocher Cybersécurité',
  },
  {
    path: 'darkweb-dossier/new',
    loadComponent: () =>
      import('./darkweb-dossier-new/darkweb-dossier-new.component').then(
        m => m.DarkwebDossierNewComponent
      ),
    canActivate: [authGuard],
    title: 'Nouveau dossier dark web — Rocher Cybersécurité',
  },
  {
    path: 'darkweb-dossier/:id',
    loadComponent: () =>
      import('./darkweb-dossier-detail/darkweb-dossier-detail.component').then(
        m => m.DarkwebDossierDetailComponent
      ),
    canActivate: [authGuard],
    title: 'Résultats dossier dark web — Rocher Cybersécurité',
  },
  {
    path: 'onboarding',
    loadComponent: () =>
      import('./onboarding/onboarding.component').then(m => m.OnboardingComponent),
    canActivate: [authGuard],
    title: 'Démarrage — Rocher Cybersécurité',
  },
  {
    path: 'success',
    loadComponent: () =>
      import('./success/success.component').then(m => m.CheckoutSuccessComponent),
    canActivate: [authGuard],
    title: 'Abonnement activé — Rocher Cybersécurité',
  },
  {
    path: 'nis2',
    loadComponent: () => import('./nis2/nis2.component').then(m => m.Nis2Component),
    title: 'Conformité NIS2 — Rocher Cybersécurité',
  },
  {
    path: 'iso27001',
    loadComponent: () => import('./iso27001/iso27001.component').then(m => m.Iso27001Component),
    title: 'Conformité ISO 27001:2022 — Rocher Cybersécurité',
  },
  {
    path: 'ressources',
    loadComponent: () =>
      import('./ressources/ressources.component').then(m => m.RessourcesComponent),
    title: 'Ressources — Rocher Cybersécurité',
  },
  {
    path: 'audit-pme',
    loadComponent: () => import('./audit-pme/audit-pme.component').then(m => m.AuditPmeComponent),
    title: 'Audit sécurité PME — Rocher Cybersécurité',
  },
  {
    path: 'bonnes-pratiques',
    loadComponent: () =>
      import('./bonnes-pratiques/bonnes-pratiques.component').then(m => m.BonnesPratiquesComponent),
    title: 'Bonnes pratiques — Rocher Cybersécurité',
  },
  {
    path: 'cgu',
    loadComponent: () => import('./cgu/cgu.component').then(m => m.CguComponent),
    title: 'CGU — Rocher Cybersécurité',
  },
  {
    path: 'cgv',
    loadComponent: () => import('./cgv/cgv.component').then(m => m.CgvComponent),
    title: 'CGV — Rocher Cybersécurité',
  },
  {
    path: 'dpa',
    loadComponent: () => import('./dpa/dpa.component').then(m => m.DpaComponent),
    title: 'Accord de sous-traitance RGPD (DPA) — Rocher Cybersécurité',
  },
  {
    path: 'politique-confidentialite',
    loadComponent: () =>
      import('./politique-confidentialite/politique-confidentialite.component').then(
        m => m.PolitiqueConfidentialiteComponent
      ),
    title: 'Politique de confidentialité — Rocher Cybersécurité',
  },
  {
    path: 'mentions-legales',
    loadComponent: () =>
      import('./mentions-legales/mentions-legales.component').then(m => m.MentionsLegalesComponent),
    title: 'Mentions légales — Rocher Cybersécurité',
  },
  {
    path: 'demo-result/:token',
    loadComponent: () =>
      import('./demo-result/demo-result.component').then(m => m.DemoResultComponent),
    title: 'Résultat demo — Rocher Cybersécurité',
  },
  {
    path: 'r/:token',
    redirectTo: ({ params }) => `/demo-result/${params['token']}`,
  },
  {
    path: 'subdomains/:id',
    loadComponent: () =>
      import('./subdomains/subdomains.component').then(m => m.SubdomainsComponent),
    canActivate: [authGuard],
    title: 'Sous-domaines — Rocher Cybersécurité',
  },
  {
    path: 'admin/newsletter',
    loadComponent: () =>
      import('./newsletter-admin/newsletter-admin.component').then(m => m.NewsletterAdminComponent),
    title: 'Admin Newsletter — Rocher Cybersécurité',
  },
  {
    path: 'newsletter/confirm',
    loadComponent: () =>
      import('./newsletter-confirm/newsletter-confirm.component').then(
        m => m.NewsletterConfirmComponent
      ),
    title: 'Confirmation newsletter — Rocher Cybersécurité',
  },
  {
    path: 'newsletter/unsubscribe',
    loadComponent: () =>
      import('./newsletter-unsubscribe/newsletter-unsubscribe.component').then(
        m => m.NewsletterUnsubscribeComponent
      ),
    title: 'Désabonnement newsletter — Rocher Cybersécurité',
  },
  {
    path: 'r00t',
    loadComponent: () => import('./r00t/r00t.component').then(m => m.R00tComponent),
    title: 'r00t@cyberscan — terminal',
  },
  {
    path: 'simulation-phishing',
    loadComponent: () => import('./phishing/phishing.component').then(m => m.PhishingComponent),
    title: 'Simulation de Phishing PME — Test et Sensibilisation | Rocher Cybersécurité',
  },
  {
    path: 'phishing/campaigns',
    loadComponent: () =>
      import('./phishing-campaigns/phishing-campaigns.component').then(
        m => m.PhishingCampaignsComponent
      ),
    canActivate: [authGuard],
    title: 'Mes campagnes phishing — Rocher Cybersécurité',
  },
  {
    path: 'phishing/new',
    loadComponent: () =>
      import('./phishing-campaign-creator/phishing-campaign-creator.component').then(
        m => m.PhishingCampaignCreatorComponent
      ),
    canActivate: [authGuard],
    title: 'Nouvelle campagne phishing — Rocher Cybersécurité',
  },
  {
    path: 'phishing/campaigns/:id',
    loadComponent: () =>
      import('./phishing-campaign-detail/phishing-campaign-detail.component').then(
        m => m.PhishingCampaignDetailComponent
      ),
    canActivate: [authGuard],
    title: 'Résultats campagne — Rocher Cybersécurité',
  },
  {
    path: 'phishing/campaigns/:id/edit',
    loadComponent: () =>
      import('./phishing-campaign-edit/phishing-campaign-edit.component').then(
        m => m.PhishingCampaignEditComponent
      ),
    canActivate: [authGuard],
    title: 'Configurer campagne — Rocher Cybersécurité',
  },
  {
    path: 'scan-gratuit',
    loadComponent: () =>
      import('./scan-gratuit/scan-gratuit.component').then(m => m.ScanGratuitComponent),
    title: 'Scan de sécurité gratuit — Audit en 90 secondes | Rocher Cybersécurité',
  },
  {
    path: 'api',
    loadComponent: () =>
      import('./api-landing/api-landing.component').then(m => m.ApiLandingComponent),
    title: 'API Rocher Cybersécurité — Automatisez vos audits de sécurité',
  },
  {
    path: 'contact',
    loadComponent: () => import('./contact/contact.component').then(m => m.ContactComponent),
    title: 'Contact — Réserver un audit cybersécurité | Rocher Cybersécurité',
  },
  {
    path: 'rssi-externalise',
    loadComponent: () =>
      import('./rssi-externalise/rssi-externalise.component').then(m => m.RssiExternaliseComponent),
    title: 'RSSI externalisé — votre RSSI à temps partagé | Rocher Cybersécurité',
  },
  {
    path: 'collab/accept/:token',
    loadComponent: () =>
      import('./collab-accept/collab-accept.component').then(m => m.CollabAcceptComponent),
    title: "Accepter l'invitation — Rocher Cybersécurité",
  },
  {
    path: 'cout-cyberattaque',
    loadComponent: () =>
      import('./cost-calculator/cost-calculator.component').then(m => m.CostCalculatorComponent),
    title: 'Calculateur coût cyberattaque PME — Rocher Cybersécurité',
  },
  {
    path: 'quiz-maturite',
    loadComponent: () => import('./quiz/quiz.component').then(m => m.QuizComponent),
    title: 'Quiz maturité cybersécurité NIS2 / ISO 27001 — Rocher Cybersécurité',
  },
  {
    path: 'blog',
    loadComponent: () => import('./blog/blog-list.component').then(m => m.BlogListComponent),
    title: 'Blog cybersécurité — Conseils & analyses | Rocher Cybersécurité',
  },
  {
    path: 'blog/:slug',
    loadComponent: () => import('./blog/blog-article.component').then(m => m.BlogArticleComponent),
    title: 'Blog | Rocher Cybersécurité',
  },
  {
    path: 'devis/:token/accepter',
    loadComponent: () =>
      import('./quote-action/quote-action.component').then(m => m.QuoteActionComponent),
    title: 'Acceptation du devis — Rocher Cybersécurité',
  },
  {
    path: 'devis/:token/refuser',
    loadComponent: () =>
      import('./quote-action/quote-action.component').then(m => m.QuoteActionComponent),
    title: 'Refus du devis — Rocher Cybersécurité',
  },
  {
    path: 'reserver',
    loadComponent: () => import('./booking/booking.component').then(m => m.BookingComponent),
    title: 'Réserver un créneau — Rocher Cybersécurité',
  },
  {
    path: 'reserver/annuler',
    loadComponent: () => import('./booking/booking.component').then(m => m.BookingComponent),
    title: 'Annulation réservation — Rocher Cybersécurité',
  },
  {
    path: 'admin/ba61c5a60113/agenda',
    loadComponent: () =>
      import('./booking-admin/booking-admin.component').then(m => m.BookingAdminComponent),
    title: 'Admin — Agenda | Rocher Cybersécurité',
  },
  {
    path: 'admin',
    loadComponent: () => import('./admin/admin-shell.component').then(m => m.AdminShellComponent),
    children: [
      {
        path: '',
        pathMatch: 'full',
        loadComponent: () =>
          import('./admin/dashboard/admin-dashboard.component').then(
            m => m.AdminDashboardComponent
          ),
        title: "Admin — Vue d'ensemble | Rocher Cybersécurité",
      },
      {
        path: 'contacts',
        loadComponent: () =>
          import('./admin/contacts/admin-contacts.component').then(m => m.AdminContactsComponent),
        title: 'Admin — Contacts | Rocher Cybersécurité',
      },
      {
        path: 'blog',
        loadComponent: () =>
          import('./admin/blog/admin-blog.component').then(m => m.AdminBlogComponent),
        title: 'Admin — Blog | Rocher Cybersécurité',
      },
      {
        path: 'users',
        loadComponent: () =>
          import('./admin/users/admin-users.component').then(m => m.AdminUsersComponent),
        title: 'Admin — Utilisateurs | Rocher Cybersécurité',
      },
      {
        path: 'scans',
        loadComponent: () =>
          import('./admin/scans/admin-scans.component').then(m => m.AdminScansComponent),
        title: 'Admin — Scans | Rocher Cybersécurité',
      },
      {
        path: 'invoices',
        loadComponent: () =>
          import('./admin/invoices/admin-invoices.component').then(m => m.AdminInvoicesComponent),
        title: 'Admin — Factures | Rocher Cybersécurité',
      },
      {
        path: 'quotes',
        loadComponent: () =>
          import('./admin/quotes/admin-quotes.component').then(m => m.AdminQuotesComponent),
        title: 'Admin — Devis | Rocher Cybersécurité',
      },
    ],
  },
];
