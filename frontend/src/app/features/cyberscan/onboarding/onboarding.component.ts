import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Title } from '@angular/platform-browser';

import { CyberscanService, Plan } from '../services/cyberscan.service';

@Component({
    standalone: true,
    selector: 'app-onboarding',
    imports: [
        CommonModule, ReactiveFormsModule, RouterLink,
        MatButtonModule, MatIconModule, MatProgressSpinnerModule, MatSnackBarModule,
    ],
    templateUrl: './onboarding.component.html',
    styleUrl: './onboarding.component.css'
})
export class OnboardingComponent implements OnInit {
  private cyberscan = inject(CyberscanService);
  private fb = inject(FormBuilder);
  private router = inject(Router);
  private snack = inject(MatSnackBar);
  private title = inject(Title);

  plans = signal<Plan[]>([]);
  selectedPlan = signal<Plan | null>(null);
  checkoutLoading = signal(false);
  addingSite = signal(false);
  currentStep = signal(1);

  siteForm = this.fb.nonNullable.group({
    url: ['', [Validators.required, Validators.minLength(3)]],
    name: ['', Validators.required],
  });

  readonly steps = [
    { n: 1, label: 'Votre plan' },
    { n: 2, label: 'Premier site' },
    { n: 3, label: 'C\'est parti !' },
  ];

  ngOnInit() {
    this.title.setTitle('Démarrage — CyberScan');
    this.cyberscan.getPlans().subscribe({ next: p => this.plans.set(p) });
    // If user already has a subscription (e.g. coming back from Stripe success),
    // skip step 1 and go directly to step 2 (add first site).
    this.cyberscan.getMySubscription(true).subscribe({
      next: sub => { if (sub) this.currentStep.set(2); },
    });
  }

  selectPlan(plan: Plan) {
    this.selectedPlan.set(plan);
    this.checkoutLoading.set(true);
    this.cyberscan.createCheckout(plan.id).subscribe({
      next: res => {
        const url = res.checkout_url;
        if (url.startsWith('/') || url.includes(window.location.host)) {
          const path = url.startsWith('/') ? url : new URL(url).pathname;
          this.router.navigateByUrl(path);
        } else {
          window.location.href = url;
        }
      },
      error: () => this.checkoutLoading.set(false),
    });
  }

  addSiteAndScan() {
    if (this.siteForm.invalid) return;
    this.addingSite.set(true);
    const { url, name } = this.siteForm.getRawValue();
    const fullUrl = url.startsWith('http') ? url : `https://${url}`;
    this.cyberscan.createSite({ url: fullUrl, name }).subscribe({
      next: site => {
        this.addingSite.set(false);
        this.currentStep.set(3);
        this.cyberscan.triggerScan(site.id).subscribe({
          error: () => this.snack.open('Erreur lors du lancement du scan', 'Fermer', { duration: 4000 }),
        });
      },
      error: err => {
        this.addingSite.set(false);
        this.snack.open(err.error?.detail || 'Erreur', 'Fermer', { duration: 4000 });
      },
    });
  }

  goBack() {
    if (this.currentStep() === 2) {
      this.currentStep.set(1);
    } else {
      this.router.navigate(['/cyberscan/dashboard']);
    }
  }

  goToDashboard() {
    this.router.navigate(['/cyberscan/dashboard']);
  }

  formatPrice(cents: number): string {
    return (cents / 100).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });
  }

  planFeatures(plan: Plan): string[] {
    const features: string[] = [];
    features.push(`${plan.max_sites} site${plan.max_sites > 1 ? 's' : ''} surveillé${plan.max_sites > 1 ? 's' : ''}`);
    features.push(`Scan tous les ${plan.scan_interval_days} jours`);
    if (plan.scan_interval_days <= 7) features.push('Alertes email immédiates');
    if (plan.scan_interval_days <= 14) features.push('Rapports PDF inclus');
    if (plan.max_sites >= 5) features.push('Multi-sites & équipes');
    return features;
  }
}
