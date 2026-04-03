import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatStepperModule } from '@angular/material/stepper';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Title } from '@angular/platform-browser';

import { CyberscanService, Plan } from '../services/cyberscan.service';

@Component({
  selector: 'app-onboarding',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule, RouterLink,
    MatButtonModule, MatIconModule, MatStepperModule,
    MatFormFieldModule, MatInputModule, MatProgressSpinnerModule, MatSnackBarModule,
  ],
  templateUrl: './onboarding.component.html',
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
  scanTriggered = signal(false);

  siteForm = this.fb.nonNullable.group({
    url: ['', [Validators.required, Validators.pattern(/^https?:\/\/.+/)]],
    name: ['', Validators.required],
  });

  ngOnInit() {
    this.title.setTitle('Démarrage — CyberScan');
    this.cyberscan.getPlans().subscribe({ next: p => this.plans.set(p) });
  }

  selectPlan(plan: Plan) {
    this.selectedPlan.set(plan);
    this.checkoutLoading.set(true);
    this.cyberscan.createCheckout(plan.id).subscribe({
      next: res => { window.location.href = res.checkout_url; },
      error: () => this.checkoutLoading.set(false),
    });
  }

  addSiteAndScan(stepper: any) {
    if (this.siteForm.invalid) return;
    this.addingSite.set(true);
    this.cyberscan.createSite(this.siteForm.getRawValue()).subscribe({
      next: site => {
        this.addingSite.set(false);
        stepper.next();
        this.cyberscan.triggerScan(site.id).subscribe({
          next: () => this.scanTriggered.set(true),
          error: () => this.snack.open('Erreur lors du lancement du scan', 'Fermer', { duration: 4000 }),
        });
      },
      error: err => {
        this.addingSite.set(false);
        this.snack.open(err.error?.detail || 'Erreur', 'Fermer', { duration: 4000 });
      },
    });
  }

  goToDashboard() {
    this.router.navigate(['/cyberscan/dashboard']);
  }

  formatPrice(cents: number): string {
    return (cents / 100).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });
  }
}
