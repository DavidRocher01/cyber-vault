import { Component, AfterViewInit, inject, OnInit, signal, ViewChild } from '@angular/core';
import { CommonModule, NgClass } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
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
import { DOCUMENT } from '@angular/common';
import { EasterEggService } from '../../../shared/easter-eggs/easter-egg.service';
import { AuthModalComponent } from './components/auth-modal/auth-modal.component';
import { DemoScanComponent } from './components/demo-scan/demo-scan.component';
import {
  FEATURES, TESTIMONIALS, FAQS, AUDIT_OFFERS,
  NEWSLETTER_AVATARS, NEWSLETTER_ITEMS, COMPARISON_ROWS,
  TRUST_ITEMS, ARCH_STEPS, COMPLIANCE_ITEMS,
  HOW_IT_WORKS, USE_CASES, CYBER_STATS,
} from './landing.data';

@Component({
    standalone: true,
    selector: 'app-cyberscan-landing',
    imports: [
        CommonModule,
        NgClass,
        RouterLink,
        MatButtonModule,
        MatCardModule,
        MatIconModule,
        MatProgressSpinnerModule,
        GlobeComponent,
        MatFormFieldModule,
        MatInputModule,
        ReactiveFormsModule,
        AuthModalComponent,
        DemoScanComponent,
    ],
    templateUrl: './landing.component.html',
    styleUrl: './landing.component.css'
})
export class LandingComponent implements OnInit, AfterViewInit {
  @ViewChild(AuthModalComponent) authModal!: AuthModalComponent;

  private cyberscan = inject(CyberscanService);
  readonly auth = inject(AuthService);
  readonly easterEgg = inject(EasterEggService);
  private route = inject(ActivatedRoute);
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

  isRssiConsultant = signal(false);

  // Static data from landing.data.ts
  readonly features        = FEATURES;
  readonly testimonials    = TESTIMONIALS;
  readonly faqs            = FAQS;
  readonly auditOffers     = AUDIT_OFFERS;
  readonly newsletterAvatars = NEWSLETTER_AVATARS;
  readonly newsletterItems   = NEWSLETTER_ITEMS;
  readonly comparisonRows    = COMPARISON_ROWS;
  readonly trustItems        = TRUST_ITEMS;
  readonly archSteps         = ARCH_STEPS;
  readonly complianceItems   = COMPLIANCE_ITEMS;
  readonly howItWorks        = HOW_IT_WORKS;
  readonly useCases          = USE_CASES;
  readonly cyberStats        = CYBER_STATS;

  counters = [
    { label: 'sites scannés', icon: 'language', target: 500, current: signal(0), suffix: '+' },
    { label: 'vulnérabilités détectées', icon: 'bug_report', target: 12000, current: signal(0), suffix: '+' },
    { label: 'disponibilité', icon: 'verified', target: 99, current: signal(0), suffix: '%' },
  ];

  // Newsletter
  newsletterSchedule: { actu_title: string; actu_url: string; actu_source: string; reflex: string }[] = [
    { actu_title: 'L\'IA accélère les cyberattaques : une faille exploitée en seulement 72 minutes', actu_url: 'https://www.lemondeinformatique.fr/actualites/lire-l-ia-accelere-la-vitesse-des-cyberattaques-99405.html', actu_source: 'Le Monde Informatique', reflex: 'Réduire le délai de détection grâce à un EDR/SIEM' },
    { actu_title: 'Piratage du fichier SIA : 41 000 détenteurs d\'armes exposés en France', actu_url: 'https://korben.info/fuite-sia-armes-ministere-interieur.html', actu_source: 'Korben', reflex: 'Activer la double authentification sur tous vos comptes' },
    { actu_title: 'Axios compromis : l\'impact d\'une intrusion nord-coréenne sur la chaîne logistique', actu_url: 'https://www.lemagit.fr/actualites/366641121/Axios-compromis-limpact-dune-intrusion-nord-coreenne-sur-la-chaine-logisitique', actu_source: 'LeMagIT', reflex: 'Auditer ses dépendances open source avant mise en prod' },
    { actu_title: 'Europa.eu cyberattaquée par ShinyHunters : Bruxelles minimise l\'impact', actu_url: 'https://www.zataz.com/cyber-actualites-zataz-de-la-semaine-du-30-mars-au-4-avril-2026/', actu_source: 'ZATAZ', reflex: 'Ne jamais minimiser une alerte de sécurité — toujours investiguer' },
    { actu_title: 'Exposition de 16 milliards d\'identifiants et mots de passe : que faire ?', actu_url: 'https://www.cnil.fr/fr/exposition-de-16-milliards-didentifiants-et-des-mots-de-passe-que-faire', actu_source: 'CNIL', reflex: 'Vérifier ses comptes sur haveibeenpwned.com et changer ses mots de passe' },
    { actu_title: '17Cyber : le nouveau réflexe officiel pour signaler une cyberattaque en France', actu_url: 'https://www.gendarmerie.interieur.gouv.fr/gendinfo/actualites/2026/17cyber-le-reflexe-cyber-pour-tous', actu_source: 'Gendarmerie nationale', reflex: 'Signaler toute cyberattaque sur 17cyber.gouv.fr' },
  ];

  newsletterForm = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
  });
  newsletterLoading = false;
  newsletterSent    = false;
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
    if (this.auth.isAuthenticated()) {
      this.http.get<{ is_rssi_consultant: boolean }>('/api/v1/users/me').subscribe({
        next: u => this.isRssiConsultant.set(u.is_rssi_consultant),
        error: () => {},
      });
    }
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

  ngAfterViewInit() {
    const action = this.route.snapshot.queryParamMap.get('action');
    if (action === 'register' || action === 'login') {
      setTimeout(() => this.authModal.open(action), 0);
    }
  }

  openAuth(mode: 'login' | 'register') {
    this.authModal.open(mode);
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
      this.authModal.open('register');
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

  scrollToPricing(event: Event) {
    event.preventDefault();
    document.getElementById('pricing')?.scrollIntoView({ behavior: 'smooth' });
  }
}
