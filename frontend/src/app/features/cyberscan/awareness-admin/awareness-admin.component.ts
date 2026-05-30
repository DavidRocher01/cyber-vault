import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';

import { AwarenessService, AwarenessOrganization } from '../services/awareness.service';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
  standalone: true,
  selector: 'app-awareness-admin',
  imports: [
    CommonModule,
    RouterLink,
    FormsModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTooltipModule,
    NavButtonsComponent,
  ],
  template: `
    <app-nav-buttons />

    <div class="min-h-screen bg-gray-950 text-white p-4 md:p-8">
      <div class="max-w-5xl mx-auto">
        <!-- Header -->
        <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-6">
          <div>
            <div class="flex items-center gap-3 mb-1">
              <h1
                class="text-2xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent"
              >
                Sensibilisation NIS2
              </h1>
              <span
                class="px-2 py-0.5 text-[10px] font-bold rounded-full bg-cyan-500/15 text-cyan-400 border border-cyan-600/30 uppercase tracking-widest"
              >
                B2B
              </span>
            </div>
            <p class="text-gray-500 text-sm">
              Gérez vos organisations clientes et pilotez la conformité
            </p>
            <!-- Context chips -->
            <div class="flex items-center gap-2 mt-3 flex-wrap">
              <span
                class="inline-flex items-center gap-1.5 text-xs text-gray-400 bg-gray-800/60 border border-gray-700/60 px-2.5 py-1 rounded-full"
              >
                <mat-icon class="!text-[0.85rem] !w-[0.85rem] !h-[0.85rem] text-cyan-400"
                  >school</mat-icon
                >
                17 modules NIS2 Art. 21
              </span>
              <span
                class="inline-flex items-center gap-1.5 text-xs text-gray-400 bg-gray-800/60 border border-gray-700/60 px-2.5 py-1 rounded-full"
              >
                <mat-icon class="!text-[0.85rem] !w-[0.85rem] !h-[0.85rem] text-green-400"
                  >verified</mat-icon
                >
                Attestations PDF + QR
              </span>
              <span
                class="inline-flex items-center gap-1.5 text-xs text-gray-400 bg-gray-800/60 border border-gray-700/60 px-2.5 py-1 rounded-full"
              >
                <mat-icon class="!text-[0.85rem] !w-[0.85rem] !h-[0.85rem] text-amber-400"
                  >bar_chart</mat-icon
                >
                Suivi de conformité
              </span>
            </div>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <a
              routerLink="/cyberscan/awareness-pricing"
              mat-stroked-button
              class="!rounded-xl !border-gray-700 !text-gray-300 !text-sm"
            >
              <mat-icon>sell</mat-icon> Tarifs
            </a>
            <button
              mat-flat-button
              class="!rounded-xl !bg-cyan-600 hover:!bg-cyan-500 !text-white"
              (click)="showCreate = !showCreate"
            >
              <mat-icon>add</mat-icon> Nouvelle organisation
            </button>
          </div>
        </div>

        <!-- Create form -->
        @if (showCreate) {
          <div class="rounded-xl border border-cyan-500/20 bg-cyan-500/5 p-5 mb-6">
            <h3 class="text-white font-semibold mb-4 flex items-center gap-2">
              <mat-icon class="text-cyan-400 !text-[1.1rem]">add_business</mat-icon>
              Créer une organisation
            </h3>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
              <mat-form-field appearance="outline" class="w-full">
                <mat-label>Nom de l'organisation</mat-label>
                <input matInput [(ngModel)]="newName" placeholder="Acme Corp" />
              </mat-form-field>
              <mat-form-field appearance="outline" class="w-full">
                <mat-label>Secteur (optionnel)</mat-label>
                <input matInput [(ngModel)]="newSector" placeholder="Industrie, Santé..." />
              </mat-form-field>
              <mat-form-field appearance="outline" class="w-full">
                <mat-label>Nb max learners</mat-label>
                <input matInput type="number" [(ngModel)]="newMaxLearners" min="1" />
              </mat-form-field>
            </div>
            <div class="flex gap-2 mt-1">
              <button
                mat-flat-button
                class="!rounded-xl !bg-cyan-600 hover:!bg-cyan-500 !text-white"
                (click)="createOrg()"
                [disabled]="creating()"
              >
                @if (creating()) {
                  <mat-spinner diameter="14" />
                }
                Créer
              </button>
              <button
                mat-stroked-button
                class="!rounded-xl !border-gray-600 !text-gray-300"
                (click)="showCreate = false"
              >
                Annuler
              </button>
            </div>
          </div>
        }

        <!-- Loading -->
        @if (loading()) {
          <div class="flex justify-center py-20"><mat-spinner diameter="40" /></div>
        }

        <!-- Empty state -->
        @if (!loading() && orgs().length === 0) {
          <div
            class="rounded-2xl border border-dashed border-gray-700 bg-gray-900/30 p-12 text-center"
          >
            <div
              class="w-16 h-16 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center mx-auto mb-5"
            >
              <mat-icon class="text-cyan-400 !text-[2rem] !w-[2rem] !h-[2rem]">domain_add</mat-icon>
            </div>
            <h3 class="text-white font-semibold text-lg mb-2">Créez votre première organisation</h3>
            <p class="text-gray-400 text-sm mb-8 max-w-sm mx-auto leading-relaxed">
              Invitez vos équipes, suivez leur progression NIS2 et générez des attestations
              vérifiables en quelques minutes.
            </p>

            <!-- Steps -->
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8 max-w-2xl mx-auto text-left">
              @for (step of onboardingSteps; track step.label) {
                <div class="rounded-xl border border-gray-800 bg-gray-900/60 p-4 flex gap-3">
                  <div
                    class="w-7 h-7 rounded-full bg-cyan-500/15 border border-cyan-600/30 flex items-center justify-center text-xs font-bold text-cyan-400 shrink-0"
                  >
                    {{ $index + 1 }}
                  </div>
                  <div>
                    <p class="text-white text-sm font-medium">{{ step.label }}</p>
                    <p class="text-gray-500 text-xs mt-0.5">{{ step.desc }}</p>
                  </div>
                </div>
              }
            </div>

            <button
              mat-flat-button
              class="!rounded-xl !bg-cyan-600 hover:!bg-cyan-500 !text-white !px-6"
              (click)="showCreate = true"
            >
              <mat-icon>add</mat-icon> Créer ma première organisation
            </button>
          </div>
        }

        <!-- Org cards -->
        @if (!loading() && orgs().length > 0) {
          <!-- Summary bar -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
            <div class="rounded-xl border border-gray-800 bg-gray-900 p-4 text-center">
              <p class="text-2xl font-bold text-white">{{ orgs().length }}</p>
              <p class="text-xs text-gray-500 mt-0.5">
                Organisation{{ orgs().length > 1 ? 's' : '' }}
              </p>
            </div>
            <div class="rounded-xl border border-gray-800 bg-gray-900 p-4 text-center">
              <p class="text-2xl font-bold text-white">{{ totalLearners() }}</p>
              <p class="text-xs text-gray-500 mt-0.5">Learners actifs</p>
            </div>
            <div class="rounded-xl border border-gray-800 bg-gray-900 p-4 text-center">
              <p class="text-2xl font-bold" [class]="completionColor(avgCompletion())">
                {{ avgCompletion().toFixed(0) }}%
              </p>
              <p class="text-xs text-gray-500 mt-0.5">Complétion moy.</p>
            </div>
            <div class="rounded-xl border border-gray-800 bg-gray-900 p-4 text-center">
              <p class="text-2xl font-bold text-cyan-400">17</p>
              <p class="text-xs text-gray-500 mt-0.5">Modules NIS2</p>
            </div>
          </div>

          <div class="flex flex-col gap-4">
            @for (org of orgs(); track org.id) {
              <div
                class="rounded-xl border border-gray-800 bg-gray-900 p-5 hover:border-gray-700 transition-colors group"
              >
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div class="flex items-center gap-4 min-w-0">
                    <div
                      class="w-11 h-11 rounded-xl flex items-center justify-center shrink-0 bg-blue-500/10 border border-blue-500/20"
                    >
                      <mat-icon class="text-blue-400 !text-[1.3rem]">business</mat-icon>
                    </div>
                    <div class="min-w-0">
                      <div class="flex items-center gap-2 flex-wrap">
                        <h3 class="font-semibold text-white truncate">{{ org.name }}</h3>
                        <span
                          class="text-[0.65rem] font-semibold px-1.5 py-0.5 rounded-full border shrink-0"
                          [class]="
                            org.is_active
                              ? 'text-green-400 bg-green-900/20 border-green-700/40'
                              : 'text-gray-400 bg-gray-800/40 border-gray-700'
                          "
                          >{{ org.is_active ? 'Actif' : 'Inactif' }}</span
                        >
                      </div>
                      <p class="text-gray-500 text-xs mt-0.5">
                        {{ org.sector || 'Secteur non précisé' }}
                      </p>
                    </div>
                  </div>

                  <div class="flex items-center gap-5 shrink-0">
                    <div class="text-center hidden sm:block">
                      <p class="text-lg font-bold text-white">
                        {{ org.learner_count ?? 0
                        }}<span class="text-gray-600 text-sm font-normal"
                          >/{{ org.max_learners }}</span
                        >
                      </p>
                      <p class="text-[0.65rem] text-gray-500 uppercase tracking-wide">Learners</p>
                    </div>
                    <div class="text-center hidden sm:block">
                      <p
                        class="text-lg font-bold"
                        [class]="completionColor(org.completion_rate ?? 0)"
                      >
                        {{ (org.completion_rate ?? 0).toFixed(0) }}%
                      </p>
                      <p class="text-[0.65rem] text-gray-500 uppercase tracking-wide">Complétion</p>
                    </div>
                    <a
                      [routerLink]="['/cyberscan/awareness/org', org.id]"
                      mat-flat-button
                      class="!rounded-lg !bg-gray-800 group-hover:!bg-gray-700 !text-gray-300 !text-xs transition-colors"
                    >
                      <mat-icon class="!text-[1rem]">people</mat-icon> Gérer
                    </a>
                  </div>
                </div>

                <!-- Progress bar -->
                <div class="mt-4">
                  <div class="flex justify-between items-center mb-1">
                    <span class="text-[0.65rem] text-gray-600 uppercase tracking-wide"
                      >Progression NIS2</span
                    >
                    <span class="text-[0.65rem]" [class]="completionColor(org.completion_rate ?? 0)"
                      >{{ (org.completion_rate ?? 0).toFixed(0) }}%</span
                    >
                  </div>
                  <div class="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                    <div
                      class="h-full rounded-full transition-all duration-500"
                      [class]="completionBarColor(org.completion_rate ?? 0)"
                      [style.width.%]="org.completion_rate ?? 0"
                    ></div>
                  </div>
                </div>
              </div>
            }
          </div>
        }
      </div>
    </div>
  `,
})
export class AwarenessAdminComponent implements OnInit {
  private svc = inject(AwarenessService);
  private snack = inject(MatSnackBar);

  orgs = signal<AwarenessOrganization[]>([]);
  loading = signal(true);
  creating = signal(false);
  showCreate = false;
  newName = '';
  newSector = '';
  newMaxLearners = 10;

  readonly onboardingSteps = [
    {
      label: 'Créer une organisation',
      desc: 'Renseignez le nom, le secteur et le quota de learners.',
    },
    {
      label: 'Inviter les learners',
      desc: 'Import CSV ou ajout manuel, connexion par magic-link.',
    },
    {
      label: 'Suivre la conformité',
      desc: 'Tableau de bord, attestations PDF et score NIS2 en temps réel.',
    },
  ];

  totalLearners() {
    return this.orgs().reduce((s, o) => s + (o.learner_count ?? 0), 0);
  }

  avgCompletion() {
    const list = this.orgs();
    if (!list.length) return 0;
    return list.reduce((s, o) => s + (o.completion_rate ?? 0), 0) / list.length;
  }

  ngOnInit() {
    this.load();
  }

  load() {
    this.svc.listOrganizations().subscribe({
      next: data => {
        this.orgs.set(data);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  createOrg() {
    if (!this.newName.trim()) return;
    this.creating.set(true);
    this.svc
      .createOrganization({
        name: this.newName.trim(),
        sector: this.newSector.trim() || undefined,
        max_learners: this.newMaxLearners,
      })
      .subscribe({
        next: org => {
          this.orgs.update(l => [...l, org]);
          this.newName = '';
          this.newSector = '';
          this.newMaxLearners = 10;
          this.showCreate = false;
          this.creating.set(false);
          this.snack.open('Organisation créée.', 'OK', { duration: 3000 });
        },
        error: () => {
          this.creating.set(false);
          this.snack.open('Erreur lors de la création.', 'Fermer', { duration: 4000 });
        },
      });
  }

  completionColor(r: number) {
    return r >= 80 ? 'text-green-400' : r >= 50 ? 'text-yellow-400' : 'text-red-400';
  }
  completionBarColor(r: number) {
    return r >= 80 ? 'bg-green-500' : r >= 50 ? 'bg-yellow-500' : 'bg-red-500';
  }
}
