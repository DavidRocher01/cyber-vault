import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';

export interface PortalConsultant {
  display_name: string | null;
  company_name: string | null;
  email: string;
  phone: string | null;
}

export interface PortalVisit {
  id: number;
  scheduled_date: string;
  visit_type: string;
  location: string | null;
  status: string;
  actual_date: string | null;
  duration_hours: number | null;
}

export interface PortalAction {
  id: number;
  title: string;
  description: string | null;
  category: string | null;
  priority: string;
  status: string;
  assigned_to: string | null;
  due_date: string | null;
  completed_at: string | null;
}

export interface PortalDeliverable {
  id: number;
  title: string;
  doc_type: string;
  delivered_at: string;
  notes: string | null;
  has_file: boolean;
}

export interface PortalMe {
  name: string;
  formula: string | null;
  status: string;
  contract_start_date: string | null;
  contract_renewal_at: string | null;
  consultant: PortalConsultant | null;
  progress_score: number;
  actions_total: number;
  actions_open: number;
  actions_in_progress: number;
  actions_done: number;
  actions_overdue: number;
  next_visit: PortalVisit | null;
}

@Injectable({ providedIn: 'root' })
export class ClientPortalService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/portal`;

  getMe() {
    return this.http.get<PortalMe>(`${this.base}/me`);
  }
  getActions() {
    return this.http.get<PortalAction[]>(`${this.base}/actions`);
  }
  getVisits() {
    return this.http.get<PortalVisit[]>(`${this.base}/visits`);
  }
  getDeliverables() {
    return this.http.get<PortalDeliverable[]>(`${this.base}/deliverables`);
  }
  getDeliverableUrl(id: number) {
    return this.http.get<{ url: string }>(`${this.base}/deliverables/${id}/download`);
  }
  downloadReport() {
    return this.http.get(`${this.base}/report`, { responseType: 'blob' });
  }
}
