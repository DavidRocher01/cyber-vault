import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Title } from '@angular/platform-browser';
import { RouterLink } from '@angular/router';

import { CostCalcService, CalcQuestion, CostResult } from '../services/cost-calc.service';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
  standalone: true,
  selector: 'app-cost-calculator',
  imports: [
    CommonModule, ReactiveFormsModule, RouterLink,
    MatButtonModule, MatIconModule, MatProgressSpinnerModule, MatSnackBarModule,
    NavButtonsComponent,
  ],
  templateUrl: './cost-calculator.component.html',
})
export class CostCalculatorComponent implements OnInit {
  private calcService = inject(CostCalcService);
  private fb = inject(FormBuilder);
  private snack = inject(MatSnackBar);
  private title = inject(Title);

  questions = signal<CalcQuestion[]>([]);
  loading = signal(true);
  step = signal<'intro' | 'wizard' | 'email' | 'result'>('intro');
  currentIndex = signal(0);
  answers = signal<Record<string, string>>({});
  submitting = signal(false);
  result = signal<CostResult | null>(null);

  emailForm = this.fb.nonNullable.group({
    email: ['', [Validators.email]],
    company: [''],
  });

  get currentQuestion(): CalcQuestion | null {
    return this.questions()[this.currentIndex()] ?? null;
  }

  get progress(): number {
    const total = this.questions().length;
    return total ? Math.round((this.currentIndex() / total) * 100) : 0;
  }

  get allAnswered(): boolean {
    return this.questions().every(q => this.answers()[q.key] != null);
  }

  ngOnInit() {
    this.title.setTitle('Calculateur coût cyberattaque — PME | CyberScan');
    this.calcService.getQuestions().subscribe({
      next: qs => { this.questions.set(qs); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  selectAnswer(key: string, optionId: string) {
    this.answers.update(a => ({ ...a, [key]: optionId }));
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

  finishWizard() {
    this.step.set('email');
  }

  submit() {
    this.submitting.set(true);
    const { email, company } = this.emailForm.getRawValue();
    const answerList = Object.entries(this.answers()).map(([key, option_id]) => ({ key, option_id }));
    this.calcService.estimate(answerList, email || undefined, company || undefined).subscribe({
      next: r => {
        this.result.set(r);
        this.submitting.set(false);
        this.step.set('result');
      },
      error: () => {
        this.submitting.set(false);
        this.snack.open('Erreur lors du calcul', 'Fermer', { duration: 4000 });
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

  formatEur(n: number): string {
    return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(n);
  }

  breakdownColor(pct: number): string {
    if (pct >= 30) return 'bg-red-500';
    if (pct >= 20) return 'bg-orange-500';
    return 'bg-yellow-500';
  }
}
