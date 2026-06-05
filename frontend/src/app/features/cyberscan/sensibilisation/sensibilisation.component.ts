import { Component, inject, OnInit, signal } from '@angular/core';
import { UpperCasePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Title } from '@angular/platform-browser';

import {
  TrainingService,
  TrainingModule,
  TrainingProgress,
  CompleteResult,
} from '../services/training.service';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

type QuizState = 'idle' | 'answered';

interface ModuleUiState {
  open: boolean;
  selected: string | null;
  quizState: QuizState;
  result: CompleteResult | null;
  submitting: boolean;
}

@Component({
  standalone: true,
  selector: 'app-sensibilisation',
  imports: [
    UpperCasePipe,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTooltipModule,
    NavButtonsComponent,
  ],
  templateUrl: './sensibilisation.component.html',
  styleUrl: './sensibilisation.component.css',
})
export class SensibilisationComponent implements OnInit {
  private training = inject(TrainingService);
  private snack = inject(MatSnackBar);
  private title = inject(Title);

  modules = signal<TrainingModule[]>([]);
  progress = signal<TrainingProgress | null>(null);
  loading = signal(true);
  uiState = signal<Record<string, ModuleUiState>>({});

  ngOnInit() {
    this.title.setTitle('Sensibilisation — CyberScan');
    this.loadAll();
  }

  loadAll() {
    this.training.getModules().subscribe({
      next: mods => {
        this.modules.set(mods);
        const state: Record<string, ModuleUiState> = {};
        mods.forEach(m => {
          state[m.id] = {
            open: false,
            selected: null,
            quizState: 'idle',
            result: null,
            submitting: false,
          };
        });
        this.uiState.set(state);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
    this.training.getProgress().subscribe({
      next: p => this.progress.set(p),
    });
  }

  toggleModule(id: string) {
    this.uiState.update(s => ({
      ...s,
      [id]: { ...s[id], open: !s[id].open },
    }));
  }

  selectChoice(moduleId: string, choiceId: string) {
    const state = this.uiState()[moduleId];
    if (state.quizState === 'answered') return;
    this.uiState.update(s => ({ ...s, [moduleId]: { ...s[moduleId], selected: choiceId } }));
  }

  submitAnswer(moduleId: string) {
    const state = this.uiState()[moduleId];
    if (!state.selected || state.quizState === 'answered' || state.submitting) return;

    this.uiState.update(s => ({ ...s, [moduleId]: { ...s[moduleId], submitting: true } }));

    this.training.completeModule(moduleId, state.selected).subscribe({
      next: result => {
        this.uiState.update(s => ({
          ...s,
          [moduleId]: { ...s[moduleId], quizState: 'answered', result, submitting: false },
        }));
        if (result.correct) {
          this.modules.update(mods =>
            mods.map(m => (m.id === moduleId ? { ...m, completed: true } : m))
          );
          this.training.getProgress().subscribe({ next: p => this.progress.set(p) });
          this.snack.open('Bonne réponse ! Module complété.', 'OK', { duration: 3000 });
        }
      },
      error: () => {
        this.uiState.update(s => ({ ...s, [moduleId]: { ...s[moduleId], submitting: false } }));
        this.snack.open('Erreur lors de la soumission', 'Fermer', { duration: 4000 });
      },
    });
  }

  resetQuiz(moduleId: string) {
    this.uiState.update(s => ({
      ...s,
      [moduleId]: { ...s[moduleId], selected: null, quizState: 'idle', result: null },
    }));
  }

  getState(id: string): ModuleUiState {
    return (
      this.uiState()[id] ?? {
        open: false,
        selected: null,
        quizState: 'idle',
        result: null,
        submitting: false,
      }
    );
  }

  colorClass(color: string): { border: string; icon: string; badge: string } {
    const map: Record<string, { border: string; icon: string; badge: string }> = {
      red: {
        border: 'border-red-600/40',
        icon: 'text-red-400',
        badge: 'bg-red-500/15 text-red-300',
      },
      blue: {
        border: 'border-blue-600/40',
        icon: 'text-blue-400',
        badge: 'bg-blue-500/15 text-blue-300',
      },
      yellow: {
        border: 'border-yellow-600/40',
        icon: 'text-yellow-400',
        badge: 'bg-yellow-500/15 text-yellow-300',
      },
      orange: {
        border: 'border-orange-600/40',
        icon: 'text-orange-400',
        badge: 'bg-orange-500/15 text-orange-300',
      },
      green: {
        border: 'border-green-600/40',
        icon: 'text-green-400',
        badge: 'bg-green-500/15 text-green-300',
      },
    };
    return map[color] ?? map['blue'];
  }
}
