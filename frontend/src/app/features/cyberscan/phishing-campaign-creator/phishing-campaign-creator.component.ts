import { Component, OnInit, inject, signal } from '@angular/core';
import { TitleCasePipe } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Title } from '@angular/platform-browser';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import {
  PhishingService,
  PhishingCampaign,
  LOOKALIKE_TECHNIQUE_LABELS,
  PHISHING_PLAN_CONFIG,
  planMaxScenarios,
  planMaxTargets,
} from '../services/phishing.service';
import { PHISHING_SCENARIOS } from '../services/phishing-scenarios';
import { extractApiError } from '../../../core/http-error';

export type WizardStep = 'plan' | 'info' | 'targets' | 'scenarios' | 'review';

export const STEPS: WizardStep[] = ['plan', 'info', 'targets', 'scenarios', 'review'];

export const STEP_LABELS: Record<WizardStep, string> = {
  plan: 'Offre',
  info: 'Infos',
  targets: 'Cibles',
  scenarios: 'Scénarios',
  review: 'Validation',
};

// Plans one-shot proposés dans l'assistant. Les plafonds (maxTargets/scenarios)
// proviennent de la source unique PHISHING_PLAN_CONFIG — pas de valeurs en dur.
export const PLAN_OPTIONS = [
  {
    id: 'express',
    label: 'Phishing Express',
    price: '990 € HT',
    maxTargets: PHISHING_PLAN_CONFIG['express'].maxTargets,
    scenarios: PHISHING_PLAN_CONFIG['express'].maxScenarios,
    highlight: false,
  },
  {
    id: 'standard',
    label: 'Phishing Standard',
    price: '1 890 € HT',
    maxTargets: PHISHING_PLAN_CONFIG['standard'].maxTargets,
    scenarios: PHISHING_PLAN_CONFIG['standard'].maxScenarios,
    highlight: true,
  },
  {
    id: 'premium',
    label: 'Phishing Premium',
    price: '2 990 € HT',
    maxTargets: PHISHING_PLAN_CONFIG['premium'].maxTargets,
    scenarios: PHISHING_PLAN_CONFIG['premium'].maxScenarios,
    highlight: false,
  },
];

@Component({
  standalone: true,
  selector: 'app-phishing-campaign-creator',
  imports: [
    TitleCasePipe,
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
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
  readonly lookalikeTechLabels = LOOKALIKE_TECHNIQUE_LABELS;
  uploadedFile = signal<File | null>(null);
  uploading = signal(false);
  submitting = signal(false);
  launching = signal(false);

  infoForm = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(100)]],
    domain: ['', [Validators.pattern(/^[a-z0-9.-]+\.[a-z]{2,}$/i)]],
  });

  reviewForm = this.fb.nonNullable.group({
    cgu1: [false, Validators.requiredTrue],
    cgu2: [false, Validators.requiredTrue],
    cgu3: [false, Validators.requiredTrue],
  });

  get stepIndex(): number {
    return STEPS.indexOf(this.currentStep());
  }
  get maxScenarios(): number {
    return planMaxScenarios(this.selectedPlan());
  }
  get maxTargets(): number {
    return planMaxTargets(this.selectedPlan());
  }

  ngOnInit() {
    this.title.setTitle('Nouvelle campagne de phishing | Rocher Cybersécurité');
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

  createAndNext(): void {
    if (this.infoForm.invalid || this.submitting()) return;
    this.submitting.set(true);
    const { name, domain } = this.infoForm.getRawValue();
    this.service.createCampaign(name, this.selectedPlan()).subscribe({
      next: c => {
        const patch = domain?.trim() ? { domain: domain.trim() } : {};
        if (Object.keys(patch).length) {
          this.service.updateCampaign(c.id, patch).subscribe({
            next: updated => {
              this.campaign.set(updated);
              this.submitting.set(false);
              this.next();
            },
            error: () => {
              this.campaign.set(c);
              this.submitting.set(false);
              this.next();
            },
          });
        } else {
          this.campaign.set(c);
          this.submitting.set(false);
          this.next();
        }
      },
      error: () => {
        this.submitting.set(false);
        this.snack.open('Erreur lors de la création', 'Fermer', { duration: 3000 });
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
        this.campaign.update(cam => (cam ? { ...cam, targets_count: r.targets_added } : cam));
        this.next();
      },
      error: err => {
        this.uploading.set(false);
        const msg = extractApiError(err, "Erreur lors de l'import du CSV");
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
    this.service
      .updateCampaign(c.id, {
        scenario_keys: Array.from(this.selectedScenarios()),
      })
      .subscribe({
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
    this.service.launchWithCgu(c.id).subscribe({
      next: () => {
        this.launching.set(false);
        this.snack.open('Campagne lancée !', 'Fermer', { duration: 3000 });
        this.router.navigate(['/phishing/campaigns']);
      },
      error: err => {
        this.launching.set(false);
        const msg = extractApiError(err, 'Erreur lors du lancement');
        this.snack.open(msg, 'Fermer', { duration: 5000 });
      },
    });
  }
}
