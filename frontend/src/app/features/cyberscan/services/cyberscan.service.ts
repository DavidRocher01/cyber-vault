import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Plan {
  id: number;
  name: string;
  display_name: string;
  price_eur: number;
  max_sites: number;
  scan_interval_days: number;
  tier_level: number;
  stripe_price_id: string;
}

export interface Subscription {
  id: number;
  plan_id: number;
  status: string;
  current_period_start: string;
  current_period_end: string;
  plan: Plan;
}

export interface CheckoutSession {
  checkout_url: string;
}

export interface Site {
  id: number;
  url: string;
  name: string;
  is_active: boolean;
  created_at: string;
}

export interface SiteCreate {
  url: string;
  name: string;
}

export interface Scan {
  id: number;
  site_id: number;
  status: string;
  overall_status: string | null;
  pdf_path: string | null;
  results_json: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
}

export interface PaginatedScans {
  items: Scan[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface UrlScan {
  id: number;
  user_id: number;
  url: string;
  status: string;
  verdict: 'safe' | 'suspicious' | 'malicious' | null;
  threat_type: string | null;
  threat_score: number | null;
  screenshot_path: string | null;
  results_json: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface PaginatedUrlScans {
  items: UrlScan[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

const API = '/api/v1';

@Injectable({ providedIn: 'root' })
export class CyberscanService {
  private http = inject(HttpClient);

  getPlans(): Observable<Plan[]> {
    return this.http.get<Plan[]>(`${API}/plans`);
  }

  getMySubscription(): Observable<Subscription | null> {
    return this.http.get<Subscription | null>(`${API}/subscriptions/me`);
  }

  createCheckout(planId: number): Observable<CheckoutSession> {
    return this.http.post<CheckoutSession>(`${API}/subscriptions/checkout/${planId}`, {});
  }

  getBillingPortal(): Observable<{ checkout_url: string }> {
    return this.http.get<{ checkout_url: string }>(`${API}/subscriptions/portal`);
  }

  getMySites(): Observable<Site[]> {
    return this.http.get<Site[]>(`${API}/sites`);
  }

  createSite(data: SiteCreate): Observable<Site> {
    return this.http.post<Site>(`${API}/sites`, data);
  }

  deleteSite(siteId: number): Observable<void> {
    return this.http.delete<void>(`${API}/sites/${siteId}`);
  }

  triggerScan(siteId: number): Observable<{ scan_id: number; message: string }> {
    return this.http.post<{ scan_id: number; message: string }>(`${API}/scans/trigger/${siteId}`, {});
  }

  getSiteScans(siteId: number, page = 1, perPage = 10): Observable<PaginatedScans> {
    return this.http.get<PaginatedScans>(`${API}/scans/site/${siteId}?page=${page}&per_page=${perPage}`);
  }

  getScan(scanId: number): Observable<Scan> {
    return this.http.get<Scan>(`${API}/scans/${scanId}`);
  }

  downloadPdf(scanId: number): string {
    return `${API}/scans/${scanId}/pdf`;
  }

  exportCsv(siteId: number): string {
    return `${API}/scans/site/${siteId}/export`;
  }

  // ── URL Scans ──────────────────────────────────────────────────────────

  triggerUrlScan(url: string): Observable<UrlScan> {
    return this.http.post<UrlScan>(`${API}/url-scans`, { url });
  }

  getUrlScans(page = 1, perPage = 20): Observable<PaginatedUrlScans> {
    return this.http.get<PaginatedUrlScans>(`${API}/url-scans?page=${page}&per_page=${perPage}`);
  }

  getUrlScan(id: number): Observable<UrlScan> {
    return this.http.get<UrlScan>(`${API}/url-scans/${id}`);
  }

  deleteUrlScan(id: number): Observable<void> {
    return this.http.delete<void>(`${API}/url-scans/${id}`);
  }
}
