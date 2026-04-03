import { Component, inject, OnInit } from '@angular/core';
import { CommonModule, NgClass } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { CyberscanService, Plan } from '../services/cyberscan.service';
import { AuthService } from '../../../core/services/auth.service';

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
  ],
  templateUrl: './landing.component.html',
})
export class LandingComponent implements OnInit {
  private cyberscan = inject(CyberscanService);
  private auth = inject(AuthService);
  private router = inject(Router);

  plans: Plan[] = [];
  loading = true;
  checkoutLoading: number | null = null;

  features = [
    { icon: 'security', title: 'Analyse SSL/TLS', desc: 'Audit complet des protocoles, chiffrements et certificats' },
    { icon: 'bug_report', title: 'Détection de vulnérabilités', desc: 'Headers HTTP, injections, XSS, CSRF et plus' },
    { icon: 'dns', title: 'Prise d\'empreinte technologique', desc: 'Identification des frameworks, CMS, CDN utilisés' },
    { icon: 'vpn_key', title: 'Audit JWT', desc: 'Détection des tokens faibles, alg:none, secrets par défaut' },
    { icon: 'warning', title: 'Threat Intelligence', desc: 'Corrélation avec Shodan InternetDB et bases CVE' },
    { icon: 'picture_as_pdf', title: 'Rapport PDF', desc: 'Rapport complet avec score de risque et recommandations' },
  ];

  ngOnInit() {
    this.cyberscan.getPlans().subscribe({
      next: plans => { this.plans = plans; this.loading = false; },
      error: () => { this.loading = false; },
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
