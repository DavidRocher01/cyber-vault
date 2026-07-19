import { Component, OnInit, inject, signal } from '@angular/core';
import { TitleCasePipe } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { Title } from '@angular/platform-browser';

import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import { PhishingStatusBadgeComponent } from '../phishing-status-badge/phishing-status-badge.component';
import { PhishingService, PhishingCampaign, PhishingTarget } from '../services/phishing.service';
import { PHISHING_SCENARIOS } from '../phishing/phishing.component';

const MAX_SCENARIOS_BY_PLAN: Record<string, number> = {
  express: 2,
  standard: 5,
  premium: 10,
  quarterly: 3,
  monthly: 7,
};

@Component({
  standalone: true,
  selector: 'app-phishing-campaign-edit',
  imports: [
    TitleCasePipe,
    RouterLink,
    ReactiveFormsModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatCheckboxModule,
    NavButtonsComponent,
    PhishingStatusBadgeComponent,
  ],
  templateUrl: './phishing-campaign-edit.component.html',
})
export class PhishingCampaignEditComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private fb = inject(FormBuilder);
  private phishingService = inject(PhishingService);
  private snack = inject(MatSnackBar);
  private title = inject(Title);

  campaignId = 0;
  campaign = signal<PhishingCampaign | null>(null);
  loading = signal(true);
  saving = signal(false);
  launching = signal(false);
  uploadingTargets = signal(false);
  targets = signal<PhishingTarget[]>([]);
  newTargetEmail = signal('');
  addingTarget = signal(false);

  readonly allScenarios = PHISHING_SCENARIOS;
  selectedScenarios = signal<Set<string>>(new Set());

  form = this.fb.group({
    name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(100)]],
    cgu_accepted: [false, Validators.requiredTrue],
    scheduled_at: [''],
    training_on_fail: [false],
    batch_size: [null as number | null, [Validators.min(1), Validators.max(1000)]],
  });

  ngOnInit() {
    this.campaignId = Number(this.route.snapshot.paramMap.get('id'));
    this.load();
  }

  load() {
    this.loading.set(true);
    this.phishingService.getCampaign(this.campaignId).subscribe({
      next: c => {
        // Redirect away if campaign is already running or done
        if (
          c.status === 'active' ||
          c.status === 'completed' ||
          c.status === 'sending' ||
          c.status === 'cancelled'
        ) {
          this.router.navigate(['/phishing/campaigns', this.campaignId]);
          return;
        }
        this.campaign.set(c);
        this.title.setTitle(`Configurer "${c.name}" | Rocher Cybersécurité`);
        const scheduledLocal = c.scheduled_at
          ? new Date(c.scheduled_at).toISOString().slice(0, 16)
          : '';
        this.form.patchValue({
          name: c.name,
          cgu_accepted: c.cgu_accepted,
          scheduled_at: scheduledLocal,
          training_on_fail: c.training_on_fail,
          batch_size: c.batch_size,
        });
        this.selectedScenarios.set(new Set(c.scenario_keys));
        this.reloadTargets();
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.snack.open('Campagne introuvable', 'Fermer', { duration: 3000 });
        this.router.navigate(['/phishing/campaigns']);
      },
    });
  }

  get maxScenarios(): number {
    return MAX_SCENARIOS_BY_PLAN[this.campaign()?.plan_tier ?? 'express'] ?? 2;
  }

  toggleScenario(id: string) {
    const set = new Set(this.selectedScenarios());
    if (set.has(id)) {
      set.delete(id);
    } else if (set.size < this.maxScenarios) {
      set.add(id);
    } else {
      this.snack.open(`Maximum ${this.maxScenarios} scénario(s) pour ce plan`, 'OK', {
        duration: 3000,
      });
    }
    this.selectedScenarios.set(set);
  }

  isScenarioSelected(id: string): boolean {
    return this.selectedScenarios().has(id);
  }

  get canLaunch(): boolean {
    const c = this.campaign();
    return (
      !!c &&
      (c.status === 'draft' || c.status === 'ready' || c.status === 'scheduled') &&
      this.selectedScenarios().size > 0 &&
      c.targets_count > 0 &&
      this.form.get('cgu_accepted')?.value === true &&
      this.form.get('name')?.valid === true
    );
  }

  get isScheduled(): boolean {
    const v = this.form.get('scheduled_at')?.value;
    if (!v) return false;
    return new Date(v) > new Date();
  }

  get scheduledAtIso(): string | undefined {
    const v = this.form.get('scheduled_at')?.value;
    if (!v) return undefined;
    const d = new Date(v);
    return isNaN(d.getTime()) ? undefined : d.toISOString();
  }

  get minScheduledAt(): string {
    const d = new Date();
    d.setMinutes(d.getMinutes() + 5);
    return d.toISOString().slice(0, 16);
  }

  save() {
    if (this.form.get('name')?.invalid) return;
    this.saving.set(true);
    this.phishingService
      .updateCampaign(this.campaignId, {
        name: this.form.value.name!,
        scenario_keys: Array.from(this.selectedScenarios()),
        cgu_accepted: this.form.value.cgu_accepted ?? false,
        scheduled_at: this.scheduledAtIso,
        training_on_fail: this.form.value.training_on_fail ?? false,
        ...(this.form.value.batch_size ? { batch_size: this.form.value.batch_size } : {}),
      })
      .subscribe({
        next: c => {
          this.campaign.set(c);
          this.saving.set(false);
          this.snack.open('Campagne enregistrée', 'OK', { duration: 3000 });
        },
        error: err => {
          this.saving.set(false);
          this.snack.open(err.error?.detail || 'Erreur lors de la sauvegarde', 'Fermer', {
            duration: 4000,
          });
        },
      });
  }

  launch() {
    this.launching.set(true);
    // Save first, then launch
    this.phishingService
      .updateCampaign(this.campaignId, {
        name: this.form.value.name!,
        scenario_keys: Array.from(this.selectedScenarios()),
        cgu_accepted: true,
        scheduled_at: this.scheduledAtIso,
        training_on_fail: this.form.value.training_on_fail ?? false,
        ...(this.form.value.batch_size ? { batch_size: this.form.value.batch_size } : {}),
      })
      .subscribe({
        next: () => {
          this.phishingService.launchCampaign(this.campaignId).subscribe({
            next: () => {
              this.launching.set(false);
              const msg = this.isScheduled ? 'Envoi planifié !' : 'Campagne lancée !';
              this.snack.open(msg, 'Voir', { duration: 5000 });
              this.router.navigate(['/phishing/campaigns', this.campaignId]);
            },
            error: err => {
              this.launching.set(false);
              this.snack.open(err.error?.detail || 'Erreur au lancement', 'Fermer', {
                duration: 4000,
              });
            },
          });
        },
        error: err => {
          this.launching.set(false);
          this.snack.open(err.error?.detail || 'Erreur lors de la sauvegarde', 'Fermer', {
            duration: 4000,
          });
        },
      });
  }

  onFileChange(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    this.uploadingTargets.set(true);
    // Merge par défaut : n'écrase pas les cibles déjà présentes.
    this.phishingService.uploadTargets(this.campaignId, file).subscribe({
      next: res => {
        this.uploadingTargets.set(false);
        input.value = '';
        const skipped = res.targets_skipped ? ` (${res.targets_skipped} doublon(s) ignoré(s))` : '';
        this.snack.open(`${res.targets_added} cible(s) ajoutée(s)${skipped}`, 'OK', {
          duration: 3500,
        });
        this.reloadTargets();
      },
      error: err => {
        this.uploadingTargets.set(false);
        input.value = '';
        this.snack.open(err.error?.detail || "Erreur lors de l'import", 'Fermer', {
          duration: 4000,
        });
      },
    });
  }

  private reloadTargets() {
    this.phishingService.getTargets(this.campaignId).subscribe({
      next: list => {
        this.targets.set(list);
        const c = this.campaign();
        if (c) this.campaign.set({ ...c, targets_count: list.length });
      },
    });
  }

  addTarget() {
    const email = this.newTargetEmail().trim();
    if (!email || this.addingTarget()) return;
    this.addingTarget.set(true);
    this.phishingService.addTarget(this.campaignId, { email }).subscribe({
      next: () => {
        this.addingTarget.set(false);
        this.newTargetEmail.set('');
        this.reloadTargets();
      },
      error: err => {
        this.addingTarget.set(false);
        this.snack.open(err.error?.detail || "Impossible d'ajouter la cible", 'Fermer', {
          duration: 4000,
        });
      },
    });
  }

  removeTarget(targetId: number) {
    this.phishingService.deleteTarget(this.campaignId, targetId).subscribe({
      next: () => this.reloadTargets(),
      error: err =>
        this.snack.open(err.error?.detail || 'Suppression impossible', 'Fermer', {
          duration: 4000,
        }),
    });
  }

  difficultyColor(d: string): string {
    switch (d) {
      case 'Difficile':
        return 'text-red-400';
      case 'Moyen':
        return 'text-yellow-400';
      default:
        return 'text-green-400';
    }
  }
}
