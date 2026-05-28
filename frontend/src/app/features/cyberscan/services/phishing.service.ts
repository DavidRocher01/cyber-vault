import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';

export interface PhishingCampaign {
  id: number;
  name: string;
  status: 'draft' | 'pending_verification' | 'ready' | 'scheduled' | 'active' | 'sending' | 'completed' | 'cancelled';
  plan_tier: string;
  domain: string | null;
  domain_verified: boolean;
  lookalike_domain: string | null;
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

export type LookalikeTechnique =
  | 'sim_subdomain'
  | 'combosquatting_prepend'
  | 'combosquatting_append'
  | 'tld_swap'
  | 'typo_missing_char'
  | 'typo_double_char'
  | 'typo_char_swap'
  | 'typo_homoglyph'
  | 'subdomain_trick';

export const LOOKALIKE_TECHNIQUE_LABELS: Record<LookalikeTechnique, string> = {
  sim_subdomain: 'Sous-domaine simulation (gratuit)',
  combosquatting_prepend: 'Préfixe (combosquatting)',
  combosquatting_append: 'Suffixe (combosquatting)',
  tld_swap: "Changement d'extension",
  typo_missing_char: 'Caractère manquant',
  typo_double_char: 'Doublon de caractère',
  typo_char_swap: 'Inversion de lettres',
  typo_homoglyph: 'Homoglyphe',
  subdomain_trick: 'Sous-domaine trompeur',
};

export interface LookalikeDomain {
  domain: string;
  technique: LookalikeTechnique;
  realism_score: number;
  requires_purchase: boolean;
  purchase_url: string;
  setup_instructions: string;
  note: string;
}

export interface LookalikeDomainsResult {
  domain: string;
  suggestions: LookalikeDomain[];
}

export interface PhishingTarget {
  id: number;
  email: string;
  first_name: string;
  last_name: string | null;
  department: string | null;
  scenario_key: string | null;
  status: string;
  email_sent_at: string | null;
  opened_at: string | null;
  clicked_at: string | null;
  submitted_at: string | null;
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
    lookalike_domain: string;
    scenario_keys: string[];
    cgu_accepted: boolean;
    scheduled_at: string;
  }>): Observable<PhishingCampaign> {
    return this.http.patch<PhishingCampaign>(`${this.base}/campaigns/${id}`, patch);
  }

  getLookalikeDomains(domain: string): Observable<LookalikeDomainsResult> {
    return this.http.get<LookalikeDomainsResult>(`${this.base}/lookalike-domains`, {
      params: { domain },
    });
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
