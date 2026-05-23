import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface BrandProfile {
  company_name: string;
  accent_color: string;
  logo_b64: string | null;
  updated_at: string;
}

export interface BrandProfileInput {
  company_name: string;
  accent_color: string;
  logo_b64?: string | null;
}

const API = '/api/v1/brand';

@Injectable({ providedIn: 'root' })
export class BrandService {
  private http = inject(HttpClient);

  get(): Observable<BrandProfile | null> {
    return this.http.get<BrandProfile | null>(`${API}/me`);
  }

  upsert(payload: BrandProfileInput): Observable<BrandProfile> {
    return this.http.put<BrandProfile>(`${API}/me`, payload);
  }
}
