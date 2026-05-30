import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface QuizOption {
  id: string;
  text: string;
}
export interface QuizQuestion {
  id: number;
  text: string;
  category: string;
  options: QuizOption[];
}

export interface QuizAnswer {
  question_id: number;
  answer_id: string;
}
export interface QuizSubmitPayload {
  answers: QuizAnswer[];
  email?: string;
  company?: string;
}

export interface CategoryScore {
  category: string;
  score: number;
  max: number;
  percentage: number;
}
export interface QuizLevel {
  label: string;
  color: string;
  description: string;
}
export interface QuizResult {
  score: number;
  max_score: number;
  percentage: number;
  level: QuizLevel;
  category_scores: CategoryScore[];
  recommendations: string[];
}

const API = '/api/v1/quiz';

@Injectable({ providedIn: 'root' })
export class QuizService {
  private http = inject(HttpClient);

  getQuestions(): Observable<QuizQuestion[]> {
    return this.http.get<QuizQuestion[]>(`${API}/questions`);
  }

  submit(payload: QuizSubmitPayload): Observable<QuizResult> {
    return this.http.post<QuizResult>(`${API}/submit`, payload);
  }
}
