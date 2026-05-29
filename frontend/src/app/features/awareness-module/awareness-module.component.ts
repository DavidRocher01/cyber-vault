import { Component, inject, OnDestroy, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatRadioModule } from '@angular/material/radio';
import { MatCheckboxModule } from '@angular/material/checkbox';

import {
  AwarenessService,
  LearnerDashboard,
  ModuleProgress,
  AwarenessModule as AModule,
  QuizStart,
  QuizResult,
} from '../cyberscan/services/awareness.service';

type PageView = 'dashboard' | 'content' | 'quiz' | 'quiz-result' | 'certificate';

@Component({
  standalone: true,
  selector: 'app-awareness-module',
  imports: [
    CommonModule, RouterLink, FormsModule,
    MatButtonModule, MatIconModule, MatProgressSpinnerModule,
    MatProgressBarModule, MatSnackBarModule, MatRadioModule, MatCheckboxModule,
  ],
  template: `
    <div class="min-h-screen bg-[#0f172a] text-white">

      <!-- Top bar -->
      <div class="bg-[#1e293b] border-b border-slate-700 px-4 py-3 flex items-center gap-4">
        <a routerLink="/awareness" mat-icon-button>
          <mat-icon class="text-slate-400">arrow_back</mat-icon>
        </a>
        @if (dashboard()) {
          <div class="flex-1">
            <p class="text-white text-sm font-semibold">{{ dashboard()!.program.title }}</p>
            <mat-progress-bar mode="determinate" [value]="dashboard()!.enrollment.completion_pct" class="mt-1" />
          </div>
          <span class="text-cyan-400 text-sm font-bold">{{ dashboard()!.enrollment.completion_pct.toFixed(0) }}%</span>
        }
      </div>

      @if (loading()) {
        <div class="flex justify-center py-16"><mat-spinner diameter="48" /></div>
      }

      @if (!loading() && dashboard()) {

        <!-- ── Module list view ── -->
        @if (view() === 'dashboard') {
          <div class="max-w-2xl mx-auto p-6">
            <h2 class="text-white font-semibold mb-4">Modules du programme</h2>
            <div class="space-y-3">
              @for (mp of dashboard()!.modules_progress; track mp.module_id) {
                <button class="w-full text-left bg-[#1e293b] rounded-xl p-4 border transition-colors flex items-center gap-4"
                        [class]="moduleCardClass(mp.status)"
                        (click)="openModule(mp)"
                        [disabled]="mp.status === 'not_started' && !isNextModule(mp)">
                  <div class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                       [class]="moduleIconBg(mp.status)">
                    <mat-icon class="text-sm">{{ moduleIcon(mp.status) }}</mat-icon>
                  </div>
                  <div class="flex-1">
                    <p class="text-white text-sm font-medium">{{ mp.title }}</p>
                    @if (mp.time_spent_seconds > 0) {
                      <p class="text-slate-500 text-xs">{{ formatTime(mp.time_spent_seconds) }} passé</p>
                    }
                  </div>
                  @if (mp.best_quiz_score !== null) {
                    <span class="text-xs px-2 py-0.5 rounded bg-green-500/20 text-green-400">
                      {{ mp.best_quiz_score }}%
                    </span>
                  }
                </button>
              }
            </div>

            @if (dashboard()!.enrollment.status === 'completed') {
              <div class="mt-6 p-5 bg-green-500/10 border border-green-500/30 rounded-xl text-center">
                <mat-icon class="text-green-400 text-4xl">verified</mat-icon>
                <p class="text-green-400 font-semibold mt-2">Programme complété !</p>
                <button mat-raised-button color="primary" class="mt-3" (click)="view.set('certificate')">
                  Voir mon attestation
                </button>
              </div>
            }
          </div>
        }

        <!-- ── Content view ── -->
        @if (view() === 'content' && currentModule()) {
          <div class="max-w-2xl mx-auto p-6">
            <div class="flex items-center gap-3 mb-6">
              <button mat-icon-button (click)="view.set('dashboard')">
                <mat-icon>close</mat-icon>
              </button>
              <h2 class="text-xl font-bold text-white">{{ currentModule()!.title }}</h2>
            </div>

            <!-- Markdown content rendered as HTML (simple approach) -->
            @if (currentModule()!.content_markdown) {
              <div class="prose prose-invert prose-sm max-w-none text-slate-300 leading-relaxed"
                   [innerHTML]="renderMarkdown(currentModule()!.content_markdown!)">
              </div>
            } @else {
              <p class="text-slate-400">Contenu non disponible.</p>
            }

            <div class="mt-8 flex gap-3">
              @if (currentModule()!.has_quiz) {
                <button mat-raised-button color="primary" (click)="startQuiz()">
                  <mat-icon>quiz</mat-icon> Passer le quiz
                </button>
              } @else {
                <button mat-raised-button color="primary" (click)="completeWithoutQuiz()" [disabled]="completing()">
                  @if (completing()) { <mat-spinner diameter="18" /> } @else {
                    <mat-icon>check</mat-icon> Marquer comme terminé
                  }
                </button>
              }
              <button mat-stroked-button (click)="view.set('dashboard')">Retour</button>
            </div>
          </div>
        }

        <!-- ── Quiz view ── -->
        @if (view() === 'quiz' && quizData()) {
          <div class="max-w-2xl mx-auto p-6">
            <div class="flex items-center gap-3 mb-6">
              <button mat-icon-button (click)="view.set('content')">
                <mat-icon>arrow_back</mat-icon>
              </button>
              <div>
                <h2 class="text-xl font-bold text-white">Quiz — {{ currentModule()?.title }}</h2>
                <p class="text-slate-400 text-sm">Tentative {{ quizData()!.attempt_number }}</p>
              </div>
            </div>

            <div class="space-y-6">
              @for (q of quizData()!.questions; track q.id; let qi = $index) {
                <div class="bg-[#1e293b] rounded-xl p-5 border border-slate-700">
                  <p class="text-white font-medium mb-4">{{ qi + 1 }}. {{ q.text }}</p>

                  @if (q.type === 'single_choice' || q.type === 'true_false') {
                    <div class="space-y-2">
                      @for (a of q.answers; track a.id) {
                        <label class="flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors"
                               [class]="selectedAnswers()[q.id]?.[0] === a.id ? 'bg-cyan-500/20 border border-cyan-500/50' : 'bg-[#0f172a] border border-slate-700 hover:border-slate-600'">
                          <input type="radio" [name]="'q_' + q.id" [value]="a.id"
                                 class="text-cyan-500"
                                 (change)="selectAnswer(q.id, a.id, false)" />
                          <span class="text-slate-300 text-sm">{{ a.text }}</span>
                        </label>
                      }
                    </div>
                  }

                  @if (q.type === 'multiple_choice') {
                    <div class="space-y-2">
                      @for (a of q.answers; track a.id) {
                        <label class="flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors"
                               [class]="isSelected(q.id, a.id) ? 'bg-cyan-500/20 border border-cyan-500/50' : 'bg-[#0f172a] border border-slate-700 hover:border-slate-600'">
                          <mat-checkbox [checked]="isSelected(q.id, a.id)"
                                        (change)="selectAnswer(q.id, a.id, true)" />
                          <span class="text-slate-300 text-sm">{{ a.text }}</span>
                        </label>
                      }
                    </div>
                  }
                </div>
              }
            </div>

            <div class="mt-6">
              <button mat-raised-button color="primary" (click)="submitQuiz()" [disabled]="submittingQuiz()">
                @if (submittingQuiz()) { <mat-spinner diameter="18" /> } @else { Soumettre }
              </button>
            </div>
          </div>
        }

        <!-- ── Quiz result view ── -->
        @if (view() === 'quiz-result' && quizResult()) {
          <div class="max-w-2xl mx-auto p-6">
            <div class="text-center mb-8">
              <div class="text-6xl font-bold mb-2"
                   [class]="quizResult()!.result === 'passed' ? 'text-green-400' : 'text-red-400'">
                {{ quizResult()!.score }}%
              </div>
              <p class="text-xl font-semibold"
                 [class]="quizResult()!.result === 'passed' ? 'text-green-400' : 'text-red-400'">
                {{ quizResult()!.result === 'passed' ? '✓ Réussi !' : '✗ Échec' }}
              </p>
              <p class="text-slate-400 text-sm mt-1">Seuil : {{ quizResult()!.passing_score }}%</p>
            </div>

            <!-- Details -->
            <div class="space-y-3 mb-6">
              @for (d of quizResult()!.details; track d.question_id) {
                <div class="bg-[#1e293b] rounded-lg p-3 border"
                     [class]="d.is_correct ? 'border-green-500/30' : 'border-red-500/30'">
                  <div class="flex items-center gap-2 mb-1">
                    <mat-icon class="text-sm" [class]="d.is_correct ? 'text-green-400' : 'text-red-400'">
                      {{ d.is_correct ? 'check_circle' : 'cancel' }}
                    </mat-icon>
                    <span class="text-slate-300 text-sm">{{ d.is_correct ? 'Correct' : 'Incorrect' }}</span>
                  </div>
                  @if (d.explanation) {
                    <p class="text-slate-400 text-xs">{{ d.explanation }}</p>
                  }
                </div>
              }
            </div>

            <div class="flex gap-3">
              @if (quizResult()!.result === 'passed') {
                <button mat-raised-button color="primary" (click)="view.set('dashboard')">
                  Continuer <mat-icon>arrow_forward</mat-icon>
                </button>
              } @else {
                <button mat-raised-button (click)="retryQuiz()">
                  <mat-icon>replay</mat-icon> Réessayer
                </button>
                <button mat-stroked-button (click)="view.set('content')">Relire le module</button>
              }
            </div>
          </div>
        }

        <!-- ── Certificate view ── -->
        @if (view() === 'certificate') {
          <div class="max-w-2xl mx-auto p-6 text-center">
            @if (certLoading()) {
              <mat-spinner diameter="48" class="mx-auto" />
            } @else if (certificate()) {
              <div class="bg-[#1e293b] rounded-2xl p-8 border border-cyan-500/30">
                <mat-icon class="text-cyan-400 text-6xl">verified</mat-icon>
                <h2 class="text-2xl font-bold text-white mt-4">Attestation de complétion</h2>
                <p class="text-slate-400 mt-2">{{ dashboard()!.program.title }}</p>
                <p class="text-slate-500 text-sm mt-1">Référence : {{ certificate()!.public_id }}</p>
                <p class="text-slate-500 text-sm">Émise le {{ certificate()!.issued_at | date:'dd/MM/yyyy' }}</p>
                @if (certificate()!.expires_at) {
                  <p class="text-slate-500 text-sm">Valable jusqu'au {{ certificate()!.expires_at | date:'dd/MM/yyyy' }}</p>
                }
                <div class="mt-6 flex gap-3 justify-center">
                  <a [href]="certDownloadUrl()" download mat-raised-button color="primary">
                    <mat-icon>download</mat-icon> Télécharger le PDF
                  </a>
                  <button mat-stroked-button (click)="view.set('dashboard')">Retour</button>
                </div>
              </div>
            } @else {
              <p class="text-slate-400">Attestation non disponible.</p>
              <button mat-stroked-button class="mt-4" (click)="view.set('dashboard')">Retour</button>
            }
          </div>
        }
      }
    </div>
  `,
})
export class AwarenessModuleComponent implements OnInit, OnDestroy {
  private svc = inject(AwarenessService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private snack = inject(MatSnackBar);

  enrollmentId = signal(0);
  dashboard = signal<LearnerDashboard | null>(null);
  currentModuleId = signal<number | null>(null);
  quizData = signal<QuizStart | null>(null);
  quizResult = signal<QuizResult | null>(null);
  certificate = signal<any>(null);

  view = signal<PageView>('dashboard');
  loading = signal(true);
  completing = signal(false);
  submittingQuiz = signal(false);
  certLoading = signal(false);

  selectedAnswers = signal<Record<string, string[]>>({});

  private heartbeatInterval: ReturnType<typeof setInterval> | null = null;
  private moduleStartTime = 0;

  ngOnInit() {
    const id = Number(this.route.snapshot.paramMap.get('enrollmentId'));
    this.enrollmentId.set(id);
    this.loadDashboard();

    // Check if direct certificate view
    if (this.route.snapshot.paramMap.get('view') === 'certificate') {
      this.view.set('certificate');
      this.loadCertificate();
    }
  }

  ngOnDestroy() {
    this.stopHeartbeat();
  }

  loadDashboard() {
    this.svc.getEnrollmentDashboard(this.enrollmentId()).subscribe({
      next: d => { this.dashboard.set(d); this.loading.set(false); },
      error: () => { this.loading.set(false); this.router.navigate(['/awareness']); },
    });
  }

  currentModule(): AModule | undefined {
    if (!this.currentModuleId() || !this.dashboard()) return undefined;
    return this.dashboard()!.program.modules.find(m => m.id === this.currentModuleId());
  }

  openModule(mp: ModuleProgress) {
    this.currentModuleId.set(mp.module_id);
    this.view.set('content');
    this.quizData.set(null);
    this.quizResult.set(null);
    this.selectedAnswers.set({});
    this.moduleStartTime = Date.now();

    this.svc.startModule(this.enrollmentId(), mp.module_id).subscribe({
      next: () => this.startHeartbeat(mp.module_id),
      error: () => {},
    });
  }

  startQuiz() {
    if (!this.currentModuleId()) return;
    this.svc.getQuizQuestions(this.enrollmentId(), this.currentModuleId()!).subscribe({
      next: q => { this.quizData.set(q); this.view.set('quiz'); },
      error: (err) => {
        const msg = err.error?.detail || 'Impossible de charger le quiz.';
        this.snack.open(msg, 'Fermer', { duration: 4000 });
      },
    });
  }

  selectAnswer(questionId: string, answerId: string, multiple: boolean) {
    this.selectedAnswers.update(answers => {
      if (multiple) {
        const current = answers[questionId] ?? [];
        const idx = current.indexOf(answerId);
        return {
          ...answers,
          [questionId]: idx >= 0 ? current.filter(a => a !== answerId) : [...current, answerId],
        };
      }
      return { ...answers, [questionId]: [answerId] };
    });
  }

  isSelected(questionId: string, answerId: string): boolean {
    return (this.selectedAnswers()[questionId] ?? []).includes(answerId);
  }

  submitQuiz() {
    const duration = Math.floor((Date.now() - this.moduleStartTime) / 1000);
    this.submittingQuiz.set(true);
    this.svc.submitQuiz(this.enrollmentId(), this.currentModuleId()!, this.selectedAnswers(), duration).subscribe({
      next: result => {
        this.quizResult.set(result);
        this.submittingQuiz.set(false);
        this.view.set('quiz-result');
        if (result.result === 'passed') {
          this.stopHeartbeat();
          this.loadDashboard();
        }
      },
      error: () => {
        this.submittingQuiz.set(false);
        this.snack.open('Erreur lors de la soumission.', 'Fermer', { duration: 4000 });
      },
    });
  }

  retryQuiz() {
    this.selectedAnswers.set({});
    this.startQuiz();
  }

  completeWithoutQuiz() {
    this.completing.set(true);
    this.svc.completeModule(this.enrollmentId(), this.currentModuleId()!).subscribe({
      next: () => {
        this.completing.set(false);
        this.stopHeartbeat();
        this.loadDashboard();
        this.view.set('dashboard');
        this.snack.open('Module complété ! 🎉', 'OK', { duration: 3000 });
      },
      error: () => {
        this.completing.set(false);
        this.snack.open('Erreur.', 'Fermer', { duration: 3000 });
      },
    });
  }

  loadCertificate() {
    this.certLoading.set(true);
    this.svc.getCertificate(this.enrollmentId()).subscribe({
      next: c => { this.certificate.set(c); this.certLoading.set(false); },
      error: () => this.certLoading.set(false),
    });
  }

  certDownloadUrl(): string {
    return this.svc.certificateDownloadUrl(this.enrollmentId());
  }

  isNextModule(mp: ModuleProgress): boolean {
    const mods = this.dashboard()?.modules_progress ?? [];
    const completedCount = mods.filter(m => m.status === 'completed').length;
    return mp.position === completedCount + 1;
  }

  renderMarkdown(md: string): string {
    // Simple Markdown → HTML (headings, bold, lists, hr)
    return md
      .replace(/^### (.+)$/gm, '<h3 class="text-white font-semibold text-base mt-5 mb-2">$1</h3>')
      .replace(/^## (.+)$/gm, '<h2 class="text-cyan-400 font-bold text-lg mt-6 mb-3 border-b border-slate-700 pb-2">$1</h2>')
      .replace(/^# (.+)$/gm, '<h1 class="text-2xl font-bold text-white mb-4">$1</h1>')
      .replace(/\*\*(.+?)\*\*/g, '<strong class="text-white">$1</strong>')
      .replace(/^> (.+)$/gm, '<blockquote class="border-l-4 border-cyan-500 pl-4 text-cyan-300 italic my-3">$1</blockquote>')
      .replace(/^---$/gm, '<hr class="border-slate-700 my-5" />')
      .replace(/^- (.+)$/gm, '<li class="text-slate-300 ml-4 list-disc">$1</li>')
      .replace(/^(\d+)\. (.+)$/gm, '<li class="text-slate-300 ml-4 list-decimal">$2</li>')
      .replace(/\n\n/g, '</p><p class="text-slate-300 leading-relaxed my-2">')
      .replace(/❌ /g, '<span class="text-red-400">❌ </span>')
      .replace(/✅ /g, '<span class="text-green-400">✅ </span>');
  }

  formatTime(seconds: number): string {
    if (seconds < 60) return `${seconds}s`;
    return `${Math.floor(seconds / 60)}min`;
  }

  moduleIcon(status: string): string {
    const m: Record<string, string> = {
      completed: 'check', in_progress: 'play_arrow',
      failed: 'close', not_started: 'lock_outline',
    };
    return m[status] ?? 'circle';
  }

  moduleIconBg(status: string): string {
    const m: Record<string, string> = {
      completed: 'bg-green-500/20 text-green-400',
      in_progress: 'bg-blue-500/20 text-blue-400',
      failed: 'bg-red-500/20 text-red-400',
      not_started: 'bg-slate-700 text-slate-500',
    };
    return m[status] ?? 'bg-slate-700 text-slate-500';
  }

  moduleCardClass(status: string): string {
    if (status === 'not_started') return 'border-slate-700/50 opacity-60';
    if (status === 'in_progress') return 'border-blue-500/40';
    if (status === 'completed') return 'border-green-500/40';
    return 'border-slate-700';
  }

  private startHeartbeat(moduleId: number) {
    this.stopHeartbeat();
    this.heartbeatInterval = setInterval(() => {
      this.svc.heartbeat(this.enrollmentId(), moduleId, 30).subscribe({ error: () => {} });
    }, 30000);
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }
}
