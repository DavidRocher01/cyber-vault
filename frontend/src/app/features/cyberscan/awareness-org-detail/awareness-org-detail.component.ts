import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';

import {
  AwarenessService,
  AwarenessOrganization,
  AwarenessLearner,
  CsvImportResult,
  OrgAdminDashboard,
  Nis2Report,
} from '../services/awareness.service';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
  standalone: true,
  selector: 'app-awareness-org-detail',
  imports: [
    CommonModule, RouterLink, FormsModule,
    MatButtonModule, MatCardModule, MatIconModule,
    MatInputModule, MatFormFieldModule, MatProgressSpinnerModule,
    MatSnackBarModule, MatTabsModule, MatChipsModule, MatTooltipModule,
    NavButtonsComponent,
  ],
  template: `
    <app-nav-buttons />

    <div class="min-h-screen bg-[#0f172a] text-white p-6">
      <div class="max-w-6xl mx-auto">

        <!-- Back -->
        <a routerLink="/cyberscan/awareness" class="flex items-center gap-1 text-slate-400 hover:text-white text-sm mb-6">
          <mat-icon class="text-base">arrow_back</mat-icon> Mes organisations
        </a>

        @if (loading()) {
          <div class="flex justify-center py-16"><mat-spinner diameter="48" /></div>
        }

        @if (!loading() && org()) {
          <div class="flex items-center gap-4 mb-6">
            <div class="bg-cyan-500/10 rounded-xl p-3">
              <mat-icon class="text-cyan-400 text-3xl">business</mat-icon>
            </div>
            <div>
              <h1 class="text-2xl font-bold text-white">{{ org()!.name }}</h1>
              <p class="text-slate-400 text-sm">{{ org()!.sector || 'Secteur non précisé' }} · {{ org()!.learner_count ?? 0 }}/{{ org()!.max_learners }} learners</p>
            </div>
          </div>

          <mat-tab-group animationDuration="200ms">

            <!-- ── Tab 1: Learners ── -->
            <mat-tab label="Learners">
              <div class="py-6">

                <!-- Add learner -->
                <div class="bg-[#1e293b] rounded-xl p-4 mb-6 border border-slate-700">
                  <h3 class="text-white font-semibold mb-3">Ajouter un learner</h3>
                  <div class="flex gap-3 flex-wrap">
                    <mat-form-field appearance="outline" class="flex-1 min-w-48">
                      <mat-label>Email</mat-label>
                      <input matInput [(ngModel)]="newEmail" type="email" placeholder="alice@entreprise.com" />
                    </mat-form-field>
                    <mat-form-field appearance="outline" class="flex-1 min-w-32">
                      <mat-label>Prénom (opt.)</mat-label>
                      <input matInput [(ngModel)]="newFirstName" />
                    </mat-form-field>
                    <mat-form-field appearance="outline" class="flex-1 min-w-32">
                      <mat-label>Département (opt.)</mat-label>
                      <input matInput [(ngModel)]="newDept" />
                    </mat-form-field>
                  </div>
                  <button mat-raised-button color="primary" (click)="addLearner()" [disabled]="addingLearner()">
                    @if (addingLearner()) { <mat-spinner diameter="18" /> } @else { Ajouter }
                  </button>
                </div>

                <!-- CSV Import -->
                <div class="bg-[#1e293b] rounded-xl p-4 mb-6 border border-slate-700">
                  <h3 class="text-white font-semibold mb-2">Import CSV</h3>
                  <p class="text-slate-400 text-xs mb-3">Colonnes : email, first_name, last_name, department, job_title</p>
                  <div class="flex items-center gap-3">
                    <input type="file" accept=".csv" #csvInput class="hidden" (change)="onCsvSelected($event)" />
                    <button mat-stroked-button (click)="csvInput.click()">
                      <mat-icon>upload_file</mat-icon> Choisir un fichier CSV
                    </button>
                    @if (csvFile) {
                      <span class="text-slate-300 text-sm">{{ csvFile.name }}</span>
                      <button mat-raised-button color="accent" (click)="uploadCsv()" [disabled]="importingCsv()">
                        @if (importingCsv()) { <mat-spinner diameter="18" /> } @else { Importer }
                      </button>
                    }
                  </div>
                  @if (csvResult()) {
                    <div class="mt-3 p-3 rounded-lg bg-[#0f172a] text-sm">
                      <span class="text-green-400">✓ {{ csvResult()!.created }} créés</span>
                      <span class="text-blue-400 ml-3">↻ {{ csvResult()!.updated }} mis à jour</span>
                      <span class="text-slate-400 ml-3">— {{ csvResult()!.skipped }} ignorés</span>
                      @if (csvResult()!.errors.length > 0) {
                        <div class="mt-2 text-red-400 text-xs">{{ csvResult()!.errors[0] }}</div>
                      }
                    </div>
                  }
                </div>

                <!-- Learner list -->
                @if (learners().length === 0) {
                  <p class="text-slate-500 text-center py-8">Aucun learner. Ajoutez-en un ou importez un CSV.</p>
                }
                <div class="space-y-2">
                  @for (learner of learners(); track learner.id) {
                    <div class="bg-[#1e293b] rounded-lg p-3 border border-slate-700/50 flex items-center justify-between">
                      <div>
                        <p class="text-white text-sm font-medium">
                          {{ learner.first_name || '' }} {{ learner.last_name || '' }}
                          <span class="text-slate-400 font-normal ml-2">{{ learner.email }}</span>
                        </p>
                        <p class="text-slate-500 text-xs">{{ learner.department || '—' }}</p>
                      </div>
                      <div class="flex items-center gap-2">
                        <span class="text-xs text-slate-500">{{ learner.last_login_at ? 'Connecté' : 'Jamais connecté' }}</span>
                        <button mat-icon-button [matTooltip]="'Envoyer un lien de connexion'" (click)="sendMagicLink(learner)">
                          <mat-icon class="text-cyan-400 text-sm">link</mat-icon>
                        </button>
                      </div>
                    </div>
                  }
                </div>
              </div>
            </mat-tab>

            <!-- ── Tab 2: Dashboard ── -->
            <mat-tab label="Dashboard">
              <div class="py-6">
                @if (loadingDash()) {
                  <div class="flex justify-center py-8"><mat-spinner diameter="32" /></div>
                }
                @if (dashboard()) {
                  <!-- Funnel -->
                  <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    <div class="bg-[#1e293b] rounded-xl p-4 text-center border border-slate-700">
                      <p class="text-2xl font-bold text-white">{{ dashboard()!.engagement.total_learners }}</p>
                      <p class="text-slate-400 text-xs">Learners totaux</p>
                    </div>
                    <div class="bg-[#1e293b] rounded-xl p-4 text-center border border-slate-700">
                      <p class="text-2xl font-bold text-blue-400">{{ dashboard()!.engagement.enrolled_learners }}</p>
                      <p class="text-slate-400 text-xs">Inscrits</p>
                    </div>
                    <div class="bg-[#1e293b] rounded-xl p-4 text-center border border-slate-700">
                      <p class="text-2xl font-bold text-yellow-400">{{ dashboard()!.engagement.active_learners }}</p>
                      <p class="text-slate-400 text-xs">Actifs</p>
                    </div>
                    <div class="bg-[#1e293b] rounded-xl p-4 text-center border border-slate-700">
                      <p class="text-2xl font-bold text-green-400">{{ dashboard()!.engagement.completed_learners }}</p>
                      <p class="text-slate-400 text-xs">Complétés</p>
                    </div>
                  </div>

                  <!-- Programmes -->
                  @if (dashboard()!.programs.length > 0) {
                    <h3 class="text-white font-semibold mb-3">Programmes</h3>
                    <div class="space-y-2 mb-6">
                      @for (prog of dashboard()!.programs; track prog.program_id) {
                        <div class="bg-[#1e293b] rounded-lg p-4 border border-slate-700">
                          <div class="flex justify-between items-center mb-2">
                            <p class="text-white text-sm font-medium">{{ prog.program_title }}</p>
                            <span class="text-sm font-bold" [class]="completionColor(prog.completion_rate)">
                              {{ prog.completion_rate.toFixed(0) }}%
                            </span>
                          </div>
                          <div class="w-full bg-slate-700 rounded-full h-1.5">
                            <div class="h-1.5 rounded-full bg-cyan-500 transition-all"
                                 [style.width.%]="prog.completion_rate"></div>
                          </div>
                          <p class="text-slate-400 text-xs mt-1">{{ prog.completed_learners }}/{{ prog.enrolled_learners }} complétés · moy. {{ prog.avg_completion_pct.toFixed(0) }}%</p>
                        </div>
                      }
                    </div>
                  }

                  <!-- At-risk -->
                  @if (dashboard()!.at_risk_learners.length > 0) {
                    <div class="bg-red-500/10 border border-red-500/30 rounded-xl p-4">
                      <h3 class="text-red-400 font-semibold mb-3 flex items-center gap-2">
                        <mat-icon>warning</mat-icon> Learners à risque ({{ dashboard()!.at_risk_learners.length }})
                      </h3>
                      <div class="space-y-2">
                        @for (r of dashboard()!.at_risk_learners; track r.learner_id) {
                          <div class="flex justify-between items-center text-sm">
                            <span class="text-white">{{ r.display_name }}</span>
                            <span class="text-slate-400">{{ r.days_inactive }}j inactif · {{ r.completion_pct.toFixed(0) }}%</span>
                          </div>
                        }
                      </div>
                    </div>
                  }
                }
              </div>
            </mat-tab>

            <!-- ── Tab 3: NIS2 ── -->
            <mat-tab label="NIS2">
              <div class="py-6">
                @if (loadingNis2()) {
                  <div class="flex justify-center py-8"><mat-spinner diameter="32" /></div>
                }
                @if (nis2()) {
                  <div class="flex items-center justify-between mb-6">
                    <div class="text-center">
                      <p class="text-5xl font-bold" [class]="nis2ScoreColor(nis2()!.global_score)">{{ nis2()!.global_score.toFixed(0) }}%</p>
                      <p class="text-slate-400 text-sm">Score de conformité NIS2</p>
                    </div>
                    <a [href]="pdfUrl()" download mat-raised-button color="primary">
                      <mat-icon>download</mat-icon> Rapport PDF
                    </a>
                  </div>

                  <div class="space-y-3">
                    @for (req of nis2()!.requirements; track req.article) {
                      <div class="bg-[#1e293b] rounded-lg p-4 border border-slate-700">
                        <div class="flex items-start justify-between">
                          <div>
                            <p class="text-slate-400 text-xs">{{ req.article }}</p>
                            <p class="text-white text-sm font-medium">{{ req.title }}</p>
                          </div>
                          <span class="px-2 py-0.5 rounded text-xs font-semibold"
                                [class]="nis2StatusClass(req.color)">
                            {{ req.status_label }}
                          </span>
                        </div>
                        <div class="mt-2 flex items-center gap-3">
                          <div class="flex-1 bg-slate-700 rounded-full h-1.5">
                            <div class="h-1.5 rounded-full transition-all"
                                 [class]="nis2BarColor(req.color)"
                                 [style.width.%]="Math.min(req.value, 100)"></div>
                          </div>
                          <span class="text-slate-300 text-xs w-16 text-right">{{ req.value.toFixed(0) }}% / {{ req.threshold }}%</span>
                        </div>
                      </div>
                    }
                  </div>
                }
              </div>
            </mat-tab>

          </mat-tab-group>
        }
      </div>
    </div>
  `,
})
export class AwarenessOrgDetailComponent implements OnInit {
  private svc = inject(AwarenessService);
  private route = inject(ActivatedRoute);
  private snack = inject(MatSnackBar);

  protected Math = Math;

  orgId = signal(0);
  org = signal<AwarenessOrganization | null>(null);
  learners = signal<AwarenessLearner[]>([]);
  dashboard = signal<OrgAdminDashboard | null>(null);
  nis2 = signal<Nis2Report | null>(null);
  csvResult = signal<CsvImportResult | null>(null);

  loading = signal(true);
  loadingDash = signal(false);
  loadingNis2 = signal(false);
  addingLearner = signal(false);
  importingCsv = signal(false);

  newEmail = '';
  newFirstName = '';
  newDept = '';
  csvFile: File | null = null;

  ngOnInit() {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.orgId.set(id);
    this.svc.getOrganization(id).subscribe({
      next: org => { this.org.set(org); this.loading.set(false); this.loadLearners(); this.loadDash(); this.loadNis2(); },
      error: () => this.loading.set(false),
    });
  }

  loadLearners() {
    this.svc.listLearners(this.orgId()).subscribe({ next: l => this.learners.set(l) });
  }

  loadDash() {
    this.loadingDash.set(true);
    this.svc.orgAdminDashboard(this.orgId()).subscribe({
      next: d => { this.dashboard.set(d); this.loadingDash.set(false); },
      error: () => this.loadingDash.set(false),
    });
  }

  loadNis2() {
    this.loadingNis2.set(true);
    this.svc.nis2Report(this.orgId()).subscribe({
      next: r => { this.nis2.set(r); this.loadingNis2.set(false); },
      error: () => this.loadingNis2.set(false),
    });
  }

  addLearner() {
    if (!this.newEmail.trim()) return;
    this.addingLearner.set(true);
    this.svc.createLearner(this.orgId(), {
      email: this.newEmail.trim(),
      first_name: this.newFirstName.trim() || undefined,
      department: this.newDept.trim() || undefined,
    }).subscribe({
      next: l => {
        this.learners.update(list => [...list, l]);
        this.newEmail = ''; this.newFirstName = ''; this.newDept = '';
        this.addingLearner.set(false);
        this.snack.open('Learner ajouté.', 'OK', { duration: 3000 });
      },
      error: (err) => {
        this.addingLearner.set(false);
        const msg = err.error?.detail || 'Erreur lors de l\'ajout.';
        this.snack.open(msg, 'Fermer', { duration: 4000 });
      },
    });
  }

  onCsvSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    this.csvFile = input.files?.[0] ?? null;
    this.csvResult.set(null);
  }

  uploadCsv() {
    if (!this.csvFile) return;
    this.importingCsv.set(true);
    this.svc.importCsv(this.orgId(), this.csvFile).subscribe({
      next: r => {
        this.csvResult.set(r);
        this.importingCsv.set(false);
        this.loadLearners();
        this.snack.open(`Import terminé : ${r.created} créés, ${r.updated} mis à jour.`, 'OK', { duration: 4000 });
      },
      error: () => {
        this.importingCsv.set(false);
        this.snack.open('Erreur lors de l\'import.', 'Fermer', { duration: 4000 });
      },
    });
  }

  sendMagicLink(learner: AwarenessLearner) {
    this.svc.requestMagicLink(learner.email, this.orgId()).subscribe({
      next: () => this.snack.open(`Lien envoyé à ${learner.email}`, 'OK', { duration: 3000 }),
      error: () => this.snack.open('Erreur envoi lien.', 'Fermer', { duration: 3000 }),
    });
  }

  pdfUrl(): string {
    return this.svc.nis2ReportPdfUrl(this.orgId());
  }

  completionColor(rate: number): string {
    if (rate >= 80) return 'text-green-400';
    if (rate >= 50) return 'text-yellow-400';
    return 'text-red-400';
  }

  nis2ScoreColor(score: number): string {
    if (score >= 80) return 'text-green-400';
    if (score >= 50) return 'text-yellow-400';
    return 'text-red-400';
  }

  nis2StatusClass(color: string): string {
    const m: Record<string, string> = {
      green: 'bg-green-500/20 text-green-400',
      yellow: 'bg-yellow-500/20 text-yellow-400',
      red: 'bg-red-500/20 text-red-400',
    };
    return m[color] ?? 'bg-slate-500/20 text-slate-400';
  }

  nis2BarColor(color: string): string {
    const m: Record<string, string> = {
      green: 'bg-green-500',
      yellow: 'bg-yellow-500',
      red: 'bg-red-500',
    };
    return m[color] ?? 'bg-slate-500';
  }
}
