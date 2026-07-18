import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';

export interface PhishingCampaign {
  id: number;
  name: string;
  status:
    | 'draft'
    | 'pending_verification'
    | 'ready'
    | 'scheduled'
    | 'active'
    | 'sending'
    | 'completed'
    | 'cancelled';
  plan_tier: string;
  rssi_client_id: number | null;
  sending_domain: string;
  training_on_fail: boolean;
  training_trigger: 'click' | 'submit';
  batch_size: number | null;
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

  /** rssiClientId renseigné => campagnes d'un client (mode consultant) ;
   *  sinon => campagnes de l'entreprise en direct (sans client rattaché). */
  getCampaigns(rssiClientId?: number): Observable<PhishingCampaign[]> {
    const q = rssiClientId != null ? `?rssi_client_id=${rssiClientId}` : '';
    return this.http.get<PhishingCampaign[]>(`${this.base}/campaigns${q}`);
  }

  getCampaign(id: number): Observable<PhishingCampaign> {
    return this.http.get<PhishingCampaign>(`${this.base}/campaigns/${id}`);
  }

  /** rssiClientId rattache la campagne à un client RSSI (mode consultant). */
  createCampaign(
    name: string,
    plan_tier: string,
    rssiClientId?: number
  ): Observable<PhishingCampaign> {
    const body: { name: string; plan_tier: string; rssi_client_id?: number } = { name, plan_tier };
    if (rssiClientId != null) body.rssi_client_id = rssiClientId;
    return this.http.post<PhishingCampaign>(`${this.base}/campaigns`, body);
  }

  updateCampaign(
    id: number,
    patch: Partial<{
      name: string;
      domain: string;
      lookalike_domain: string;
      scenario_keys: string[];
      cgu_accepted: boolean;
      scheduled_at: string;
      training_on_fail: boolean;
      training_trigger: 'click' | 'submit';
      batch_size: number;
    }>
  ): Observable<PhishingCampaign> {
    return this.http.patch<PhishingCampaign>(`${this.base}/campaigns/${id}`, patch);
  }

  /** Annule une campagne (statut "cancelled") : plus aucun email ne partira. */
  cancelCampaign(id: number): Observable<PhishingCampaign> {
    return this.http.post<PhishingCampaign>(`${this.base}/campaigns/${id}/cancel`, {});
  }

  /** Supprime définitivement une campagne (et ses cibles). */
  deleteCampaign(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/campaigns/${id}`);
  }

  getLookalikeDomains(domain: string): Observable<LookalikeDomainsResult> {
    return this.http.get<LookalikeDomainsResult>(`${this.base}/lookalike-domains`, {
      params: { domain },
    });
  }

  /** Import CSV. replace=false (défaut) = merge/dédup (n'écrase pas les cibles
   *  existantes) ; replace=true = remplace tout. */
  uploadTargets(
    id: number,
    file: File,
    replace = false
  ): Observable<{ targets_added: number; targets_skipped: number; targets_total: number }> {
    const form = new FormData();
    form.append('file', file);
    const q = replace ? '?replace=true' : '';
    return this.http.post<{
      targets_added: number;
      targets_skipped: number;
      targets_total: number;
    }>(`${this.base}/campaigns/${id}/targets${q}`, form);
  }

  getTargets(id: number): Observable<PhishingTarget[]> {
    return this.http.get<PhishingTarget[]>(`${this.base}/campaigns/${id}/targets`);
  }

  addTarget(
    id: number,
    target: { email: string; first_name?: string; last_name?: string; department?: string }
  ): Observable<PhishingTarget> {
    return this.http.post<PhishingTarget>(`${this.base}/campaigns/${id}/targets/single`, target);
  }

  deleteTarget(id: number, targetId: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/campaigns/${id}/targets/${targetId}`);
  }

  launchCampaign(id: number): Observable<{ status: string; campaign_id: number }> {
    return this.http.post<{ status: string; campaign_id: number }>(
      `${this.base}/campaigns/${id}/launch`,
      {}
    );
  }

  requestDomainVerify(domain: string): Observable<DomainVerifyResult> {
    return this.http.post<DomainVerifyResult>(`${this.base}/domain-verify`, { domain });
  }

  checkDomainVerify(
    domain: string
  ): Observable<{ domain: string; verified: boolean; verified_at: string | null }> {
    return this.http.post<{ domain: string; verified: boolean; verified_at: string | null }>(
      `${this.base}/domain-verify/check`,
      { domain }
    );
  }

  /**
   * Télécharge le PDF via HttpClient (responseType blob) pour que
   * l'intercepteur d'auth ajoute le Bearer — un window.open ne le ferait pas
   * (navigation navigateur sans header → 401).
   */
  downloadPdfBlob(id: number): Observable<Blob> {
    return this.http.get(`${this.base}/campaigns/${id}/pdf`, { responseType: 'blob' });
  }
}
