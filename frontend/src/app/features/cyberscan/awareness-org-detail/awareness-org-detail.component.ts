import { Component, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';

import {
  AwarenessService,
  AwarenessOrganization,
  AwarenessLearner,
  AwarenessProgram,
  CsvImportResult,
  OrgAdminDashboard,
  Nis2Report,
} from '../services/awareness.service';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
  standalone: true,
  selector: 'app-awareness-org-detail',
  imports: [
    RouterLink,
    FormsModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTooltipModule,
    NavButtonsComponent,
  ],
  template: `
    <app-nav-buttons />

    <div class="min-h-screen bg-gray-950 text-white p-4 md:p-8">
      <div class="max-w-5xl mx-auto">
        <!-- Back -->
        <a
          routerLink="/awareness-admin"
          class="inline-flex items-center gap-1.5 text-gray-400 hover:text-white text-sm mb-6 transition-colors"
        >
          <mat-icon class="!text-base">arrow_back</mat-icon> Mes organisations
        </a>

        @if (loading()) {
          <div class="flex justify-center py-20"><mat-spinner diameter="40" /></div>
        }

        @if (!loading() && org()) {
          <!-- Org header -->
          <div class="rounded-xl border border-gray-800 bg-gray-900 p-5 mb-6">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div class="flex items-center gap-4">
                <div
                  class="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center shrink-0"
                >
                  <mat-icon class="text-cyan-400 !text-[1.4rem]">business</mat-icon>
                </div>
                <div>
                  <h1
                    class="text-xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent"
                  >
                    {{ org()!.name }}
                  </h1>
                  <p class="text-gray-400 text-sm">{{ org()!.sector || 'Secteur non précisé' }}</p>
                </div>
              </div>
              <div class="flex items-center gap-6 text-center">
                <div>
                  <p class="text-xl font-bold text-white">
                    {{ org()!.learner_count ?? 0
                    }}<span class="text-gray-600 text-sm">/{{ org()!.max_learners }}</span>
                  </p>
                  <p class="text-[0.65rem] text-gray-500 uppercase tracking-wide">Learners</p>
                </div>
                <div>
                  <p
                    class="text-xl font-bold"
                    [class]="completionColor(org()!.completion_rate ?? 0)"
                  >
                    {{ (org()!.completion_rate ?? 0).toFixed(0) }}%
                  </p>
                  <p class="text-[0.65rem] text-gray-500 uppercase tracking-wide">Complétion</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Pill tabs -->
          <div class="flex gap-1 p-1 bg-gray-900 border border-gray-800 rounded-xl mb-6 w-fit">
            @for (tab of tabs; track tab.id) {
              <button
                type="button"
                class="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all"
                [class]="
                  activeTab() === tab.id
                    ? 'bg-gray-800 text-white shadow-sm'
                    : 'text-gray-500 hover:text-gray-300'
                "
                (click)="activeTab.set(tab.id)"
              >
                <mat-icon class="!text-[1rem] !w-[1rem] !h-[1rem]">{{ tab.icon }}</mat-icon>
                {{ tab.label }}
              </button>
            }
          </div>

          <!-- ── Tab Learners ── -->
          @if (activeTab() === 'learners') {
            <div class="flex flex-col gap-5">
              <!-- Add learner -->
              <div class="rounded-xl border border-gray-800 bg-gray-900 p-5">
                <h3 class="text-gray-400 text-xs font-semibold uppercase tracking-wider mb-3">
                  Ajouter manuellement
                </h3>
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-3">
                  <div class="sm:col-span-1">
                    <label class="block text-xs font-medium text-gray-400 mb-1.5">
                      Email <span class="text-red-400">*</span>
                    </label>
                    <input
                      type="email"
                      [(ngModel)]="newEmail"
                      (ngModelChange)="emailError.set(false)"
                      placeholder="alice@entreprise.com"
                      class="w-full bg-gray-800 border rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/30 transition-colors"
                      [class.border-gray-700]="!emailError()"
                      [class.border-red-500]="emailError()"
                    />
                    @if (emailError()) {
                      <p class="mt-1.5 text-xs text-red-400">L'email du learner est requis.</p>
                    }
                  </div>
                  <div>
                    <label class="block text-xs font-medium text-gray-400 mb-1.5">Prénom</label>
                    <input
                      type="text"
                      [(ngModel)]="newFirstName"
                      placeholder="Alice"
                      class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/30 transition-colors"
                    />
                  </div>
                  <div>
                    <label class="block text-xs font-medium text-gray-400 mb-1.5"
                      >Département</label
                    >
                    <input
                      type="text"
                      [(ngModel)]="newDept"
                      placeholder="IT, RH, Direction…"
                      class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/30 transition-colors"
                    />
                  </div>
                </div>
                <button
                  mat-flat-button
                  class="!rounded-xl !bg-cyan-600 hover:!bg-cyan-500 !text-white !text-sm"
                  (click)="addLearner()"
                  [disabled]="addingLearner()"
                >
                  @if (addingLearner()) {
                    <mat-spinner diameter="14" />
                  } @else {
                    <mat-icon class="!text-[1rem]">person_add</mat-icon>
                  }
                  Ajouter
                </button>
              </div>

              <!-- CSV import -->
              <div class="rounded-xl border border-gray-800 bg-gray-900 p-5">
                <h3 class="text-gray-400 text-xs font-semibold uppercase tracking-wider mb-1">
                  Import CSV
                </h3>
                <p class="text-gray-500 text-xs mb-3">
                  Colonnes : email, first_name, last_name, department, job_title
                </p>
                <div class="flex items-center gap-3 flex-wrap">
                  <input
                    type="file"
                    accept=".csv"
                    #csvInput
                    class="hidden"
                    (change)="onCsvSelected($event)"
                  />
                  <button
                    mat-stroked-button
                    class="!rounded-xl !border-gray-700 !text-gray-300 !text-sm"
                    (click)="csvInput.click()"
                  >
                    <mat-icon>upload_file</mat-icon> Choisir un fichier CSV
                  </button>
                  @if (csvFile) {
                    <span class="text-gray-300 text-sm">{{ csvFile.name }}</span>
                    <button
                      mat-flat-button
                      class="!rounded-xl !bg-purple-600 hover:!bg-purple-500 !text-white !text-sm"
                      (click)="uploadCsv()"
                      [disabled]="importingCsv()"
                    >
                      @if (importingCsv()) {
                        <mat-spinner diameter="14" />
                      }
                      Importer
                    </button>
                  }
                </div>
                @if (csvResult()) {
                  <div
                    class="mt-3 p-3 rounded-lg border border-gray-700 bg-gray-800 text-sm flex gap-4"
                  >
                    <span class="text-green-400 flex items-center gap-1"
                      ><mat-icon class="!text-sm">check_circle</mat-icon>
                      {{ csvResult()!.created }} créés</span
                    >
                    <span class="text-blue-400 flex items-center gap-1"
                      ><mat-icon class="!text-sm">sync</mat-icon> {{ csvResult()!.updated }} mis à
                      jour</span
                    >
                    <span class="text-gray-400 flex items-center gap-1"
                      ><mat-icon class="!text-sm">remove</mat-icon>
                      {{ csvResult()!.skipped }} ignorés</span
                    >
                  </div>
                }
              </div>

              <!-- Enroll all to program -->
              @if (programs().length > 0 && learners().length > 0) {
                <div class="rounded-xl border border-gray-800 bg-gray-900 p-5">
                  <h3 class="text-gray-400 text-xs font-semibold uppercase tracking-wider mb-3">
                    Inscrire tous les learners à un programme
                  </h3>
                  <div class="flex gap-3 flex-wrap items-center">
                    <select
                      class="flex-1 min-w-48 bg-gray-950 border border-gray-700 text-gray-300 text-sm rounded-lg px-3 py-2.5 focus:outline-none focus:border-cyan-500"
                      [(ngModel)]="selectedProgramId"
                    >
                      <option [ngValue]="null" disabled>Choisir un programme</option>
                      @for (prog of programs(); track prog.id) {
                        <option [ngValue]="prog.id">{{ prog.title }}</option>
                      }
                    </select>
                    <button
                      mat-flat-button
                      class="!rounded-xl !bg-cyan-600 hover:!bg-cyan-500 !text-white !text-sm shrink-0"
                      (click)="enrollAll()"
                      [disabled]="!selectedProgramId || enrollingAll()"
                    >
                      @if (enrollingAll()) {
                        <mat-spinner diameter="14" />
                      }
                      <mat-icon>group_add</mat-icon> Inscrire tous
                    </button>
                  </div>
                </div>
              }

              <!-- Learner list -->
              @if (learners().length === 0) {
                <div class="rounded-xl border border-gray-800 bg-gray-900/50 p-12 text-center">
                  <mat-icon class="!text-[3rem] !w-[3rem] !h-[3rem] text-gray-700 mb-2"
                    >people_outline</mat-icon
                  >
                  <p class="text-gray-500 text-sm">
                    Aucun learner. Ajoutez-en un ou importez un CSV.
                  </p>
                </div>
              }

              <div class="flex flex-col gap-2">
                @for (learner of learners(); track learner.id) {
                  <div
                    class="rounded-xl border border-gray-800 bg-gray-900 px-4 py-3 flex items-center justify-between hover:border-gray-700 transition-colors"
                  >
                    <div class="flex items-center gap-3 min-w-0">
                      <div
                        class="w-8 h-8 rounded-full bg-gray-800 border border-gray-700 flex items-center justify-center shrink-0 text-gray-400 text-xs font-semibold"
                      >
                        {{ (learner.first_name?.[0] ?? learner.email[0]).toUpperCase() }}
                      </div>
                      <div class="min-w-0">
                        <p class="text-white text-sm font-medium truncate">
                          {{ learner.first_name || '' }} {{ learner.last_name || '' }}
                          @if (!learner.first_name) {
                            <span class="text-gray-400 font-normal">{{ learner.email }}</span>
                          }
                        </p>
                        <p class="text-gray-500 text-xs">
                          {{ learner.first_name ? learner.email : ''
                          }}{{ learner.department ? ' · ' + learner.department : '' }}
                        </p>
                      </div>
                    </div>
                    <div class="flex items-center gap-3 shrink-0">
                      <span class="text-[0.65rem] text-gray-600">{{
                        learner.last_login_at ? 'Connecté' : 'Jamais connecté'
                      }}</span>
                      <button
                        mat-icon-button
                        class="!text-gray-600 hover:!text-cyan-400"
                        [matTooltip]="'Envoyer un lien de connexion'"
                        (click)="sendMagicLink(learner)"
                      >
                        <mat-icon class="!text-[1.1rem]">send</mat-icon>
                      </button>
                    </div>
                  </div>
                }
              </div>
            </div>
          }

          <!-- ── Tab Dashboard ── -->
          @if (activeTab() === 'dashboard') {
            <div>
              @if (loadingDash()) {
                <div class="flex justify-center py-12"><mat-spinner diameter="32" /></div>
              }
              @if (dashboard()) {
                <!-- Funnel -->
                <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                  @for (stat of funnelStats(); track stat.label) {
                    <div class="rounded-xl border border-gray-800 bg-gray-900 p-4 text-center">
                      <p class="text-2xl font-bold" [class]="stat.color">{{ stat.value }}</p>
                      <p class="text-[0.65rem] text-gray-500 uppercase tracking-wide mt-0.5">
                        {{ stat.label }}
                      </p>
                    </div>
                  }
                </div>

                <!-- Programme stats -->
                @if (dashboard()!.programs.length > 0) {
                  <h3 class="text-xs text-gray-400 font-semibold uppercase tracking-wider mb-3">
                    Programmes
                  </h3>
                  <div class="flex flex-col gap-3 mb-6">
                    @for (prog of dashboard()!.programs; track prog.program_id) {
                      <div class="rounded-xl border border-gray-800 bg-gray-900 p-4">
                        <div class="flex justify-between items-center mb-2">
                          <p class="text-white text-sm font-medium">{{ prog.program_title }}</p>
                          <span
                            class="text-sm font-bold"
                            [class]="completionColor(prog.completion_rate)"
                            >{{ prog.completion_rate.toFixed(0) }}%</span
                          >
                        </div>
                        <div class="h-1.5 bg-gray-800 rounded-full overflow-hidden mb-1">
                          <div
                            class="h-full rounded-full transition-all duration-500"
                            [class]="completionBarColor(prog.completion_rate)"
                            [style.width.%]="prog.completion_rate"
                          ></div>
                        </div>
                        <p class="text-gray-500 text-xs">
                          {{ prog.completed_learners }}/{{ prog.enrolled_learners }} complétés ·
                          moy. {{ prog.avg_completion_pct.toFixed(0) }}%
                        </p>
                      </div>
                    }
                  </div>
                }

                <!-- At-risk -->
                @if (dashboard()!.at_risk_learners.length > 0) {
                  <div class="rounded-xl border border-red-700/40 bg-red-900/10 p-4">
                    <h3 class="text-red-400 font-semibold text-sm mb-3 flex items-center gap-2">
                      <mat-icon class="!text-[1rem]">warning</mat-icon>
                      {{ dashboard()!.at_risk_learners.length }} learner(s) à risque
                    </h3>
                    <div class="flex flex-col gap-2">
                      @for (r of dashboard()!.at_risk_learners; track r.learner_id) {
                        <div
                          class="flex justify-between items-center text-sm py-1 border-b border-red-700/20 last:border-0"
                        >
                          <span class="text-gray-300"
                            >{{ r.display_name }}
                            <span class="text-gray-500 text-xs">{{
                              r.department ? '· ' + r.department : ''
                            }}</span></span
                          >
                          <span class="text-gray-400 text-xs"
                            >{{ r.days_inactive }}j inactif ·
                            {{ r.completion_pct.toFixed(0) }}%</span
                          >
                        </div>
                      }
                    </div>
                  </div>
                }
              }
            </div>
          }

          <!-- ── Tab NIS2 ── -->
          @if (activeTab() === 'nis2') {
            <div>
              @if (loadingNis2()) {
                <div class="flex justify-center py-12"><mat-spinner diameter="32" /></div>
              }
              @if (nis2()) {
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                  <div class="flex items-center gap-4">
                    <!-- Score gauge -->
                    <div class="relative w-20 h-20 shrink-0">
                      <svg viewBox="0 0 36 36" class="w-full h-full -rotate-90">
                        <circle
                          cx="18"
                          cy="18"
                          r="15.9"
                          fill="none"
                          stroke="#1f2937"
                          stroke-width="3"
                        />
                        <circle
                          cx="18"
                          cy="18"
                          r="15.9"
                          fill="none"
                          [attr.stroke]="nis2GaugeColor(nis2()!.global_score)"
                          stroke-width="3"
                          stroke-linecap="round"
                          [attr.stroke-dasharray]="nis2()!.global_score + ' 100'"
                          stroke-dashoffset="0"
                        />
                      </svg>
                      <div class="absolute inset-0 flex items-center justify-center">
                        <span
                          class="text-sm font-bold"
                          [class]="nis2ScoreColor(nis2()!.global_score)"
                          >{{ nis2()!.global_score.toFixed(0) }}%</span
                        >
                      </div>
                    </div>
                    <div>
                      <p class="text-white font-semibold">Score de conformité NIS2</p>
                      <p class="text-gray-400 text-sm">
                        {{ nis2()!.certificate_count }} attestation(s) délivrée(s)
                      </p>
                    </div>
                  </div>
                  <a
                    [href]="pdfUrl()"
                    download
                    mat-flat-button
                    class="!rounded-xl !bg-cyan-600 hover:!bg-cyan-500 !text-white !text-sm shrink-0"
                  >
                    <mat-icon>download</mat-icon> Rapport PDF
                  </a>
                </div>

                <div class="flex flex-col gap-3">
                  @for (req of nis2()!.requirements; track req.article) {
                    <div
                      class="rounded-xl border bg-gray-900 p-4"
                      [class]="
                        req.color === 'green'
                          ? 'border-green-700/40'
                          : req.color === 'yellow'
                            ? 'border-yellow-700/40'
                            : 'border-red-700/40'
                      "
                    >
                      <div class="flex items-start justify-between mb-2">
                        <div class="flex-1 min-w-0 mr-3">
                          <p class="text-gray-500 text-[0.65rem] uppercase tracking-wide">
                            {{ req.article }}
                          </p>
                          <p class="text-white text-sm font-medium">{{ req.title }}</p>
                        </div>
                        <span
                          class="text-[0.65rem] font-semibold px-1.5 py-0.5 rounded-full border shrink-0"
                          [class]="nis2StatusClass(req.color)"
                        >
                          {{ req.status_label }}
                        </span>
                      </div>
                      <div class="flex items-center gap-3">
                        <div class="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                          <div
                            class="h-full rounded-full transition-all duration-500"
                            [class]="nis2BarColor(req.color)"
                            [style.width.%]="Math.min(req.value, 100)"
                          ></div>
                        </div>
                        <span class="text-gray-400 text-xs w-20 text-right shrink-0"
                          >{{ req.value.toFixed(0) }}% / {{ req.threshold }}%</span
                        >
                      </div>
                    </div>
                  }
                </div>
              }
            </div>
          }
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

  tabs = [
    { id: 'learners', label: 'Learners', icon: 'people' },
    { id: 'dashboard', label: 'Dashboard', icon: 'dashboard' },
    { id: 'nis2', label: 'Rapport NIS2', icon: 'verified_user' },
  ];
  activeTab = signal('learners');

  orgId = signal(0);
  org = signal<AwarenessOrganization | null>(null);
  learners = signal<AwarenessLearner[]>([]);
  dashboard = signal<OrgAdminDashboard | null>(null);
  nis2 = signal<Nis2Report | null>(null);
  csvResult = signal<CsvImportResult | null>(null);

  programs = signal<AwarenessProgram[]>([]);
  selectedProgramId: number | null = null;

  loading = signal(true);
  loadingDash = signal(false);
  loadingNis2 = signal(false);
  addingLearner = signal(false);
  importingCsv = signal(false);
  enrollingAll = signal(false);
  emailError = signal(false);

  newEmail = '';
  newFirstName = '';
  newDept = '';
  csvFile: File | null = null;

  ngOnInit() {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.orgId.set(id);
    this.svc.listAdminPrograms().subscribe({ next: p => this.programs.set(p), error: () => {} });
    this.svc.getOrganization(id).subscribe({
      next: org => {
        this.org.set(org);
        this.loading.set(false);
        this.loadLearners();
        this.loadDash();
        this.loadNis2();
      },
      error: () => this.loading.set(false),
    });
  }

  loadLearners() {
    this.svc.listLearners(this.orgId()).subscribe({ next: l => this.learners.set(l) });
  }

  loadDash() {
    this.loadingDash.set(true);
    this.svc.orgAdminDashboard(this.orgId()).subscribe({
      next: d => {
        this.dashboard.set(d);
        this.loadingDash.set(false);
      },
      error: () => this.loadingDash.set(false),
    });
  }

  loadNis2() {
    this.loadingNis2.set(true);
    this.svc.nis2Report(this.orgId()).subscribe({
      next: r => {
        this.nis2.set(r);
        this.loadingNis2.set(false);
      },
      error: () => this.loadingNis2.set(false),
    });
  }

  addLearner() {
    if (!this.newEmail.trim()) {
      this.emailError.set(true);
      return;
    }
    this.emailError.set(false);
    this.addingLearner.set(true);
    this.svc
      .createLearner(this.orgId(), {
        email: this.newEmail.trim(),
        first_name: this.newFirstName.trim() || undefined,
        department: this.newDept.trim() || undefined,
      })
      .subscribe({
        next: l => {
          this.learners.update(list => [...list, l]);
          this.newEmail = '';
          this.newFirstName = '';
          this.newDept = '';
          this.addingLearner.set(false);
          this.snack.open('Learner ajouté.', 'OK', { duration: 3000 });
        },
        error: err => {
          this.addingLearner.set(false);
          this.snack.open(err.error?.detail || 'Erreur.', 'Fermer', { duration: 4000 });
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
        this.snack.open(`Import : ${r.created} créés, ${r.updated} mis à jour.`, 'OK', {
          duration: 4000,
        });
      },
      error: () => {
        this.importingCsv.set(false);
        this.snack.open('Erreur import.', 'Fermer', { duration: 4000 });
      },
    });
  }

  enrollAll() {
    if (!this.selectedProgramId) return;
    this.enrollingAll.set(true);
    this.svc.enrollAll(this.orgId(), this.selectedProgramId).subscribe({
      next: r => {
        this.enrollingAll.set(false);
        this.snack.open(
          `${r.enrolled} learner(s) inscrits, ${r.skipped} déjà inscrits. Invitations envoyées.`,
          'OK',
          { duration: 5000 }
        );
        this.selectedProgramId = null;
      },
      error: () => {
        this.enrollingAll.set(false);
        this.snack.open("Erreur lors de l'inscription.", 'Fermer', { duration: 4000 });
      },
    });
  }

  sendMagicLink(learner: AwarenessLearner) {
    this.svc.requestMagicLink(learner.email, this.orgId()).subscribe({
      next: () => this.snack.open(`Lien envoyé à ${learner.email}`, 'OK', { duration: 3000 }),
      error: () => this.snack.open('Erreur envoi lien.', 'Fermer', { duration: 3000 }),
    });
  }

  pdfUrl() {
    return this.svc.nis2ReportPdfUrl(this.orgId());
  }

  funnelStats() {
    const e = this.dashboard()!.engagement;
    return [
      { value: e.total_learners, label: 'Total', color: 'text-white' },
      { value: e.enrolled_learners, label: 'Inscrits', color: 'text-blue-400' },
      { value: e.active_learners, label: 'Actifs', color: 'text-yellow-400' },
      { value: e.completed_learners, label: 'Complétés', color: 'text-green-400' },
    ];
  }

  completionColor(r: number) {
    return r >= 80 ? 'text-green-400' : r >= 50 ? 'text-yellow-400' : 'text-red-400';
  }
  completionBarColor(r: number) {
    return r >= 80 ? 'bg-green-500' : r >= 50 ? 'bg-yellow-500' : 'bg-red-500';
  }
  nis2ScoreColor(s: number) {
    return s >= 80 ? 'text-green-400' : s >= 50 ? 'text-yellow-400' : 'text-red-400';
  }
  nis2GaugeColor(s: number) {
    return s >= 80 ? '#4ade80' : s >= 50 ? '#facc15' : '#f87171';
  }
  nis2StatusClass(c: string) {
    return c === 'green'
      ? 'text-green-400 bg-green-900/20 border-green-700/40'
      : c === 'yellow'
        ? 'text-yellow-400 bg-yellow-900/20 border-yellow-700/40'
        : 'text-red-400 bg-red-900/20 border-red-700/40';
  }
  nis2BarColor(c: string) {
    return c === 'green' ? 'bg-green-500' : c === 'yellow' ? 'bg-yellow-500' : 'bg-red-500';
  }
}
