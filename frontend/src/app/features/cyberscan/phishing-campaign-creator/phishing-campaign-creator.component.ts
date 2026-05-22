import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Title } from '@angular/platform-browser';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import { PhishingService, PhishingCampaign, DomainVerifyResult, LookalikeDomain, LOOKALIKE_TECHNIQUE_LABELS } from '../services/phishing.service';
import { PHISHING_SCENARIOS } from '../phishing/phishing.component';

export type WizardStep = 'plan' | 'info' | 'domain' | 'targets' | 'scenarios' | 'review';

export const STEPS: WizardStep[] = ['plan', 'info', 'domain', 'targets', 'scenarios', 'review'];

export const STEP_LABELS: Record<WizardStep, string> = {
  plan: 'Offre',
  info: 'Infos',
  domain: 'Domaine',
  targets: 'Cibles',
  scenarios: 'Scénarios',
  review: 'Validation',
};

export const PLAN_OPTIONS = [
  { id: 'express',    label: 'Express',     price: '800 € HT',    maxTargets: 50,  scenarios: 2,  highlight: false },
  { id: 'standard',  label: 'Standard',    price: '1 500 € HT',  maxTargets: 200, scenarios: 5,  highlight: true  },
  { id: 'premium',   label: 'Premium',     price: '2 500 € HT',  maxTargets: 500, scenarios: 10, highlight: false },
];

@Component({
  standalone: true,
  selector: 'app-phishing-campaign-creator',
  imports: [
    CommonModule, ReactiveFormsModule, RouterLink,
    MatButtonModule, MatIconModule, MatProgressSpinnerModule, MatSnackBarModule,
    NavButtonsComponent,
  ],
  templateUrl: './phishing-campaign-creator.component.html',
})
export class PhishingCampaignCreatorComponent implements OnInit {
  private service = inject(PhishingService);
  private snack = inject(MatSnackBar);
  private router = inject(Router);
  private fb = inject(FormBuilder);
  private title = inject(Title);

  // Wizard state
  currentStep = signal<WizardStep>('plan');
  steps = STEPS;
  stepLabels = STEP_LABELS;
  planOptions = PLAN_OPTIONS;
  readonly allScenarios = PHISHING_SCENARIOS;

  selectedPlan = signal<string>('standard');
  selectedScenarios = signal<Set<string>>(new Set());
  campaign = signal<PhishingCampaign | null>(null);
  domainVerifyResult = signal<DomainVerifyResult | null>(null);
  domainVerified = signal(false);
  lookalikeSuggestions = signal<LookalikeDomain[]>([]);
  loadingLookalikes = signal(false);
  selectedLookalikeDomain = signal<string | null>(null);
  readonly lookalikeTechLabels = LOOKALIKE_TECHNIQUE_LABELS;
  uploadedFile = signal<File | null>(null);
  uploading = signal(false);
  submitting = signal(false);
  verifying = signal(false);
  launching = signal(false);

  infoForm = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(100)]],
  });

  domainForm = this.fb.nonNullable.group({
    domain: ['', [Validators.required, Validators.pattern(/^[a-z0-9.-]+\.[a-z]{2,}$/i)]],
  });

  reviewForm = this.fb.nonNullable.group({
    cgu1: [false, Validators.requiredTrue],
    cgu2: [false, Validators.requiredTrue],
    cgu3: [false, Validators.requiredTrue],
  });

  get stepIndex(): number { return STEPS.indexOf(this.currentStep()); }
  get maxScenarios(): number { return PLAN_OPTIONS.find(p => p.id === this.selectedPlan())?.scenarios ?? 2; }
  get maxTargets(): number { return PLAN_OPTIONS.find(p => p.id === this.selectedPlan())?.maxTargets ?? 50; }

  ngOnInit() {
    this.title.setTitle('Nouvelle campagne de phishing | CyberScan');
  }

  goTo(step: WizardStep): void {
    const targetIndex = STEPS.indexOf(step);
    if (targetIndex <= this.stepIndex) {
      this.currentStep.set(step);
    }
  }

  next(): void {
    const next = STEPS[this.stepIndex + 1];
    if (next) this.currentStep.set(next);
  }

  prev(): void {
    const prev = STEPS[this.stepIndex - 1];
    if (prev) this.currentStep.set(prev);
  }

  // ── Step: info ──────────────────────────────────────────────────────────────

  async createAndNext(): Promise<void> {
    if (this.infoForm.invalid || this.submitting()) return;
    this.submitting.set(true);
    this.service.createCampaign(this.infoForm.getRawValue().name, this.selectedPlan()).subscribe({
      next: c => {
        this.campaign.set(c);
        this.submitting.set(false);
        this.next();
      },
      error: () => {
        this.submitting.set(false);
        this.snack.open('Erreur lors de la création', 'Fermer', { duration: 3000 });
      },
    });
  }

  // ── Step: domain ────────────────────────────────────────────────────────────

  requestVerify(): void {
    if (this.domainForm.invalid || this.verifying()) return;
    this.verifying.set(true);
    this.service.requestDomainVerify(this.domainForm.getRawValue().domain).subscribe({
      next: r => {
        this.domainVerifyResult.set(r);
        this.domainVerified.set(r.verified);
        this.verifying.set(false);
        if (r.verified) {
          this.loadLookalikes(r.domain);
        }
      },
      error: () => {
        this.verifying.set(false);
        this.snack.open('Erreur lors de la demande de vérification', 'Fermer', { duration: 3000 });
      },
    });
  }

  checkDns(): void {
    const domain = this.domainVerifyResult()?.domain;
    if (!domain) return;
    this.verifying.set(true);
    this.service.checkDomainVerify(domain).subscribe({
      next: r => {
        this.verifying.set(false);
        if (r.verified) {
          this.domainVerified.set(true);
          this.snack.open('Domaine vérifié !', 'Fermer', { duration: 3000 });
          this.loadLookalikes(domain);
        } else {
          this.snack.open('Enregistrement DNS non trouvé — réessayez dans quelques minutes', 'OK', { duration: 5000 });
        }
      },
      error: () => {
        this.verifying.set(false);
        this.snack.open('Erreur lors de la vérification DNS', 'Fermer', { duration: 3000 });
      },
    });
  }

  loadLookalikes(domain: string): void {
    this.loadingLookalikes.set(true);
    this.service.getLookalikeDomains(domain).subscribe({
      next: r => {
        this.lookalikeSuggestions.set(r.suggestions.slice(0, 12));
        this.loadingLookalikes.set(false);
      },
      error: () => {
        this.loadingLookalikes.set(false);
      },
    });
  }

  selectLookalike(domain: string): void {
    this.selectedLookalikeDomain.update(current => current === domain ? null : domain);
  }

  saveDomainAndNext(): void {
    const c = this.campaign();
    if (!c) return;
    const lookalike = this.selectedLookalikeDomain();
    this.service.updateCampaign(c.id, {
      domain: this.domainForm.getRawValue().domain,
      ...(lookalike ? { lookalike_domain: lookalike } : {}),
    }).subscribe({
      next: updated => {
        this.campaign.set(updated);
        this.next();
      },
    });
  }

  // ── Step: targets ────────────────────────────────────────────────────────────

  onFileChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files?.length) {
      this.uploadedFile.set(input.files[0]);
    }
  }

  uploadTargets(): void {
    const file = this.uploadedFile();
    const c = this.campaign();
    if (!file || !c || this.uploading()) return;
    this.uploading.set(true);
    this.service.uploadTargets(c.id, file).subscribe({
      next: r => {
        this.uploading.set(false);
        this.snack.open(`${r.targets_added} cibles importées`, 'Fermer', { duration: 3000 });
        this.campaign.update(cam => cam ? { ...cam, targets_count: r.targets_added } : cam);
        this.next();
      },
      error: (err) => {
        this.uploading.set(false);
        const msg = err?.error?.detail ?? 'Erreur lors de l\'import du CSV';
        this.snack.open(msg, 'Fermer', { duration: 5000 });
      },
    });
  }

  // ── Step: scenarios ──────────────────────────────────────────────────────────

  toggleScenario(id: string): void {
    this.selectedScenarios.update(set => {
      const next = new Set(set);
      if (next.has(id)) {
        next.delete(id);
      } else if (next.size < this.maxScenarios) {
        next.add(id);
      }
      return next;
    });
  }

  saveScenarios(): void {
    const c = this.campaign();
    if (!c || this.selectedScenarios().size === 0) return;
    this.service.updateCampaign(c.id, {
      scenario_keys: Array.from(this.selectedScenarios()),
    }).subscribe({
      next: updated => {
        this.campaign.set(updated);
        this.next();
      },
    });
  }

  // ── Step: review ─────────────────────────────────────────────────────────────

  launch(): void {
    if (this.reviewForm.invalid || this.launching()) return;
    const c = this.campaign();
    if (!c) return;
    this.launching.set(true);
    this.service.updateCampaign(c.id, { cgu_accepted: true }).subscribe({
      next: updated => {
        this.service.launchCampaign(updated.id).subscribe({
          next: () => {
            this.launching.set(false);
            this.snack.open('Campagne lancée !', 'Fermer', { duration: 3000 });
            this.router.navigate(['/cyberscan/phishing/campaigns']);
          },
          error: (err) => {
            this.launching.set(false);
            const msg = err?.error?.detail ?? 'Erreur lors du lancement';
            this.snack.open(msg, 'Fermer', { duration: 5000 });
          },
        });
      },
    });
  }
}
