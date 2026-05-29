import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

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
    CommonModule, RouterLink,
    MatButtonModule, MatIconModule,
    MatProgressSpinnerModule, MatProgressBarModule, MatSnackBarModule,
  ],
  template: `
    <div class="min-h-screen bg-[#0f172a] text-white">

      <!-- Header -->
      <div class="bg-[#1e293b] border-b border-slate-700 px-6 py-4 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <mat-icon class="text-cyan-400">school</mat-icon>
          <span class="font-semibold text-white">Sensibilisation NIS2</span>
        </div>
        @if (session()) {
          <div class="flex items-center gap-4">
            @if (level()) {
              <div class="flex items-center gap-2 bg-[#0f172a] px-3 py-1 rounded-full">
                <mat-icon class="text-yellow-400 text-sm">star</mat-icon>
                <span class="text-yellow-400 text-sm font-semibold">{{ level()!.label }}</span>
                <span class="text-slate-400 text-xs">{{ level()!.xp }} XP</span>
              </div>
            }
            <button mat-stroked-button (click)="logout()">
              <mat-icon>logout</mat-icon> Déconnexion
            </button>
          </div>
        }
      </div>

      <div class="max-w-4xl mx-auto p-6">

        <!-- Welcome -->
        @if (session()) {
          <div class="mb-6">
            <h1 class="text-2xl font-bold text-white">
              Bonjour{{ session()!.first_name ? ', ' + session()!.first_name : '' }} 👋
            </h1>
            <p class="text-slate-400 text-sm mt-1">Continuez votre parcours de sensibilisation</p>
          </div>
        }

        @if (loading()) {
          <div class="flex justify-center py-16"><mat-spinner diameter="48" /></div>
        }

        <!-- Badges earned -->
        @if (badges().length > 0) {
          <div class="mb-6">
            <h2 class="text-slate-300 text-sm font-semibold uppercase tracking-wide mb-3">Mes badges récents</h2>
            <div class="flex gap-2 flex-wrap">
              @for (badge of badges().slice(0, 6); track badge.id) {
                <div class="bg-[#1e293b] rounded-lg px-3 py-2 flex items-center gap-2 border border-slate-700"
                     [title]="badge.description || badge.name">
                  <span class="text-xl">{{ badge.icon }}</span>
                  <span class="text-slate-300 text-xs">{{ badge.name }}</span>
                </div>
              }
            </div>
          </div>
        }

        <!-- Enrolled programs -->
        @if (enrollments().length > 0) {
          <h2 class="text-slate-300 text-sm font-semibold uppercase tracking-wide mb-3">Mes programmes</h2>
          <div class="space-y-4 mb-8">
            @for (enroll of enrollments(); track enroll.id) {
              <div class="bg-[#1e293b] rounded-xl p-5 border border-slate-700">
                <div class="flex items-start justify-between mb-3">
                  <div>
                    <h3 class="text-white font-semibold">{{ programTitle(enroll.program_id) }}</h3>
                    <span class="px-2 py-0.5 rounded text-xs mt-1 inline-block"
                          [class]="statusClass(enroll.status)">
                      {{ statusLabel(enroll.status) }}
                    </span>
                  </div>
                  <div class="text-right">
                    <p class="text-2xl font-bold" [class]="pctColor(enroll.completion_pct)">
                      {{ enroll.completion_pct.toFixed(0) }}%
                    </p>
                    <p class="text-slate-500 text-xs">{{ enroll.xp_earned }} XP</p>
                  </div>
                </div>
                <mat-progress-bar mode="determinate" [value]="enroll.completion_pct" class="mb-3" />
                <a [routerLink]="['/awareness/module', enroll.id]" mat-raised-button color="primary">
                  {{ enroll.status === 'completed' ? 'Revoir' : 'Continuer' }}
                  <mat-icon>arrow_forward</mat-icon>
                </a>
                @if (enroll.status === 'completed') {
                  <a [routerLink]="['/awareness/module', enroll.id, 'certificate']" mat-stroked-button class="ml-2">
                    <mat-icon>verified</mat-icon> Mon attestation
                  </a>
                }
              </div>
            }
          </div>
        }

        <!-- Available programs to enroll -->
        @if (availablePrograms().length > 0) {
          <h2 class="text-slate-300 text-sm font-semibold uppercase tracking-wide mb-3">
            Programmes disponibles
          </h2>
          <div class="space-y-3">
            @for (prog of availablePrograms(); track prog.id) {
              <div class="bg-[#1e293b] rounded-xl p-5 border border-slate-700">
                <div class="flex items-start justify-between">
                  <div>
                    <h3 class="text-white font-semibold">{{ prog.title }}</h3>
                    <p class="text-slate-400 text-sm mt-1">{{ prog.description }}</p>
                    <p class="text-slate-500 text-xs mt-2">
                      {{ prog.modules.length }} modules · {{ prog.estimated_duration_minutes }} min
                    </p>
                  </div>
                  <button mat-raised-button color="accent" (click)="enroll(prog)" [disabled]="enrolling() === prog.id">
                    @if (enrolling() === prog.id) { <mat-spinner diameter="18" /> }
                    @else { <mat-icon>play_arrow</mat-icon> Commencer }
                  </button>
                </div>
              </div>
            }
          </div>
        }

        @if (!loading() && enrollments().length === 0 && availablePrograms().length === 0) {
          <div class="text-center py-16 text-slate-500">
            <mat-icon class="text-5xl mb-3">menu_book</mat-icon>
            <p>Aucun programme disponible pour le moment.</p>
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
      next: e => { this.enrollments.set(e); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
    this.svc.getMyLevel().subscribe({ next: l => this.level.set(l) });
    this.svc.getMyBadges().subscribe({ next: b => this.badges.set(b) });
  }

  availablePrograms(): AwarenessProgram[] {
    const enrolledIds = new Set(this.enrollments().map(e => e.program_id));
    return this.programs().filter(p => !enrolledIds.has(p.id));
  }

  programTitle(programId: number): string {
    return this.programs().find(p => p.id === programId)?.title ?? `Programme #${programId}`;
  }

  enroll(prog: AwarenessProgram) {
    this.enrolling.set(prog.id);
    this.svc.enroll(prog.id).subscribe({
      next: e => {
        this.enrollments.update(list => [...list, e]);
        this.enrolling.set(null);
        this.router.navigate(['/awareness/module', e.id]);
      },
      error: () => {
        this.enrolling.set(null);
        this.snack.open('Erreur lors de l\'inscription.', 'Fermer', { duration: 4000 });
      },
    });
  }

  logout() {
    this.svc.logout();
    this.router.navigate(['/awareness/login']);
  }

  statusLabel(status: string): string {
    const map: Record<string, string> = {
      pending: 'Non commencé', in_progress: 'En cours',
      completed: 'Complété', failed: 'Échoué',
    };
    return map[status] ?? status;
  }

  statusClass(status: string): string {
    const map: Record<string, string> = {
      pending: 'bg-slate-500/20 text-slate-400',
      in_progress: 'bg-blue-500/20 text-blue-400',
      completed: 'bg-green-500/20 text-green-400',
      failed: 'bg-red-500/20 text-red-400',
    };
    return map[status] ?? 'bg-slate-500/20 text-slate-400';
  }

  pctColor(pct: number): string {
    if (pct >= 80) return 'text-green-400';
    if (pct >= 40) return 'text-yellow-400';
    return 'text-slate-400';
  }
}
