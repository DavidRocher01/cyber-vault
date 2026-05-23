import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface DossierTarget {
  id: number;
  email: string;
  status: 'pending' | 'clean' | 'exposed' | 'error';
  total_breaches: number;
  breach_sources_json: string | null;
  checked_at: string | null;
}

export interface DossierDetail {
  id: number;
  company_name: string;
  domain: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  total_emails: number;
  exposed_emails: number;
  total_breach_instances: number;
  risk_score: number | null;
  top_sources_json: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  targets: DossierTarget[];
}

export interface DossierListItem {
  id: number;
  company_name: string;
  domain: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  total_emails: number;
  exposed_emails: number;
  risk_score: number | null;
  created_at: string;
  finished_at: string | null;
}

export interface BreachSource {
  name: string;
  domain?: string;
  breach_date?: string;
  pwn_count?: number;
  data_classes?: string[];
  is_sensitive?: boolean;
  is_verified?: boolean;
}

const API = '/api/v1/darkweb-dossier';

@Injectable({ providedIn: 'root' })
export class DarkwebDossierService {
  private http = inject(HttpClient);

  list(): Observable<DossierListItem[]> {
    return this.http.get<DossierListItem[]>(API);
  }

  get(id: number): Observable<DossierDetail> {
    return this.http.get<DossierDetail>(`${API}/${id}`);
  }

  create(companyName: string, domain: string, csvFile: File): Observable<DossierDetail> {
    const fd = new FormData();
    fd.append('company_name', companyName);
    fd.append('domain', domain);
    fd.append('emails_csv', csvFile);
    return this.http.post<DossierDetail>(API, fd);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${API}/${id}`);
  }

  getPdfUrl(id: number): string {
    return `${API}/${id}/pdf`;
  }

  syncCatalog(): Observable<{ synced: number; message: string }> {
    return this.http.post<{ synced: number; message: string }>(`${API}/catalog/sync`, {});
  }

  parseBreachSources(json: string | null): BreachSource[] {
    if (!json) return [];
    try { return JSON.parse(json); } catch { return []; }
  }

  parseTopSources(json: string | null): { name: string; count: number }[] {
    if (!json) return [];
    try { return JSON.parse(json); } catch { return []; }
  }
}
