import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { CommonModule, NgClass } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { ReactiveFormsModule, FormBuilder, Validators, AbstractControl, ValidationErrors } from '@angular/forms';
import { switchMap } from 'rxjs';
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
import { OtpInputComponent } from '../../../shared/otp-input/otp-input.component';
import { AuthService } from '../../../core/services/auth.service';
import { ThemeService } from '../../../core/services/theme.service';
import { I18nService } from '../../../core/services/i18n.service';
import { Title, Meta } from '@angular/platform-browser';
import { DOCUMENT } from '@angular/common';
import { EasterEggService } from '../../../shared/easter-eggs/easter-egg.service';

@Component({
    standalone: true,
    selector: 'app-cyberscan-landing',
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
        OtpInputComponent,
        MatFormFieldModule,
        MatInputModule,
    ],
    templateUrl: './landing.component.html',
    styleUrl: './landing.component.css'
})
export class LandingComponent implements OnInit {
  private cyberscan = inject(CyberscanService);
  readonly auth = inject(AuthService);
  readonly easterEgg = inject(EasterEggService);
  private router = inject(Router);
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);
  private titleService = inject(Title);
  private meta = inject(Meta);
  private doc = inject(DOCUMENT);
  readonly themeService = inject(ThemeService);
  readonly i18n = inject(I18nService);

  readonly version = environment.version;

  plans: Plan[] = [];
  loading = true;
  checkoutLoading: number | null = null;
  openFaqIndex = signal<number | null>(null);

  toggleFaq(index: number) {
    this.openFaqIndex.update(i => (i === index ? null : index));
  }

  // ── Auth modal ────────────────────────────────────────────────────────────
  authPanel = signal<'closed' | 'login' | 'register'>('closed');
  auth2faStep = signal(false);
  pendingEmail = '';
  pendingPassword = '';
  authOtpCode = '';
  authOtpClear = 0; // increment to trigger OTP clear
  authLoading = false;
  authError: string | null = null;
  showAuthPassword = false;

  loginForm = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', Validators.required],
  });

  registerForm = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
    confirmPassword: ['', Validators.required],
  }, { validators: (g: AbstractControl): ValidationErrors | null => {
    const pw = g.get('password')?.value;
    const cp = g.get('confirmPassword')?.value;
    return pw && cp && pw !== cp ? { mismatch: true } : null;
  }});

  openAuth(mode: 'login' | 'register') {
    this.authError = null;
    this.authLoading = false;
    this.auth2faStep.set(false);
    this.loginForm.reset();
    this.registerForm.reset();
    this.authPanel.set(mode);
  }

  closeAuth() {
    this.authPanel.set('closed');
    this.auth2faStep.set(false);
    this.pendingEmail = '';
    this.pendingPassword = '';
  }

  submitLogin() {
    if (this.loginForm.invalid || this.authLoading) return;
    this.authLoading = true;
    this.authError = null;
    const { email, password } = this.loginForm.getRawValue();
    this.auth.login(email, password).subscribe({
      next: res => {
        if ('requires_2fa' in res) {
          this.pendingEmail = email;
          this.pendingPassword = password;
          this.auth2faStep.set(true);
          this.authOtpClear++;
          this.authLoading = false;
        } else {
          this.closeAuth();
          this.router.navigate(['/cyberscan']);
        }
      },
      error: err => {
        this.authError = err.error?.detail ?? 'Identifiants incorrects.';
        this.authLoading = false;
      },
    });
  }

  submitLoginTotp() {
    if (this.authOtpCode.length !== 6) return;
    this.authLoading = true;
    this.authError = null;
    this.auth.login(this.pendingEmail, this.pendingPassword, this.authOtpCode).subscribe({
      next: () => { this.closeAuth(); this.router.navigate(['/cyberscan']); },
      error: err => {
        this.authError = err.error?.detail ?? 'Code invalide.';
        this.authLoading = false;
        this.authOtpClear++;
      },
    });
  }

  cancelAuth2fa() {
    this.auth2faStep.set(false);
    this.authError = null;
    this.authOtpCode = '';
  }

  submitRegister() {
    if (this.registerForm.invalid || this.authLoading) return;
    this.authLoading = true;
    this.authError = null;
    const { email, password } = this.registerForm.getRawValue();
    this.auth.register(email, password).pipe(
      switchMap(() => this.auth.login(email, password))
    ).subscribe({
      next: () => { this.closeAuth(); this.router.navigate(['/cyberscan/onboarding']); },
      error: err => {
        this.authError = err.error?.detail ?? 'Erreur lors de la création du compte.';
        this.authLoading = false;
      },
    });
  }

  get registerPasswordStrength(): number {
    const pw = this.registerForm.get('password')?.value ?? '';
    let score = 0;
    if (pw.length >= 8) score++;
    if (/[A-Z]/.test(pw)) score++;
    if (/[0-9]/.test(pw)) score++;
    if (/[^A-Za-z0-9]/.test(pw)) score++;
    return score;
  }

  get registerStrengthLabel(): string {
    const s = this.registerPasswordStrength;
    if (s <= 1) return 'Faible';
    if (s === 2) return 'Moyen';
    if (s === 3) return 'Fort';
    return 'Très fort';
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
    { icon: 'security', title: 'Analyse SSL/TLS', desc: 'Audit complet des protocoles, chiffrements et certificats. Détection des suites faibles et certificats expirés.' },
    { icon: 'bug_report', title: 'Détection de vulnérabilités', desc: 'Headers HTTP dangereux, injections, XSS, CSRF et 15+ vérifications OWASP Top 10.' },
    { icon: 'dns', title: 'Prise d\'empreinte technologique', desc: 'Identification des frameworks, CMS, CDN utilisés — et des CVE connues associées.' },
    { icon: 'vpn_key', title: 'Audit JWT', desc: 'Détection des tokens faibles, algorithme alg:none, secrets par défaut et mauvaise expiration.' },
    { icon: 'warning', title: 'Threat Intelligence', desc: 'Corrélation avec Shodan InternetDB, bases CVE et réputation IP en temps réel.' },
    { icon: 'picture_as_pdf', title: 'Rapport PDF', desc: 'Rapport complet avec score de risque global, findings classés et plan de remédiation.' },
    { icon: 'link', title: 'Scanner URL', desc: 'Analysez n\'importe quelle URL suspecte : phishing, malware, scripts malveillants, domaines blacklistés.' },
    { icon: 'code', title: 'Scan de code', desc: 'Analyse statique SAST, détection de secrets, SCA sur vos repositories GitHub publics ou privés.' },
    { icon: 'policy', title: 'Conformité NIS2 / ISO 27001', desc: 'Auto-évaluation guidée de votre conformité réglementaire avec score et plan d\'action exportable en PDF.' },
  ];

  testimonials = [
    {
      name: 'Sophie M.',
      role: 'CTO, StartupTech',
      avatar: 'S',
      text: 'CyberScan nous a permis de détecter une fuite de configuration en production avant qu\'elle ne soit exploitée. Indispensable.',
    },
    {
      name: 'Thomas R.',
      role: 'Développeur indépendant',
      avatar: 'T',
      text: 'J\'utilise le plan Starter pour mes clients. Les rapports PDF sont clairs et je peux les transmettre directement sans explication.',
    },
    {
      name: 'Lucie B.',
      role: 'RSSI, PME industrielle',
      avatar: 'L',
      text: 'Le scan hebdomadaire Business nous donne une visibilité continue sur nos 8 sites. La détection TLS est particulièrement précise.',
    },
    {
      name: 'Marc D.',
      role: 'Responsable SI, cabinet comptable',
      avatar: 'M',
      text: 'L\'auto-évaluation NIS2 intégrée nous a évité de faire appel à un cabinet externe. Le plan d\'action PDF est directement exploitable.',
    },
    {
      name: 'Chloé V.',
      role: 'Lead Dev, agence web',
      avatar: 'C',
      text: 'On livre le rapport CyberScan à chaque client en fin de projet. Ça devient un vrai argument commercial et ça rassure les décideurs.',
    },
    {
      name: 'Antoine P.',
      role: 'Fondateur, SaaS RH',
      avatar: 'A',
      text: 'Le scanner de code a trouvé une clé AWS hardcodée dans un vieux fichier de config. Sans CyberScan, on ne l\'aurait jamais vu.',
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
    {
      q: 'Le scan de code fonctionne-t-il sur des dépôts privés ?',
      a: 'Oui. Vous pouvez fournir un Personal Access Token GitHub pour analyser vos repositories privés. Le token est utilisé uniquement pendant le scan et n\'est jamais stocké sur nos serveurs.',
    },
    {
      q: 'CyberScan peut-il m\'aider pour ma conformité NIS2 ou ISO 27001 ?',
      a: 'Oui. L\'outil d\'auto-évaluation NIS2 et ISO 27001 vous guide item par item et génère un rapport PDF de conformité avec un score et un plan d\'action. Il ne remplace pas un audit légal, mais constitue un excellent point de départ pour structurer votre démarche.',
    },
    {
      q: 'Mes données de scan sont-elles confidentielles ?',
      a: 'Oui. Les résultats de vos scans sont strictement privés et accessibles uniquement à vous depuis votre dashboard. Nous ne revendons aucune donnée à des tiers. Les données sont hébergées en Europe (AWS EU-West-3, Paris) et chiffrées au repos.',
    },
  ];

  auditOffers = [
    {
      icon: 'flash_on',
      name: 'Audit Flash',
      target: 'Sites vitrines, blogs, indépendants',
      price: '290 €',
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
      name: 'Audit Standard',
      target: 'Startups, SaaS, applications métiers',
      price: '390 €',
      duration: '1 jour',
      badge: 'Recommandé',
      featured: true,
      items: [
        'Tout l\'Audit Flash inclus',
        'Audit de code statique (SAST)',
        'Scan de dépendances (SCA) — package.json & requirements.txt',
        'Recherche de secrets dans le code',
        'Audit des droits PostgreSQL',
        'Rapport détaillé 10-15 pages + plan d\'action',
      ],
    },
    {
      icon: 'security',
      name: 'Audit Complet',
      target: 'E-commerce, santé, finance, données sensibles',
      price: 'Sur devis',
      duration: '2-3 jours',
      badge: '',
      featured: false,
      items: [
        'Tout l\'Audit Standard inclus',
        'Tests d\'intrusion manuels (SQLi, JWT, auth bypass)',
        'Test de logique métier (IDOR, escalade de privilèges)',
        'Audit configuration Cloud (AWS / Azure / OVH)',
        'Rapport complet avec preuves d\'exploitation',
        'Recommandations de code précises',
      ],
    },
    {
      icon: 'policy',
      name: 'Conformité NIS2 / RGPD',
      target: 'Entreprises soumises à NIS2 ou RGPD',
      price: '890 €',
      duration: '2 jours',
      badge: 'Nouveau',
      featured: false,
      items: [
        'Cartographie des traitements de données',
        'Analyse des écarts NIS2 (34 contrôles)',
        'Revue des contrats sous-traitants (DPA)',
        'Plan de remédiation priorisé',
        'Rapport de conformité certifiable',
        'Accompagnement déclaration CNIL si incident',
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
    { actu_title: 'L\'IA accélère les cyberattaques : une faille exploitée en seulement 72 minutes', actu_url: 'https://www.lemondeinformatique.fr/actualites/lire-l-ia-accelere-la-vitesse-des-cyberattaques-99405.html', actu_source: 'Le Monde Informatique', reflex: 'Réduire le délai de détection grâce à un EDR/SIEM' },
    { actu_title: 'Piratage du fichier SIA : 41 000 détenteurs d\'armes exposés en France', actu_url: 'https://korben.info/fuite-sia-armes-ministere-interieur.html', actu_source: 'Korben', reflex: 'Activer la double authentification sur tous vos comptes' },
    { actu_title: 'Axios compromis : l\'impact d\'une intrusion nord-coréenne sur la chaîne logistique', actu_url: 'https://www.lemagit.fr/actualites/366641121/Axios-compromis-limpact-dune-intrusion-nord-coreenne-sur-la-chaine-logisitique', actu_source: 'LeMagIT', reflex: 'Auditer ses dépendances open source avant mise en prod' },
    { actu_title: 'Europa.eu cyberattaquée par ShinyHunters : Bruxelles minimise l\'impact', actu_url: 'https://www.zataz.com/cyber-actualites-zataz-de-la-semaine-du-30-mars-au-4-avril-2026/', actu_source: 'ZATAZ', reflex: 'Ne jamais minimiser une alerte de sécurité — toujours investiguer' },
    { actu_title: 'Exposition de 16 milliards d\'identifiants et mots de passe : que faire ?', actu_url: 'https://www.cnil.fr/fr/exposition-de-16-milliards-didentifiants-et-des-mots-de-passe-que-faire', actu_source: 'CNIL', reflex: 'Vérifier ses comptes sur haveibeenpwned.com et changer ses mots de passe' },
    { actu_title: '17Cyber : le nouveau réflexe officiel pour signaler une cyberattaque en France', actu_url: 'https://www.gendarmerie.interieur.gouv.fr/gendinfo/actualites/2026/17cyber-le-reflexe-cyber-pour-tous', actu_source: 'Gendarmerie nationale', reflex: 'Signaler toute cyberattaque sur 17cyber.gouv.fr' },
  ];

  comparisonRows = [
    { label: 'Sites surveillés',              starter: '1',          pro: '3',            business: '10',          enterprise: 'Illimités' },
    { label: 'Fréquence des scans',           starter: 'Mensuel',    pro: 'Hebdomadaire', business: 'Quotidien',   enterprise: 'Temps réel' },
    { label: 'Rapport PDF',                   starter: true,         pro: true,           business: true,          enterprise: true },
    { label: 'Headers & SSL',                 starter: true,         pro: true,           business: true,          enterprise: true },
    { label: 'Scanner URL',                   starter: true,         pro: true,           business: true,          enterprise: true },
    { label: 'TLS audit / Threat Intel',      starter: false,        pro: true,           business: true,          enterprise: true },
    { label: 'JWT / Clickjacking / Redirects',starter: false,        pro: false,          business: true,          enterprise: true },
    { label: 'Scan de code (SAST/SCA)',        starter: false,        pro: true,           business: true,          enterprise: true },
    { label: 'Conformité NIS2 / ISO 27001',   starter: false,        pro: true,           business: true,          enterprise: true },
    { label: 'Alerte email CRITICAL',          starter: false,        pro: true,           business: true,          enterprise: true },
    { label: 'Alerte SSL expiration',          starter: false,        pro: true,           business: true,          enterprise: true },
    { label: 'Rapport blanc (logo client)',    starter: false,        pro: false,          business: true,          enterprise: true },
    { label: 'Accès API REST',                 starter: false,        pro: false,          business: false,         enterprise: true },
    { label: 'Webhooks & intégrations',        starter: false,        pro: false,          business: false,         enterprise: true },
    { label: 'Account manager dédié',          starter: false,        pro: false,          business: false,         enterprise: true },
    { label: 'Support prioritaire 24h',        starter: false,        pro: false,          business: true,          enterprise: true },
  ];

  private _setCanonical(url: string): void {
    let link = this.doc.querySelector<HTMLLinkElement>('link[rel="canonical"]');
    if (!link) {
      link = this.doc.createElement('link');
      link.setAttribute('rel', 'canonical');
      this.doc.head.appendChild(link);
    }
    link.setAttribute('href', url);
  }

  ngOnInit() {
    this.titleService.setTitle('CyberScan — Audit de sécurité web automatisé');
    this.meta.updateTag({ name: 'description', content: 'Auditez la sécurité de vos sites web : SSL, headers HTTP, ports ouverts. Rapports PDF automatiques et alertes en temps réel.' });
    this.meta.updateTag({ property: 'og:title', content: 'CyberScan — Audit de sécurité web automatisé' });
    this.meta.updateTag({ property: 'og:description', content: 'Auditez la sécurité de vos sites web : SSL, headers HTTP, ports ouverts. Rapports PDF automatiques et alertes en temps réel.' });
    this.meta.updateTag({ property: 'og:url', content: 'https://cyberscanapp.com/cyberscan' });
    this.meta.updateTag({ property: 'og:type', content: 'website' });
    this.meta.updateTag({ name: 'twitter:card', content: 'summary_large_image' });
    this.meta.updateTag({ name: 'twitter:title', content: 'CyberScan — Audit de sécurité web automatisé' });
    this.meta.updateTag({ name: 'twitter:description', content: 'Auditez la sécurité de vos sites : SSL, headers HTTP, ports ouverts. Rapports PDF inclus.' });
    this._setCanonical('https://cyberscanapp.com/cyberscan');
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

  userMenuOpen = false;

  get isLoggedIn(): boolean {
    return this.auth.isAuthenticated();
  }

  get userInitials(): string {
    const email = this.auth.getCurrentEmail() ?? '';
    return email.slice(0, 2).toUpperCase();
  }

  logout() {
    this.auth.logout();
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
      label: '21 modules',
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
  ];

  // ── Demo scan ─────────────────────────────────────────────────────────────
  demoUrl = signal('');
  demoLoading = signal(false);
  demoError = signal<string | null>(null);

  submitDemoScan() {
    let url = this.demoUrl().trim();
    if (!url) return;
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'https://' + url;
    }
    this.demoLoading.set(true);
    this.demoError.set(null);
    this.cyberscan.createPublicScan(url).subscribe({
      next: res => {
        this.demoLoading.set(false);
        this.router.navigate(['/cyberscan/demo-result', res.token]);
      },
      error: err => {
        this.demoLoading.set(false);
        this.demoError.set(err.error?.detail || 'Erreur lors du lancement du scan. Réessayez.');
      },
    });
  }

  readonly howItWorks = [
    {
      step: '01',
      icon: 'link',
      title: 'Entrez votre URL',
      desc: 'Renseignez l\'adresse de votre site ou de l\'URL suspecte à analyser. Aucune installation requise.',
    },
    {
      step: '02',
      icon: 'radar',
      title: 'Analyse automatique',
      desc: 'Nos 21 modules passent votre site au crible en 2 minutes : SSL, headers, ports, CVE, threat intel et bien plus.',
    },
    {
      step: '03',
      icon: 'picture_as_pdf',
      title: 'Rapport PDF + plan d\'action',
      desc: 'Téléchargez un rapport complet avec score de risque, liste des findings et recommandations de remédiation.',
    },
  ];

  readonly useCases = [
    {
      icon: 'rocket_launch',
      color: 'text-cyan-400',
      bg: 'bg-cyan-900/20 border-cyan-800/40',
      title: 'Startups & SaaS',
      desc: 'Sécurisez votre MVP avant le lancement. Montrez à vos investisseurs que la sécurité est prise au sérieux dès le Day 1.',
      points: ['Audit pré-lancement', 'Rapport pour due diligence', 'Conformité RGPD dès le départ'],
    },
    {
      icon: 'web',
      color: 'text-violet-400',
      bg: 'bg-violet-900/20 border-violet-800/40',
      title: 'Agences web',
      desc: 'Livrez un rapport de sécurité avec chaque projet client. Différenciez-vous et couvrez votre responsabilité.',
      points: ['Rapport blanc à votre logo', 'Scan en fin de projet', 'Argument commercial différenciant'],
    },
    {
      icon: 'business',
      color: 'text-amber-400',
      bg: 'bg-amber-900/20 border-amber-800/40',
      title: 'PME & ETI',
      desc: 'Surveillez vos sites en continu sans recruter un expert. Recevez une alerte dès qu\'une faille est détectée.',
      points: ['Surveillance continue', 'Alertes email CRITICAL', 'Conformité NIS2 guidée'],
    },
    {
      icon: 'shopping_cart',
      color: 'text-green-400',
      bg: 'bg-green-900/20 border-green-800/40',
      title: 'E-commerce',
      desc: 'Protégez les données de paiement de vos clients. Évitez les fuites de données et les sanctions CNIL.',
      points: ['Analyse cookies & CORS', 'Détection de skimmers', 'Conformité PCI-DSS partielle'],
    },
  ];

  readonly cyberStats = [
    { value: '4,88 M$', label: 'Coût moyen d\'une violation de données en 2024', source: 'IBM Cost of a Data Breach 2024' },
    { value: '194 jours', label: 'Délai moyen avant détection d\'une intrusion', source: 'Mandiant M-Trends 2024' },
    { value: '82 %', label: 'Des violations impliquent une erreur humaine ou une mauvaise config', source: 'Verizon DBIR 2024' },
    { value: '9,90 €', label: 'Le prix d\'un abonnement Starter CyberScan par mois', source: 'CyberScan' },
  ];

  scrollToPricing(event: Event) {
    event.preventDefault();
    document.getElementById('pricing')?.scrollIntoView({ behavior: 'smooth' });
  }
}
