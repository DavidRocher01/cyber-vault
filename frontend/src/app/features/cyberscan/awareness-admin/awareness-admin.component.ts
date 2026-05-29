import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';

import { AwarenessService, AwarenessOrganization } from '../services/awareness.service';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
  standalone: true,
  selector: 'app-awareness-admin',
  imports: [
    CommonModule, RouterLink, FormsModule,
    MatButtonModule, MatCardModule, MatDialogModule,
    MatIconModule, MatInputModule, MatFormFieldModule,
    MatProgressSpinnerModule, MatSnackBarModule, MatTooltipModule,
    NavButtonsComponent,
  ],
  template: `
    <app-nav-buttons />

    <div class="min-h-screen bg-[#0f172a] text-white p-6">
      <div class="max-w-5xl mx-auto">

        <!-- Header -->
        <div class="flex items-center justify-between mb-8">
          <div>
            <h1 class="text-2xl font-bold text-cyan-400">Sensibilisation NIS2</h1>
            <p class="text-slate-400 text-sm mt-1">Gérez vos organisations et pilotez la conformité</p>
          </div>
          <button mat-raised-button color="primary" (click)="showCreate = !showCreate">
            <mat-icon>add</mat-icon> Nouvelle organisation
          </button>
        </div>

        <!-- Create form -->
        @if (showCreate) {
          <div class="bg-[#1e293b] rounded-xl p-5 mb-6 border border-slate-700">
            <h3 class="text-white font-semibold mb-4">Créer une organisation</h3>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <mat-form-field appearance="outline" class="w-full">
                <mat-label>Nom</mat-label>
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
            <div class="flex gap-3 mt-2">
              <button mat-raised-button color="primary" (click)="createOrg()" [disabled]="creating()">
                @if (creating()) { <mat-spinner diameter="18" /> } @else { Créer }
              </button>
              <button mat-button (click)="showCreate = false">Annuler</button>
            </div>
          </div>
        }

        <!-- Loading -->
        @if (loading()) {
          <div class="flex justify-center py-16">
            <mat-spinner diameter="48" />
          </div>
        }

        <!-- Empty state -->
        @if (!loading() && orgs().length === 0) {
          <div class="text-center py-16 text-slate-500">
            <mat-icon class="text-5xl mb-3">business</mat-icon>
            <p>Aucune organisation. Créez-en une pour commencer.</p>
          </div>
        }

        <!-- Org cards -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          @for (org of orgs(); track org.id) {
            <div class="bg-[#1e293b] rounded-xl p-5 border border-slate-700 hover:border-cyan-500/50 transition-colors">
              <div class="flex items-start justify-between mb-3">
                <div>
                  <h3 class="font-semibold text-white">{{ org.name }}</h3>
                  <p class="text-slate-400 text-xs">{{ org.sector || 'Secteur non précisé' }}</p>
                </div>
                <span class="px-2 py-0.5 rounded text-xs"
                      [class]="org.is_active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'">
                  {{ org.is_active ? 'Actif' : 'Inactif' }}
                </span>
              </div>

              <div class="grid grid-cols-3 gap-3 mb-4">
                <div class="text-center bg-[#0f172a] rounded-lg py-2">
                  <p class="text-xl font-bold text-cyan-400">{{ org.learner_count ?? 0 }}</p>
                  <p class="text-xs text-slate-500">Learners</p>
                </div>
                <div class="text-center bg-[#0f172a] rounded-lg py-2">
                  <p class="text-xl font-bold text-blue-400">{{ org.active_enrollments ?? 0 }}</p>
                  <p class="text-xs text-slate-500">En cours</p>
                </div>
                <div class="text-center bg-[#0f172a] rounded-lg py-2">
                  <p class="text-xl font-bold" [class]="completionColor(org.completion_rate ?? 0)">
                    {{ (org.completion_rate ?? 0).toFixed(0) }}%
                  </p>
                  <p class="text-xs text-slate-500">Complétion</p>
                </div>
              </div>

              <div class="flex gap-2">
                <a [routerLink]="['/cyberscan/awareness/org', org.id]"
                   mat-stroked-button class="flex-1 text-center text-sm">
                  <mat-icon class="text-sm">people</mat-icon> Gérer
                </a>
                <a [routerLink]="['/cyberscan/awareness/org', org.id, 'dashboard']"
                   mat-stroked-button class="flex-1 text-center text-sm">
                  <mat-icon class="text-sm">dashboard</mat-icon> Dashboard
                </a>
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
      next: data => { this.orgs.set(data); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  createOrg() {
    if (!this.newName.trim()) return;
    this.creating.set(true);
    this.svc.createOrganization({
      name: this.newName.trim(),
      sector: this.newSector.trim() || undefined,
      max_learners: this.newMaxLearners,
    }).subscribe({
      next: org => {
        this.orgs.update(list => [...list, org]);
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

  completionColor(rate: number): string {
    if (rate >= 80) return 'text-green-400';
    if (rate >= 50) return 'text-yellow-400';
    return 'text-red-400';
  }
}
