import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface TrainingChoice {
  id: string;
  text: string;
}

export interface TrainingModule {
  id: string;
  title: string;
  icon: string;
  color: string;
  duration_min: number;
  description: string;
  scenario: string;
  choices: TrainingChoice[];
  correct: string;
  explanation: string;
  completed: boolean;
  completed_at: string | null;
}

export interface TrainingProgress {
  completed: number;
  total: number;
  percentage: number;
  completed_ids: string[];
}

export interface CompleteResult {
  correct: boolean;
  explanation: string;
  correct_answer: string;
}

const API = '/api/v1/training';

@Injectable({ providedIn: 'root' })
export class TrainingService {
  private http = inject(HttpClient);

  getModules(): Observable<TrainingModule[]> {
    return this.http.get<TrainingModule[]>(`${API}/modules`);
  }

  completeModule(moduleId: string, answer: string): Observable<CompleteResult> {
    return this.http.post<CompleteResult>(`${API}/modules/${moduleId}/complete`, { answer });
  }

  getProgress(): Observable<TrainingProgress> {
    return this.http.get<TrainingProgress>(`${API}/progress`);
  }
}
