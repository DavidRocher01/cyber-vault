import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule, NgClass } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatExpansionModule } from '@angular/material/expansion';

import { CyberscanService, Plan } from '../services/cyberscan.service';
import { AuthService } from '../../../core/services/auth.service';
import { ThemeService } from '../../../core/services/theme.service';
import { I18nService } from '../../../core/services/i18n.service';
import { Title, Meta } from '@angular/platform-browser';

@Component({
  selector: 'app-cyberscan-landing',
  standalone: true,
  imports: [
    CommonModule,
    NgClass,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatExpansionModule,
  ],
  templateUrl: './landing.component.html',
})
export class LandingComponent implements OnInit {
  private cyberscan = inject(CyberscanService);
  private auth = inject(AuthService);
  private router = inject(Router);
  private titleService = inject(Title);
  private meta = inject(Meta);
  readonly themeService = inject(ThemeService);
  readonly i18n = inject(I18nService);

  plans: Plan[] = [];
  loading = true;
  checkoutLoading: number | null = null;

  counters = [
    { label: 'sites scannés', icon: 'language', target: 500, current: signal(0), suffix: '+' },
    { label: 'vulnérabilités détectées', icon: 'bug_report', target: 12000, current: signal(0), suffix: '+' },
    { label: 'disponibilité', icon: 'verified', target: 99, current: signal(0), suffix: '%' },
  ];

  features = [
    { icon: 'security', title: 'Analyse SSL/TLS', desc: 'Audit complet des protocoles, chiffrements et certificats' },
    { icon: 'bug_report', title: 'Détection de vulnérabilités', desc: 'Headers HTTP, injections, XSS, CSRF et plus' },
    { icon: 'dns', title: 'Prise d\'empreinte technologique', desc: 'Identification des frameworks, CMS, CDN utilisés' },
    { icon: 'vpn_key', title: 'Audit JWT', desc: 'Détection des tokens faibles, alg:none, secrets par défaut' },
    { icon: 'warning', title: 'Threat Intelligence', desc: 'Corrélation avec Shodan InternetDB et bases CVE' },
    { icon: 'picture_as_pdf', title: 'Rapport PDF', desc: 'Rapport complet avec score de risque et recommandations' },
  ];

  testimonials = [
    {
      name: 'Sophie M.',
      role: 'CTO, StartupTech',
      avatar: 'S',
      text: 'CyberScan nous a permis de détecter une fuite de configuration en production avant qu\'elle ne soit exploitée. Indispensable.',
      stars: 5,
    },
    {
      name: 'Thomas R.',
      role: 'Développeur indépendant',
      avatar: 'T',
      text: 'J\'utilise le plan Starter pour mes clients. Les rapports PDF sont clairs et je peux les transmettre directement sans explication.',
      stars: 5,
    },
    {
      name: 'Lucie B.',
      role: 'RSSI, PME industrielle',
      avatar: 'L',
      text: 'Le scan hebdomadaire Business nous donne une visibilité continue sur nos 8 sites. La détection TLS est particulièrement précise.',
      stars: 5,
    },
  ];

  faqs = [
    {
      q: 'Qu\'est-ce que CyberScan analyse exactement ?',
      a: 'CyberScan effectue une analyse non intrusive de votre site : headers de sécurité, configuration SSL/TLS, technologies exposées, JWT, redirections ouvertes, clickjacking, threat intelligence (Shodan, CVE) et bien d\'autres vérifications selon votre plan.',
    },
    {
      q: 'Les scans sont-ils intrusifs ou dangereux pour mon site ?',
      a: 'Non. Tous les scans sont passifs et non destructifs. Nous analysons les réponses publiques de votre serveur, sans jamais tenter d\'exploiter une vulnérabilité.',
    },
    {
      q: 'Comment puis-je recevoir mon rapport ?',
      a: 'Chaque scan génère un rapport PDF téléchargeable depuis votre dashboard. Pour les plans Pro et Business, le rapport est également envoyé automatiquement par email.',
    },
    {
      q: 'Puis-je changer de plan à tout moment ?',
      a: 'Oui. Vous pouvez upgrader ou downgrader votre plan depuis le portail de gestion Stripe accessible dans votre dashboard. Le changement prend effet immédiatement.',
    },
    {
      q: 'Que se passe-t-il si une vulnérabilité critique est détectée ?',
      a: 'Le rapport indique clairement le niveau de criticité (OK / WARNING / CRITICAL) avec des recommandations de remédiation pour chaque finding. Pour le plan Business, un email d\'alerte est envoyé immédiatement.',
    },
    {
      q: 'Comment fonctionne la facturation ?',
      a: 'La facturation est mensuelle, sans engagement, via Stripe. Vous pouvez résilier à tout moment depuis votre portail de gestion. Aucune donnée de paiement n\'est stockée sur nos serveurs.',
    },
  ];

  auditOffers = [
    {
      icon: 'flash_on',
      name: 'Flash',
      target: 'Sites vitrines, blogs, indépendants',
      price: '490 €',
      duration: '0,5 jour',
      badge: '',
      featured: false,
      items: [
        'Scan de vulnérabilités externes (OWASP ZAP)',
        'Analyse SSL/TLS (SSL Labs)',
        'Vérification des headers HTTP',
        'Scan de ports (Nmap)',
        'Rapport synthétique 3-5 pages (score A→F)',
      ],
    },
    {
      icon: 'code',
      name: 'App-Check',
      target: 'Startups, SaaS, applications métiers',
      price: '1 450 €',
      duration: '1,5 jours',
      badge: 'Recommandé',
      featured: true,
      items: [
        'Tout l\'audit Flash inclus',
        'Audit de code statique (SAST)',
        'Scan de dépendances (SCA) — package.json & requirements.txt',
        'Recherche de secrets dans le code',
        'Audit des droits PostgreSQL',
        'Rapport détaillé 10-15 pages + plan d\'action',
      ],
    },
    {
      icon: 'security',
      name: 'Pentest Léger',
      target: 'E-commerce, santé, finance, données sensibles',
      price: '3 800 €',
      duration: '4 jours',
      badge: 'Haut de gamme',
      featured: false,
      items: [
        'Tout l\'audit App-Check inclus',
        'Tests d\'intrusion manuels (SQLi, JWT, auth bypass)',
        'Test de logique métier (IDOR, escalade de privilèges)',
        'Audit configuration Cloud (AWS / Azure / OVH)',
        'Rapport complet avec preuves d\'exploitation',
        'Recommandations de code précises',
      ],
    },
  ];

  newsletterItems = [
    { icon: 'public', title: 'Flash International', desc: 'Une cyberattaque majeure décryptée chaque semaine avec l\'impact estimé et le risque local' },
    { icon: 'lightbulb', title: 'Le Bon Réflexe', desc: 'Une pratique simple en 2 minutes qui bloque 80% des attaques basiques' },
    { icon: 'gavel', title: 'Coin des Dirigeants', desc: 'Réglementation française, lois cyber et conseils pour sensibiliser vos équipes' },
  ];

  newsletterSchedule = [
    { week: '01', actu: 'Piratage d\'un hôpital aux USA', reflex: 'Activer la Double Authentification (MFA)' },
    { week: '02', actu: 'Vol de données massif en Corée', reflex: 'Utiliser un gestionnaire de mots de passe' },
    { week: '03', actu: 'Deepfake vocal d\'un PDG à Londres', reflex: 'Créer un "mot de passe verbal" pour les virements' },
    { week: '04', actu: 'Failles dans les objets connectés (IoT)', reflex: 'Changer le mot de passe par défaut de sa box/caméra' },
    { week: '05', actu: 'Ransomware sur une mairie en Espagne', reflex: 'Vérifier que sa sauvegarde est "hors-ligne"' },
    { week: '06', actu: 'Fraude aux faux QR codes au Japon', reflex: 'Ne jamais scanner un QR code public sans douter' },
  ];

  comparisonRows = [
    { label: 'Sites surveillés', starter: '1', pro: '3', business: '10' },
    { label: 'Fréquence des scans', starter: 'Mensuel', pro: 'Mensuel', business: 'Hebdomadaire' },
    { label: 'Rapport PDF', starter: true, pro: true, business: true },
    { label: 'Headers & SSL', starter: true, pro: true, business: true },
    { label: 'TLS audit / Threat Intel', starter: false, pro: true, business: true },
    { label: 'JWT / Clickjacking / Redirects', starter: false, pro: false, business: true },
    { label: 'Alerte email CRITICAL', starter: false, pro: true, business: true },
    { label: 'Support prioritaire', starter: false, pro: false, business: true },
  ];

  ngOnInit() {
    this.titleService.setTitle('CyberScan — Audit de sécurité web automatisé');
    this.meta.updateTag({ name: 'description', content: 'Scannez vos sites web, détectez les vulnérabilités et recevez des rapports PDF complets. Plans à partir de 9€/mois.' });
    this.themeService.apply();
    this.cyberscan.getPlans().subscribe({
      next: plans => { this.plans = plans; this.loading = false; },
      error: () => { this.loading = false; },
    });
    this.animateCounters();
  }

  animateCounters() {
    this.counters.forEach(counter => {
      const steps = 60;
      const step = counter.target / steps;
      let current = 0;
      const timer = setInterval(() => {
        current = Math.min(current + step, counter.target);
        counter.current.set(Math.floor(current));
        if (current >= counter.target) clearInterval(timer);
      }, 30);
    });
  }

  get isLoggedIn(): boolean {
    return this.auth.isAuthenticated();
  }

  subscribe(plan: Plan) {
    if (!this.auth.isAuthenticated()) {
      this.router.navigate(['/auth/login']);
      return;
    }
    this.checkoutLoading = plan.id;
    this.cyberscan.createCheckout(plan.id).subscribe({
      next: res => { window.location.href = res.checkout_url; },
      error: () => { this.checkoutLoading = null; },
    });
  }

  formatPrice(cents: number): string {
    return (cents / 100).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });
  }

  getPlanFeatures(plan: Plan): string[] {
    const features: string[] = [
      `${plan.max_sites} site${plan.max_sites > 1 ? 's' : ''}`,
      `Scan tous les ${plan.scan_interval_days} jours`,
      'Rapport PDF complet',
      'Modules Tier 1 & 2',
    ];
    if (plan.tier_level >= 3) features.push('Modules Tier 3 (TLS, Threat Intel, Fingerprint)');
    if (plan.tier_level >= 4) features.push('Modules Tier 4 (JWT, Redirects, Clickjacking)');
    return features;
  }

  getPlanBadge(plan: Plan): string {
    if (plan.name === 'pro') return 'Populaire';
    if (plan.name === 'business') return 'Pro';
    return '';
  }
}
