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

const API = '/api/v1/rssi';

@Injectable({ providedIn: 'root' })
export class RssiService {
  private http = inject(HttpClient);

  // ── Clients ──────────────────────────────────────────────────────────────────

  getClients(): Observable<RssiClient[]> {
    return this.http.get<RssiClient[]>(`${API}/clients`);
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
    const params = statusFilter ? { status_filter: statusFilter } : {};
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
}
