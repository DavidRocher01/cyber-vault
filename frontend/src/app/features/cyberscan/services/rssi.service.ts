import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface RssiClient {
  id: number;
  name: string;
  email: string | null;
  description: string | null;
  formula: 'essentiel' | 'premium' | 'excellence' | null;
  monthly_amount: number | null;
  contract_start_date: string | null;
  contract_renewal_at: string | null;
  status: 'active' | 'inactive' | 'churned';
  notion_workspace_url: string | null;
  pipedrive_deal_id: string | null;
  pennylane_customer_id: string | null;
  created_at: string;
  updated_at: string | null;
  sites_count: number;
  worst_status: 'OK' | 'WARNING' | 'CRITICAL' | null;
  last_scan_at: string | null;
}

export interface RssiClientCreate {
  name: string;
  email?: string;
  description?: string;
  formula?: 'essentiel' | 'premium' | 'excellence';
  monthly_amount?: number;
  contract_start_date?: string;
  contract_renewal_at?: string;
  notion_workspace_url?: string;
  pipedrive_deal_id?: string;
  pennylane_customer_id?: string;
}

export interface RssiClientUpdate extends Partial<RssiClientCreate> {
  status?: 'active' | 'inactive' | 'churned';
}

export interface RssiVisit {
  id: number;
  client_id: number;
  scheduled_date: string;
  visit_type: 'monthly' | 'quarterly' | 'annual' | 'urgent';
  location: 'onsite' | 'remote';
  status: 'planned' | 'completed' | 'cancelled' | 'postponed';
  notes: string | null;
  actual_date: string | null;
  duration_hours: number | null;
  created_at: string;
  updated_at: string;
}

export interface RssiVisitCreate {
  scheduled_date: string;
  visit_type?: 'monthly' | 'quarterly' | 'annual' | 'urgent';
  location?: 'onsite' | 'remote';
  notes?: string;
}

export interface RssiVisitUpdate {
  scheduled_date?: string;
  visit_type?: 'monthly' | 'quarterly' | 'annual' | 'urgent';
  location?: 'onsite' | 'remote';
  status?: 'planned' | 'completed' | 'cancelled' | 'postponed';
  notes?: string;
  actual_date?: string;
  duration_hours?: number;
}

export interface RssiAction {
  id: number;
  client_id: number;
  title: string;
  description: string | null;
  category: 'governance' | 'technical' | 'training' | 'compliance' | null;
  priority: 'critical' | 'high' | 'medium' | 'low';
  status: 'open' | 'in_progress' | 'done' | 'cancelled' | 'postponed';
  assigned_to: string | null;
  due_date: string | null;
  completed_at: string | null;
  source_visit_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface RssiActionCreate {
  title: string;
  description?: string;
  category?: 'governance' | 'technical' | 'training' | 'compliance';
  priority?: 'critical' | 'high' | 'medium' | 'low';
  assigned_to?: string;
  due_date?: string;
  source_visit_id?: number;
}

export interface RssiActionUpdate extends Partial<RssiActionCreate> {
  status?: 'open' | 'in_progress' | 'done' | 'cancelled' | 'postponed';
  completed_at?: string;
}

// ── Dashboard types (Sprint 2) ────────────────────────────────────────────────

export interface DashboardOverview {
  total_clients: number;
  total_mrr: number;
  open_actions: number;
  overdue_actions: number;
  renewals_upcoming: number;
  upcoming_visits: number;
}

export interface ClientSummary {
  id: number;
  name: string;
  formula: 'essentiel' | 'premium' | 'excellence' | null;
  monthly_amount: number | null;
  status: 'active' | 'inactive' | 'churned';
  contract_renewal_at: string | null;
  open_actions: number;
  overdue_actions: number;
  next_visit: string | null;
}

export interface DashboardAlert {
  type: 'overdue_action' | 'renewal_upcoming' | 'no_recent_visit';
  severity: 'critical' | 'high' | 'medium';
  client_id: number;
  client_name: string;
  title: string;
  detail: string;
}

export interface CalendarEvent {
  visit_id: number;
  client_id: number;
  client_name: string;
  scheduled_date: string;
  visit_type: 'monthly' | 'quarterly' | 'annual' | 'urgent';
  location: 'onsite' | 'remote';
}

export interface DashboardSuggestion {
  type: 'upsell_opportunity' | 'engagement_alert' | 'renewal_upcoming' | 'high_overdue';
  client_id: number;
  client_name: string;
  title: string;
  reason: string;
  cta: string;
}

export type ActivityActionType =
  | 'view_client' | 'view_sites' | 'view_scans' | 'view_findings'
  | 'generate_report' | 'send_deliverable'
  | 'create_action' | 'update_action'
  | 'create_visit' | 'update_visit';

export interface RssiSite {
  id: number;
  url: string;
  name: string;
  is_active: boolean;
  created_at: string;
  latest_scan_status: 'OK' | 'WARNING' | 'CRITICAL' | null;
  last_scan_at: string | null;
}

export interface UnlinkedSite {
  id: number;
  url: string;
  name: string;
}

export type DeliverableDocType = 'compte_rendu' | 'rapport' | 'recommandation' | 'contrat' | 'autre';

export interface RssiDeliverable {
  id: number;
  client_id: number;
  title: string;
  doc_type: DeliverableDocType;
  file_url: string | null;
  notes: string | null;
  delivered_at: string;
  created_at: string;
  updated_at: string;
}

export interface RssiDeliverableCreate {
  title: string;
  doc_type?: DeliverableDocType;
  file_url?: string;
  notes?: string;
  delivered_at: string;
}

export interface RssiDeliverableUpdate {
  title?: string;
  doc_type?: DeliverableDocType;
  file_url?: string;
  notes?: string;
  delivered_at?: string;
}

export interface ConsultantProfile {
  email: string;
  display_name: string | null;
  company_name: string | null;
  phone: string | null;
}

export interface ConsultantProfileUpdate {
  display_name?: string | null;
  company_name?: string | null;
  phone?: string | null;
}

export interface ActivityLogCreate {
  action_type: ActivityActionType;
  resource_type?: string;
  resource_id?: number;
}

export interface ActivityLogEntry {
  id: number;
  consultant_id: number;
  client_id: number;
  action_type: ActivityActionType;
  resource_type: string | null;
  resource_id: number | null;
  performed_at: string;
}

const API = '/api/v1/rssi';

@Injectable({ providedIn: 'root' })
export class RssiService {
  private http = inject(HttpClient);

  // ── Clients ──────────────────────────────────────────────────────────────────

  getClients(): Observable<RssiClient[]> {
    return this.http.get<RssiClient[]>(`${API}/clients`);
  }

  getClient(id: number): Observable<RssiClient> {
    return this.http.get<RssiClient>(`${API}/clients/${id}`);
  }

  createClient(data: RssiClientCreate): Observable<RssiClient> {
    return this.http.post<RssiClient>(`${API}/clients`, data);
  }

  updateClient(id: number, data: RssiClientUpdate): Observable<RssiClient> {
    return this.http.put<RssiClient>(`${API}/clients/${id}`, data);
  }

  deleteClient(id: number): Observable<void> {
    return this.http.delete<void>(`${API}/clients/${id}`);
  }

  // ── Visits ───────────────────────────────────────────────────────────────────

  getVisits(clientId: number): Observable<RssiVisit[]> {
    return this.http.get<RssiVisit[]>(`${API}/clients/${clientId}/visits`);
  }

  createVisit(clientId: number, data: RssiVisitCreate): Observable<RssiVisit> {
    return this.http.post<RssiVisit>(`${API}/clients/${clientId}/visits`, data);
  }

  updateVisit(clientId: number, visitId: number, data: RssiVisitUpdate): Observable<RssiVisit> {
    return this.http.put<RssiVisit>(`${API}/clients/${clientId}/visits/${visitId}`, data);
  }

  deleteVisit(clientId: number, visitId: number): Observable<void> {
    return this.http.delete<void>(`${API}/clients/${clientId}/visits/${visitId}`);
  }

  // ── Actions ──────────────────────────────────────────────────────────────────

  getActions(clientId: number, statusFilter?: string): Observable<RssiAction[]> {
    const params: Record<string, string> = statusFilter ? { status_filter: statusFilter } : {};
    return this.http.get<RssiAction[]>(`${API}/clients/${clientId}/actions`, { params });
  }

  createAction(clientId: number, data: RssiActionCreate): Observable<RssiAction> {
    return this.http.post<RssiAction>(`${API}/clients/${clientId}/actions`, data);
  }

  updateAction(clientId: number, actionId: number, data: RssiActionUpdate): Observable<RssiAction> {
    return this.http.put<RssiAction>(`${API}/clients/${clientId}/actions/${actionId}`, data);
  }

  deleteAction(clientId: number, actionId: number): Observable<void> {
    return this.http.delete<void>(`${API}/clients/${clientId}/actions/${actionId}`);
  }

  // ── Dashboard (Sprint 2) ────────────────────────────────────────────────────

  getDashboardOverview(): Observable<DashboardOverview> {
    return this.http.get<DashboardOverview>(`${API}/dashboard/overview`);
  }

  getClientsSummary(): Observable<ClientSummary[]> {
    return this.http.get<ClientSummary[]>(`${API}/dashboard/clients-summary`);
  }

  getDashboardAlerts(): Observable<DashboardAlert[]> {
    return this.http.get<DashboardAlert[]>(`${API}/dashboard/alerts`);
  }

  getUpcomingEvents(daysAhead = 14): Observable<CalendarEvent[]> {
    return this.http.get<CalendarEvent[]>(`${API}/dashboard/upcoming-events`, {
      params: { days_ahead: daysAhead },
    });
  }

  getSuggestions(): Observable<DashboardSuggestion[]> {
    return this.http.get<DashboardSuggestion[]>(`${API}/dashboard/suggestions`);
  }

  // ── PDF report (Sprint 5) ───────────────────────────────────────────────────

  downloadReport(clientId: number): Observable<Blob> {
    return this.http.get(`${API}/clients/${clientId}/report`, { responseType: 'blob' });
  }

  // ── Activity log (Sprint 3) ─────────────────────────────────────────────────

  logActivity(clientId: number, data: ActivityLogCreate): Observable<ActivityLogEntry> {
    return this.http.post<ActivityLogEntry>(`${API}/clients/${clientId}/activity`, data);
  }

  getActivityLog(clientId: number, limit = 50): Observable<ActivityLogEntry[]> {
    return this.http.get<ActivityLogEntry[]>(`${API}/clients/${clientId}/activity`, {
      params: { limit },
    });
  }

  // ── Sites (Sprint 5C + P1) ─────────────────────────────────────────────────

  getClientSites(clientId: number): Observable<RssiSite[]> {
    return this.http.get<RssiSite[]>(`${API}/clients/${clientId}/sites`);
  }

  getUnlinkedSites(): Observable<UnlinkedSite[]> {
    return this.http.get<UnlinkedSite[]>(`${API}/sites/unlinked`);
  }

  linkSite(clientId: number, siteId: number): Observable<RssiSite> {
    return this.http.put<RssiSite>(`${API}/clients/${clientId}/sites/${siteId}`, {});
  }

  unlinkSite(clientId: number, siteId: number): Observable<void> {
    return this.http.delete<void>(`${API}/clients/${clientId}/sites/${siteId}`);
  }

  // ── Deliverables (Sprint 5A) ────────────────────────────────────────────────

  getDeliverables(clientId: number): Observable<RssiDeliverable[]> {
    return this.http.get<RssiDeliverable[]>(`${API}/clients/${clientId}/deliverables`);
  }

  createDeliverable(clientId: number, data: RssiDeliverableCreate): Observable<RssiDeliverable> {
    return this.http.post<RssiDeliverable>(`${API}/clients/${clientId}/deliverables`, data);
  }

  updateDeliverable(clientId: number, deliverableId: number, data: RssiDeliverableUpdate): Observable<RssiDeliverable> {
    return this.http.put<RssiDeliverable>(`${API}/clients/${clientId}/deliverables/${deliverableId}`, data);
  }

  deleteDeliverable(clientId: number, deliverableId: number): Observable<void> {
    return this.http.delete<void>(`${API}/clients/${clientId}/deliverables/${deliverableId}`);
  }

  // ── Consultant profile (P6) ─────────────────────────────────────────────────

  getProfile(): Observable<ConsultantProfile> {
    return this.http.get<ConsultantProfile>(`${API}/profile`);
  }

  updateProfile(data: ConsultantProfileUpdate): Observable<ConsultantProfile> {
    return this.http.patch<ConsultantProfile>(`${API}/profile`, data);
  }

  // ── CSV export (P7) ─────────────────────────────────────────────────────────

  exportActionsCsv(clientId: number): Observable<Blob> {
    return this.http.get(`${API}/clients/${clientId}/actions/export`, { responseType: 'blob' });
  }

  // ── File upload / download (P8) ─────────────────────────────────────────────

  uploadDeliverableFile(clientId: number, file: File): Observable<{ key: string; filename: string }> {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<{ key: string; filename: string }>(
      `${API}/clients/${clientId}/deliverables/upload`, form
    );
  }

  getDeliverableDownloadUrl(clientId: number, deliverableId: number): Observable<{ url: string }> {
    return this.http.get<{ url: string }>(
      `${API}/clients/${clientId}/deliverables/${deliverableId}/download`
    );
  }
}
