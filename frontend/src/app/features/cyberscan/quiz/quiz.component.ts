import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Title } from '@angular/platform-browser';
import { RouterLink } from '@angular/router';

import { QuizService, QuizQuestion, QuizResult, CategoryScore } from '../services/quiz.service';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
  standalone: true,
  selector: 'app-quiz',
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    NavButtonsComponent,
  ],
  templateUrl: './quiz.component.html',
})
export class QuizComponent implements OnInit {
  private quizService = inject(QuizService);
  private fb = inject(FormBuilder);
  private snack = inject(MatSnackBar);
  private title = inject(Title);

  questions = signal<QuizQuestion[]>([]);
  loading = signal(true);
  step = signal<'intro' | 'quiz' | 'email' | 'result'>('intro');
  currentIndex = signal(0);
  answers = signal<Record<number, string>>({});
  submitting = signal(false);
  result = signal<QuizResult | null>(null);

  emailForm = this.fb.nonNullable.group({
    email: ['', [Validators.email]],
    company: [''],
  });

  get currentQuestion(): QuizQuestion | null {
    return this.questions()[this.currentIndex()] ?? null;
  }

  get progress(): number {
    const total = this.questions().length;
    if (!total) return 0;
    return Math.round((this.currentIndex() / total) * 100);
  }

  get allAnswered(): boolean {
    return this.questions().every(q => this.answers()[q.id] != null);
  }

  ngOnInit() {
    this.title.setTitle('Quiz maturité cybersécurité — NIS2 / ISO 27001 | CyberScan');
    this.quizService.getQuestions().subscribe({
      next: qs => {
        this.questions.set(qs);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  selectAnswer(questionId: number, answerId: string) {
    this.answers.update(a => ({ ...a, [questionId]: answerId }));
  }

  next() {
    if (this.currentIndex() < this.questions().length - 1) {
      this.currentIndex.update(i => i + 1);
    }
  }

  prev() {
    if (this.currentIndex() > 0) {
      this.currentIndex.update(i => i - 1);
    }
  }

  goToQuestion(i: number) {
    this.currentIndex.set(i);
  }

  finishQuiz() {
    this.step.set('email');
  }

  submit() {
    this.submitting.set(true);
    const { email, company } = this.emailForm.getRawValue();
    const answerMap = this.answers();
    const answerList = Object.entries(answerMap).map(([qid, aid]) => ({
      question_id: Number(qid),
      answer_id: aid,
    }));
    this.quizService
      .submit({
        answers: answerList,
        email: email || undefined,
        company: company || undefined,
      })
      .subscribe({
        next: r => {
          this.result.set(r);
          this.submitting.set(false);
          this.step.set('result');
        },
        error: () => {
          this.submitting.set(false);
          this.snack.open('Erreur lors de la soumission', 'Fermer', { duration: 4000 });
        },
      });
  }

  skipEmail() {
    this.emailForm.reset();
    this.submit();
  }

  restart() {
    this.answers.set({});
    this.currentIndex.set(0);
    this.result.set(null);
    this.emailForm.reset();
    this.step.set('intro');
  }

  categoryColor(pct: number): string {
    if (pct >= 80) return 'bg-green-500';
    if (pct >= 60) return 'bg-yellow-500';
    if (pct >= 35) return 'bg-orange-500';
    return 'bg-red-500';
  }

  categoryTextColor(pct: number): string {
    if (pct >= 80) return 'text-green-400';
    if (pct >= 60) return 'text-yellow-400';
    if (pct >= 35) return 'text-orange-400';
    return 'text-red-400';
  }
}
