import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface DossierTarget {
  id: number;
  email: string;
  status: 'pending' | 'clean' | 'exposed' | 'error';
  check_status: 'pending' | 'verified_clean' | 'exposed' | 'api_error' | 'rate_limited';
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
  checked_count: number;
  unverified_count: number;
  risk_score: number | null;
  severity_score: number | null;
  top_sources_json: string | null;
  error_message: string | null;
  monitor_active: boolean;
  last_monitored_at: string | null;
  next_monitor_at: string | null;
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
  checked_count: number;
  unverified_count: number;
  risk_score: number | null;
  severity_score: number | null;
  monitor_active: boolean;
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

  rescan(id: number): Observable<DossierDetail> {
    return this.http.post<DossierDetail>(`${API}/${id}/rescan`, {});
  }

  toggleMonitor(
    id: number
  ): Observable<{ monitor_active: boolean; next_monitor_at: string | null }> {
    return this.http.patch<{ monitor_active: boolean; next_monitor_at: string | null }>(
      `${API}/${id}/monitor`,
      {}
    );
  }

  getCsvUrl(id: number): string {
    return `${API}/${id}/csv`;
  }

  getPdfUrl(id: number): string {
    return `${API}/${id}/pdf`;
  }

  syncCatalog(): Observable<{ synced: number; message: string }> {
    return this.http.post<{ synced: number; message: string }>(`${API}/catalog/sync`, {});
  }

  parseBreachSources(json: string | null): BreachSource[] {
    if (!json) return [];
    try {
      return JSON.parse(json);
    } catch {
      return [];
    }
  }

  parseTopSources(json: string | null): { name: string; count: number }[] {
    if (!json) return [];
    try {
      return JSON.parse(json);
    } catch {
      return [];
    }
  }

  /** Group breaches by year from breach_date field. Returns [{year, count}] sorted asc. */
  buildBreachTimeline(targets: DossierTarget[]): { year: number; count: number }[] {
    const counts: Record<number, number> = {};
    for (const t of targets) {
      const breaches = this.parseBreachSources(t.breach_sources_json);
      for (const b of breaches) {
        const year = b.breach_date ? parseInt(b.breach_date.substring(0, 4), 10) : 0;
        if (year >= 2000 && year <= new Date().getFullYear()) {
          counts[year] = (counts[year] ?? 0) + 1;
        }
      }
    }
    return Object.entries(counts)
      .map(([year, count]) => ({ year: Number(year), count }))
      .sort((a, b) => a.year - b.year);
  }
}
