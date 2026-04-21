import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, shareReplay } from 'rxjs';

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

export interface CodeScan {
  id: number;
  user_id: number;
  repo_url: string;
  repo_name: string | null;
  status: string;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  results_json: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface PaginatedCodeScans {
  items: CodeScan[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface AppNotification {
  id: number;
  type: string;
  title: string;
  body: string | null;
  link: string | null;
  read: boolean;
  created_at: string;
}

export interface NotificationList {
  items: AppNotification[];
  unread_count: number;
}

export interface PublicScanResult {
  token: string;
  status: string;
  overall_status: string | null;
  results_json: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface SubdomainEntry {
  subdomain: string;
  ip: string;
}

export interface SubdomainResult {
  site_url: string;
  subdomains: SubdomainEntry[];
  zone_transfer: { vulnerable: boolean; nameservers: string[]; records_found: string[] } | null;
  total_found: number;
  scan_date: string | null;
}

const API = '/api/v1';

@Injectable({ providedIn: 'root' })
export class CyberscanService {
  private http = inject(HttpClient);

  // ── In-memory caches (busted on demand) ───────────────────────────────
  private _plans$: Observable<Plan[]> | null = null;
  private _subscription$: Observable<Subscription | null> | null = null;

  getPlans(): Observable<Plan[]> {
    if (!this._plans$) {
      this._plans$ = this.http.get<Plan[]>(`${API}/plans`).pipe(shareReplay(1));
    }
    return this._plans$;
  }

  getMySubscription(refresh = false): Observable<Subscription | null> {
    if (!this._subscription$ || refresh) {
      this._subscription$ = this.http.get<Subscription | null>(`${API}/subscriptions/me`).pipe(shareReplay(1));
    }
    return this._subscription$;
  }

  /** Call after checkout / plan change to force subscription reload. */
  invalidateSubscriptionCache(): void {
    this._subscription$ = null;
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

  downloadPdfBlob(scanId: number): Observable<Blob> {
    return this.http.get(`${API}/scans/${scanId}/pdf`, { responseType: 'blob' });
  }

  downloadRemediationBlob(scanId: number, scriptKey: string): Observable<Blob> {
    return this.http.get(`${API}/scans/${scanId}/remediation/${scriptKey}`, { responseType: 'blob' });
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

  downloadUrlScanPdfBlob(scanId: number): Observable<Blob> {
    return this.http.get(`${API}/url-scans/${scanId}/pdf`, { responseType: 'blob' });
  }

  // ── Code Scans ─────────────────────────────────────────────────────────

  triggerCodeScan(repoUrl: string, githubToken?: string): Observable<{ scan_id: number; message: string }> {
    return this.http.post<{ scan_id: number; message: string }>(`${API}/code-scans`, {
      repo_url: repoUrl,
      github_token: githubToken || null,
    });
  }

  getCodeScans(page = 1, perPage = 10): Observable<PaginatedCodeScans> {
    return this.http.get<PaginatedCodeScans>(`${API}/code-scans?page=${page}&per_page=${perPage}`);
  }

  getCodeScan(id: number): Observable<CodeScan> {
    return this.http.get<CodeScan>(`${API}/code-scans/${id}`);
  }

  deleteCodeScan(id: number): Observable<void> {
    return this.http.delete<void>(`${API}/code-scans/${id}`);
  }

  uploadCodeScan(file: File): Observable<{ scan_id: number; message: string }> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<{ scan_id: number; message: string }>(`${API}/code-scans/upload`, formData);
  }

  // ── NIS2 ──────────────────────────────────────────────────────────────

  getNis2Assessment(): Observable<any> {
    return this.http.get<any>(`${API}/nis2/me`);
  }

  saveNis2Assessment(items: Record<string, string>): Observable<any> {
    return this.http.put<any>(`${API}/nis2/me`, { items });
  }

  downloadNis2PdfBlob(): Observable<Blob> {
    return this.http.get(`${API}/nis2/me/pdf`, { responseType: 'blob' });
  }

  // ── ISO 27001 ──────────────────────────────────────────────────────────

  getIso27001Assessment(): Observable<any> {
    return this.http.get<any>(`${API}/iso27001/me`);
  }

  saveIso27001Assessment(items: Record<string, string>): Observable<any> {
    return this.http.put<any>(`${API}/iso27001/me`, { items });
  }

  downloadIso27001PdfBlob(): Observable<Blob> {
    return this.http.get(`${API}/iso27001/me/pdf`, { responseType: 'blob' });
  }

  // ── Notifications ──────────────────────────────────────────────────────

  getNotifications(): Observable<NotificationList> {
    return this.http.get<NotificationList>(`${API}/notifications`);
  }

  markNotificationRead(id: number): Observable<AppNotification> {
    return this.http.post<AppNotification>(`${API}/notifications/${id}/read`, {});
  }

  markAllNotificationsRead(): Observable<void> {
    return this.http.post<void>(`${API}/notifications/read-all`, {});
  }

  deleteNotification(id: number): Observable<void> {
    return this.http.delete<void>(`${API}/notifications/${id}`);
  }

  // ── Public Scans (no auth) ─────────────────────────────────────────────

  createPublicScan(url: string): Observable<PublicScanResult> {
    return this.http.post<PublicScanResult>(`${API}/public-scans`, { url });
  }

  getPublicScan(token: string): Observable<PublicScanResult> {
    return this.http.get<PublicScanResult>(`${API}/public-scans/${token}`);
  }

  // ── Subdomains ─────────────────────────────────────────────────────────

  getSiteSubdomains(siteId: number): Observable<SubdomainResult> {
    return this.http.get<SubdomainResult>(`${API}/sites/${siteId}/subdomains`);
  }
}
