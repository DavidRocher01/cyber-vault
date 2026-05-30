import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface CalcOption {
  id: string;
  text: string;
}
export interface CalcQuestion {
  id: number;
  text: string;
  key: string;
  options: CalcOption[];
}
export interface CalcAnswer {
  key: string;
  option_id: string;
}

export interface BreakdownItem {
  label: string;
  pct: number;
  eur: number;
}
export interface CostResult {
  estimated_eur: number;
  low_eur: number;
  high_eur: number;
  multiplier: number;
  breakdown: BreakdownItem[];
}

const API = '/api/v1/cost-calc';

@Injectable({ providedIn: 'root' })
export class CostCalcService {
  private http = inject(HttpClient);

  getQuestions(): Observable<CalcQuestion[]> {
    return this.http.get<CalcQuestion[]>(`${API}/questions`);
  }

  estimate(answers: CalcAnswer[], email?: string, company?: string): Observable<CostResult> {
    return this.http.post<CostResult>(`${API}/estimate`, { answers, email, company });
  }
}
