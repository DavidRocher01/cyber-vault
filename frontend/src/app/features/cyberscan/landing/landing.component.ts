import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { CommonModule, NgClass } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { environment } from '../../../../environments/environment';

import { CyberscanService, Plan } from '../services/cyberscan.service';
import { GlobeComponent } from '../../../shared/globe/globe.component';
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
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatProgressSpinnerModule,
    GlobeComponent,
    MatFormFieldModule,
    MatInputModule,
  ],
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.css',
})
export class LandingComponent implements OnInit {
  private cyberscan = inject(CyberscanService);
  private auth = inject(AuthService);
  private router = inject(Router);
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);
  private titleService = inject(Title);
  private meta = inject(Meta);
  readonly themeService = inject(ThemeService);
  readonly i18n = inject(I18nService);

  plans: Plan[] = [];
  loading = true;
  checkoutLoading: number | null = null;
  openFaqIndex = signal<number | null>(null);

  toggleFaq(index: number) {
    this.openFaqIndex.update(i => (i === index ? null : index));
  }

  // Newsletter
  newsletterForm = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
  });
  newsletterLoading = false;
  newsletterSent = false;
  newsletterError: string | null = null;

  subscribeNewsletter() {
    if (this.newsletterForm.invalid) return;
    this.newsletterLoading = true;
    this.newsletterError = null;
    this.http.post(`${environment.apiUrl}/newsletter/subscribe`, this.newsletterForm.getRawValue()).subscribe({
      next: () => { this.newsletterSent = true; this.newsletterLoading = false; },
      error: err => {
        this.newsletterError = err.status === 409
          ? 'Vous êtes déjà abonné(e) et actif(ve) !'
          : 'Une erreur est survenue. Réessayez.';
        this.newsletterLoading = false;
      },
    });
  }

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
    {
      q: 'Puis-je analyser une URL suspecte pour savoir si elle est malveillante ?',
      a: 'Oui. L\'outil Scanner URL disponible dans votre dashboard permet d\'analyser n\'importe quelle URL en quelques secondes : détection de phishing, malware, scripts malveillants, redirections suspectes et domaines blacklistés. Idéal pour vérifier un lien reçu par email ou message avant de cliquer.',
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

  newsletterAvatars = [
    { initials: 'ML', bg: '#0e7490', color: '#fff' },
    { initials: 'PD', bg: '#7c3aed', color: '#fff' },
    { initials: 'SB', bg: '#0f766e', color: '#fff' },
    { initials: 'AR', bg: '#b45309', color: '#fff' },
    { initials: 'JC', bg: '#be185d', color: '#fff' },
  ];

  newsletterItems = [
    { emoji: '🌍', bg: 'rgba(239,68,68,0.15)', title: 'Flash International', desc: 'Une cyberattaque majeure décryptée avec l\'impact estimé et le risque pour votre secteur' },
    { emoji: '💡', bg: 'rgba(34,211,238,0.15)', title: 'Le Bon Réflexe', desc: 'Une pratique concrète en 2 minutes qui bloque 80% des attaques courantes' },
    { emoji: '⚖️', bg: 'rgba(168,85,247,0.15)', title: 'Coin des Dirigeants', desc: 'Réglementation française, NIS2, RGPD — ce que vous devez savoir chaque mois' },
  ];

  newsletterSchedule: { actu_title: string; actu_url: string; actu_source: string; reflex: string }[] = [
    { actu_title: 'Cyberhebdo : le fabricant de jouets Hasbro mis à l\'arrêt par une cyberattaque', actu_url: 'https://www.lemagit.fr/actualites/366641123/Cyberhebdo-du-3-avril-2026', actu_source: 'LeMagIT', reflex: 'Activer un plan de réponse aux incidents' },
    { actu_title: 'Axios compromis : l\'impact d\'une intrusion nord-coréenne sur la chaîne logistique', actu_url: 'https://www.lemagit.fr/actualites/366641121/Axios-compromis-limpact-dune-intrusion-nord-coreenne-sur-la-chaine-logisitique', actu_source: 'LeMagIT', reflex: 'Auditer ses dépendances open source avant mise en prod' },
    { actu_title: 'Citrix Netscaler CVE-2026-3055 : il est à nouveau temps de patcher', actu_url: 'https://www.lemagit.fr/actualites/366640755/Citrix-Netscaler-il-est-a-nouveau-temps-de-patcher', actu_source: 'LeMagIT', reflex: 'Appliquer les correctifs de sécurité sans délai' },
    { actu_title: 'Ransomware : une vulnérabilité exploitée 36 jours avant d\'être rendue publique', actu_url: 'https://www.lemagit.fr/actualites/366640450/Ransomware-36-jours-une-vulnerabilite-inedite-exploitee-36-jours-avant-detre-rendue-publique', actu_source: 'LeMagIT', reflex: 'Activer un EDR/SIEM sur vos serveurs critiques' },
    { actu_title: 'Europa.eu cyberattaquée : Bruxelles minimise l\'impact et nie toute compromission', actu_url: 'https://www.zataz.com/cyber-actualites-zataz-de-la-semaine-du-30-mars-au-4-avril-2026/', actu_source: 'ZATAZ', reflex: 'Ne jamais ignorer une alerte de sécurité — toujours investiguer' },
    { actu_title: 'Ransomware 2025–2026 : la concentration des groupes s\'accélère', actu_url: 'https://www.zataz.com/ransomware-2025-2026-la-concentration-saccelere/', actu_source: 'ZATAZ', reflex: 'Vérifier que sa sauvegarde est hors-ligne et testée' },
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
    this.http.get<{ actu_title: string; actu_url: string; actu_source: string; reflex: string }[]>(
      `${environment.apiUrl}/newsletter/schedule`
    ).subscribe({
      next: items => { this.newsletterSchedule = items; },
      error: () => { /* keep hardcoded fallback */ },
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

  readonly trustItems = [
    {
      icon: 'storage',
      q: 'Où sont mes données ?',
      a: 'Hébergées exclusivement sur AWS Paris (eu-west-3), France. Aucun transfert hors Union Européenne.',
    },
    {
      icon: 'lock',
      q: "C'est sécurisé ?",
      a: 'Score A+ sur Mozilla Observatory. Chiffrement AES-256 au repos, TLS 1.3 en transit.',
    },
    {
      icon: 'manage_accounts',
      q: 'Qui accède à mon historique ?',
      a: "Accès restreint par IAM avec MFA obligatoire. Vos rapports ne sont accessibles qu'à votre compte.",
    },
    {
      icon: 'support_agent',
      q: 'Et si ça bug ?',
      a: "Support sous 24h pour les abonnés payants. Notification obligatoire en cas d'incident (RGPD/NIS 2) sous 72h.",
    },
  ];

  readonly archSteps = [
    {
      icon: 'send',
      label: 'Requête API',
      desc: 'Votre demande de scan arrive via HTTPS sur notre API FastAPI.',
    },
    {
      icon: 'workspaces',
      label: 'Conteneur isolé',
      desc: "Un conteneur éphémère est lancé uniquement pour votre analyse.",
    },
    {
      icon: 'analytics',
      label: '19 modules',
      desc: "Les modules s'exécutent en isolation, sans accès aux données des autres clients.",
    },
    {
      icon: 'delete_sweep',
      label: 'Autodestruction',
      desc: 'Le conteneur est détruit. Seul le rapport JSON chiffré est conservé.',
    },
  ];

  readonly complianceItems = [
    {
      icon: 'gavel',
      title: 'RGPD',
      desc: "Registre des traitements tenu. Droit à l'oubli : supprimez vos scans en un clic depuis votre dashboard.",
    },
    {
      icon: 'policy',
      title: 'NIS 2',
      desc: "Signalement d'incident en moins de 72h si votre compte est affecté. Obligations respectées.",
    },
    {
      icon: 'verified',
      title: 'Assurance RC Pro Cyber',
      desc: 'Couverture active pour tous les scans payants. Votre recours en cas de litige sur un résultat.',
    },
  ];
}
