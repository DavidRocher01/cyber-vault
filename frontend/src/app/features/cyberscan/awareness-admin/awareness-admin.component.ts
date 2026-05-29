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
        <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-8">
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
          <div class="rounded-xl border border-gray-800 bg-gray-900/50 p-16 text-center">
            <mat-icon class="!text-[4rem] !w-[4rem] !h-[4rem] text-gray-700 mb-3"
              >business</mat-icon
            >
            <p class="text-gray-400 font-medium">Aucune organisation</p>
            <p class="text-gray-600 text-sm mt-1">Créez une organisation pour commencer</p>
          </div>
        }

        <!-- Org cards -->
        <div class="flex flex-col gap-4">
          @for (org of orgs(); track org.id) {
            <div
              class="rounded-xl border border-gray-800 bg-gray-900 p-5 hover:border-gray-700 transition-colors"
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
                      >
                        {{ org.is_active ? 'Actif' : 'Inactif' }}
                      </span>
                    </div>
                    <p class="text-gray-500 text-xs mt-0.5">
                      {{ org.sector || 'Secteur non précisé' }}
                    </p>
                  </div>
                </div>

                <div class="flex items-center gap-6 shrink-0">
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
                  <div class="flex gap-2">
                    <a
                      [routerLink]="['/cyberscan/awareness/org', org.id]"
                      mat-stroked-button
                      class="!rounded-lg !border-gray-600 !text-gray-300 !text-xs"
                    >
                      <mat-icon class="!text-[1rem]">people</mat-icon> Gérer
                    </a>
                  </div>
                </div>
              </div>

              <div class="mt-4">
                <div class="h-1 bg-gray-800 rounded-full overflow-hidden">
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
