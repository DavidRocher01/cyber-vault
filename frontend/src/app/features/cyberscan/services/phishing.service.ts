import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';

export interface PhishingCampaign {
  id: number;
  name: string;
  status: 'draft' | 'pending_verification' | 'ready' | 'active' | 'completed' | 'cancelled';
  plan_tier: string;
  domain: string | null;
  domain_verified: boolean;
  scenario_keys: string[];
  targets_count: number;
  emails_sent: number;
  opened_count: number;
  clicked_count: number;
  submitted_count: number;
  click_rate: number;
  cgu_accepted: boolean;
  scheduled_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  targets?: PhishingTarget[];
}

export interface PhishingTarget {
  id: number;
  email: string;
  first_name: string;
  last_name: string | null;
  department: string | null;
  status: string;
}

export interface DomainVerifyResult {
  domain: string;
  verified: boolean;
  verification_token: string;
  dns_record_name: string;
  dns_record_type: string;
  dns_record_value: string;
  instructions: string;
}

@Injectable({ providedIn: 'root' })
export class PhishingService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/phishing`;

  getCampaigns(): Observable<PhishingCampaign[]> {
    return this.http.get<PhishingCampaign[]>(`${this.base}/campaigns`);
  }

  getCampaign(id: number): Observable<PhishingCampaign> {
    return this.http.get<PhishingCampaign>(`${this.base}/campaigns/${id}`);
  }

  createCampaign(name: string, plan_tier: string): Observable<PhishingCampaign> {
    return this.http.post<PhishingCampaign>(`${this.base}/campaigns`, { name, plan_tier });
  }

  updateCampaign(id: number, patch: Partial<{
    name: string;
    domain: string;
    scenario_keys: string[];
    cgu_accepted: boolean;
    scheduled_at: string;
  }>): Observable<PhishingCampaign> {
    return this.http.patch<PhishingCampaign>(`${this.base}/campaigns/${id}`, patch);
  }

  uploadTargets(id: number, file: File): Observable<{ targets_added: number }> {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<{ targets_added: number }>(`${this.base}/campaigns/${id}/targets`, form);
  }

  launchCampaign(id: number): Observable<{ status: string; campaign_id: number }> {
    return this.http.post<{ status: string; campaign_id: number }>(`${this.base}/campaigns/${id}/launch`, {});
  }

  requestDomainVerify(domain: string): Observable<DomainVerifyResult> {
    return this.http.post<DomainVerifyResult>(`${this.base}/domain-verify`, { domain });
  }

  checkDomainVerify(domain: string): Observable<{ domain: string; verified: boolean; verified_at: string | null }> {
    return this.http.post<{ domain: string; verified: boolean; verified_at: string | null }>(
      `${this.base}/domain-verify/check`,
      { domain }
    );
  }

  getPdfUrl(id: number): string {
    return `${this.base}/campaigns/${id}/pdf`;
  }
}
