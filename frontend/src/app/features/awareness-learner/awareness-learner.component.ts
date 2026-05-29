import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';

import {
  AwarenessService,
  AwarenessProgram,
  AwarenessEnrollment,
  LearnerLevel,
  Badge,
} from '../cyberscan/services/awareness.service';

@Component({
  standalone: true,
  selector: 'app-awareness-learner',
  imports: [
    CommonModule,
    RouterLink,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTooltipModule,
  ],
  template: `
    <div class="min-h-screen bg-gray-950 text-white">
      <!-- Top bar -->
      <nav
        class="sticky top-0 z-40 flex items-center justify-between px-4 md:px-8 py-3 border-b border-white/5 backdrop-blur-md bg-gray-900/80"
      >
        <div class="flex items-center gap-2">
          <mat-icon class="text-cyan-400 !text-[1.4rem] !w-[1.4rem] !h-[1.4rem]">shield</mat-icon>
          <span class="font-bold text-white">Cyber<span class="text-cyan-400">Scan</span></span>
          <span
            class="px-2 py-0.5 text-[10px] font-bold rounded-full bg-cyan-500/15 text-cyan-400 border border-cyan-600/30 uppercase tracking-widest ml-1"
            >NIS2</span
          >
        </div>
        @if (session()) {
          <div class="flex items-center gap-3">
            @if (level()) {
              <div
                class="hidden sm:flex items-center gap-2 bg-gray-800 border border-gray-700 px-3 py-1.5 rounded-full"
              >
                <span class="text-yellow-400 text-sm">⭐</span>
                <span class="text-yellow-400 text-xs font-semibold">{{ level()!.label }}</span>
                <span class="text-gray-500 text-xs">{{ level()!.xp }} XP</span>
              </div>
            }
            <button
              mat-icon-button
              class="!text-gray-400 hover:!text-red-400"
              [matTooltip]="'Déconnexion'"
              (click)="logout()"
            >
              <mat-icon class="!text-[1.1rem]">logout</mat-icon>
            </button>
          </div>
        }
      </nav>

      <div class="max-w-3xl mx-auto p-4 md:p-8">
        <!-- Welcome -->
        @if (session()) {
          <div class="mb-8">
            <h1 class="text-2xl font-bold text-white">
              Bonjour{{ session()!.first_name ? ', ' + session()!.first_name : '' }} 👋
            </h1>
            <p class="text-gray-400 text-sm mt-1">
              Continuez votre parcours de sensibilisation cybersécurité
            </p>
          </div>
        }

        @if (loading()) {
          <div class="flex justify-center py-20"><mat-spinner diameter="40" /></div>
        }

        <!-- Level + Badges strip -->
        @if (!loading() && level()) {
          <div class="rounded-xl border border-gray-800 bg-gray-900 p-4 mb-6">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-4">
                <!-- Level ring -->
                <div class="relative w-14 h-14 shrink-0">
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
                      stroke="#eab308"
                      stroke-width="3"
                      stroke-linecap="round"
                      [attr.stroke-dasharray]="levelPct() + ' 100'"
                      stroke-dashoffset="0"
                    />
                  </svg>
                  <div class="absolute inset-0 flex items-center justify-center">
                    <span class="text-white font-bold text-sm">{{ level()!.level }}</span>
                  </div>
                </div>
                <div>
                  <p class="text-white font-semibold">{{ level()!.label }}</p>
                  <p class="text-gray-400 text-xs">
                    {{ level()!.xp }} XP
                    @if (level()!.next_level_xp) {
                      <span class="text-gray-600">/ {{ level()!.next_level_xp }} XP</span>
                    }
                  </p>
                </div>
              </div>
              @if (badges().length > 0) {
                <div class="flex gap-1.5 flex-wrap justify-end max-w-xs">
                  @for (badge of badges().slice(0, 5); track badge.id) {
                    <span class="text-lg" [matTooltip]="badge.name">{{ badge.icon }}</span>
                  }
                  @if (badges().length > 5) {
                    <span class="text-gray-500 text-xs self-end">+{{ badges().length - 5 }}</span>
                  }
                </div>
              }
            </div>
            @if (level()!.next_level_xp) {
              <div class="mt-3 h-1 bg-gray-800 rounded-full overflow-hidden">
                <div
                  class="h-full bg-yellow-500 rounded-full transition-all duration-500"
                  [style.width.%]="levelPct()"
                ></div>
              </div>
            }
          </div>
        }

        <!-- Active enrollments -->
        @if (enrollments().length > 0) {
          <h2 class="text-xs text-gray-400 font-semibold uppercase tracking-wider mb-3">
            Mes programmes
          </h2>
          <div class="flex flex-col gap-4 mb-8">
            @for (enroll of enrollments(); track enroll.id) {
              <div
                class="rounded-xl border border-gray-800 bg-gray-900 p-5 hover:border-gray-700 transition-colors"
              >
                <div class="flex items-start justify-between mb-3">
                  <div class="flex items-start gap-3">
                    <div
                      class="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center shrink-0 mt-0.5"
                    >
                      <mat-icon class="text-cyan-400 !text-[1.1rem]">menu_book</mat-icon>
                    </div>
                    <div>
                      <h3 class="text-white font-semibold">
                        {{ programTitle(enroll.program_id) }}
                      </h3>
                      <span
                        class="text-[0.65rem] font-semibold px-1.5 py-0.5 rounded-full border mt-1 inline-block"
                        [class]="enrollStatusClass(enroll.status)"
                      >
                        {{ enrollStatusLabel(enroll.status) }}
                      </span>
                    </div>
                  </div>
                  <div class="text-right ml-4 shrink-0">
                    <p class="text-2xl font-bold" [class]="pctColor(enroll.completion_pct)">
                      {{ enroll.completion_pct.toFixed(0) }}%
                    </p>
                    <p class="text-gray-500 text-xs">{{ enroll.xp_earned }} XP</p>
                  </div>
                </div>

                <div class="h-1.5 bg-gray-800 rounded-full overflow-hidden mb-4">
                  <div
                    class="h-full rounded-full transition-all duration-500"
                    [class]="pctBarColor(enroll.completion_pct)"
                    [style.width.%]="enroll.completion_pct"
                  ></div>
                </div>

                <div class="flex gap-2">
                  <a
                    [routerLink]="['/awareness/module', enroll.id]"
                    mat-flat-button
                    class="!rounded-xl !text-sm"
                    [class]="
                      enroll.status === 'completed'
                        ? '!bg-gray-700 hover:!bg-gray-600 !text-white'
                        : '!bg-cyan-600 hover:!bg-cyan-500 !text-white'
                    "
                  >
                    <mat-icon class="!text-[1rem]">{{
                      enroll.status === 'completed' ? 'replay' : 'play_arrow'
                    }}</mat-icon>
                    {{ enroll.status === 'completed' ? 'Revoir' : 'Continuer' }}
                  </a>
                  @if (enroll.status === 'completed') {
                    <a
                      [routerLink]="['/awareness/module', enroll.id]"
                      [queryParams]="{ view: 'certificate' }"
                      mat-stroked-button
                      class="!rounded-xl !border-green-700/50 !text-green-400 !text-sm"
                    >
                      <mat-icon class="!text-[1rem]">verified</mat-icon> Attestation
                    </a>
                  }
                </div>
              </div>
            }
          </div>
        }

        <!-- Available programs -->
        @if (availablePrograms().length > 0) {
          <h2 class="text-xs text-gray-400 font-semibold uppercase tracking-wider mb-3">
            Programmes disponibles
          </h2>
          <div class="flex flex-col gap-3">
            @for (prog of availablePrograms(); track prog.id) {
              <div
                class="rounded-xl border border-gray-800 bg-gray-900 p-5 hover:border-gray-700 transition-colors"
              >
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div class="flex items-start gap-3">
                    <div
                      class="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center shrink-0 mt-0.5"
                    >
                      <mat-icon class="text-cyan-400 !text-[1.1rem]">menu_book</mat-icon>
                    </div>
                    <div>
                      <h3 class="text-white font-semibold">{{ prog.title }}</h3>
                      <p class="text-gray-400 text-sm mt-0.5 line-clamp-2">
                        {{ prog.description }}
                      </p>
                      <div class="flex items-center gap-3 mt-2">
                        <span class="text-gray-500 text-xs flex items-center gap-1">
                          <mat-icon class="!text-[0.8rem]">view_module</mat-icon>
                          {{ prog.modules.length }} modules
                        </span>
                        <span class="text-gray-500 text-xs flex items-center gap-1">
                          <mat-icon class="!text-[0.8rem]">schedule</mat-icon>
                          {{ prog.estimated_duration_minutes }} min
                        </span>
                        <span class="text-gray-500 text-xs flex items-center gap-1">
                          <mat-icon class="!text-[0.8rem]">verified</mat-icon>
                          Attestation
                        </span>
                      </div>
                    </div>
                  </div>
                  <button
                    mat-flat-button
                    class="!rounded-xl !bg-cyan-600 hover:!bg-cyan-500 !text-white !text-sm shrink-0"
                    (click)="enroll(prog)"
                    [disabled]="enrolling() === prog.id"
                  >
                    @if (enrolling() === prog.id) {
                      <mat-spinner diameter="14" />
                    } @else {
                      <mat-icon class="!text-[1rem]">play_arrow</mat-icon>
                    }
                    Commencer
                  </button>
                </div>
              </div>
            }
          </div>
        }

        @if (!loading() && enrollments().length === 0 && availablePrograms().length === 0) {
          <div class="rounded-xl border border-gray-800 bg-gray-900/50 p-16 text-center">
            <mat-icon class="!text-[4rem] !w-[4rem] !h-[4rem] text-gray-700 mb-3"
              >menu_book</mat-icon
            >
            <p class="text-gray-400 font-medium">Aucun programme disponible</p>
            <p class="text-gray-600 text-sm mt-1">Contactez votre administrateur.</p>
          </div>
        }
      </div>
    </div>
  `,
})
export class AwarenessLearnerComponent implements OnInit {
  private svc = inject(AwarenessService);
  private router = inject(Router);
  private snack = inject(MatSnackBar);

  session = this.svc.learnerSession;
  programs = signal<AwarenessProgram[]>([]);
  enrollments = signal<AwarenessEnrollment[]>([]);
  level = signal<LearnerLevel | null>(null);
  badges = signal<Badge[]>([]);
  loading = signal(true);
  enrolling = signal<number | null>(null);

  ngOnInit() {
    this.loadAll();
  }

  loadAll() {
    this.svc.listPrograms().subscribe({ next: p => this.programs.set(p) });
    this.svc.listEnrollments().subscribe({
      next: e => {
        this.enrollments.set(e);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
    this.svc.getMyLevel().subscribe({ next: l => this.level.set(l) });
    this.svc.getMyBadges().subscribe({ next: b => this.badges.set(b) });
  }

  availablePrograms() {
    const ids = new Set(this.enrollments().map(e => e.program_id));
    return this.programs().filter(p => !ids.has(p.id));
  }

  programTitle(id: number) {
    return this.programs().find(p => p.id === id)?.title ?? `Programme #${id}`;
  }

  levelPct() {
    const l = this.level();
    if (!l || !l.next_level_xp) return 100;
    const thresholds = [0, 51, 151, 301, 501];
    const prev = thresholds[l.level - 1] ?? 0;
    return Math.min(((l.xp - prev) / (l.next_level_xp - prev)) * 100, 100);
  }

  enroll(prog: AwarenessProgram) {
    this.enrolling.set(prog.id);
    this.svc.enroll(prog.id).subscribe({
      next: e => {
        this.enrollments.update(l => [...l, e]);
        this.enrolling.set(null);
        this.router.navigate(['/awareness/module', e.id]);
      },
      error: () => {
        this.enrolling.set(null);
        this.snack.open("Erreur lors de l'inscription.", 'Fermer', { duration: 4000 });
      },
    });
  }

  logout() {
    this.svc.logout();
    this.router.navigate(['/awareness/login']);
  }

  enrollStatusLabel(s: string) {
    return (
      (
        {
          pending: 'Non commencé',
          in_progress: 'En cours',
          completed: 'Complété',
          failed: 'Échoué',
        } as Record<string, string>
      )[s] ?? s
    );
  }
  enrollStatusClass(s: string) {
    return (
      (
        {
          pending: 'text-gray-400 bg-gray-800/40 border-gray-700',
          in_progress: 'text-cyan-400 bg-cyan-900/20 border-cyan-700/40',
          completed: 'text-green-400 bg-green-900/20 border-green-700/40',
          failed: 'text-red-400 bg-red-900/20 border-red-700/40',
        } as Record<string, string>
      )[s] ?? ''
    );
  }
  pctColor(p: number) {
    return p >= 80 ? 'text-green-400' : p >= 40 ? 'text-yellow-400' : 'text-gray-400';
  }
  pctBarColor(p: number) {
    return p >= 80 ? 'bg-green-500' : p >= 40 ? 'bg-cyan-500' : 'bg-gray-600';
  }
}
