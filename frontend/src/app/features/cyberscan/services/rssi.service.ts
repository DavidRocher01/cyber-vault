import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface RssiClient {
  id: number;
  name: string;
  email: string | null;
  description: string | null;
  created_at: string;
  sites_count: number;
  worst_status: 'OK' | 'WARNING' | 'CRITICAL' | null;
  last_scan_at: string | null;
}

export interface RssiClientCreate {
  name: string;
  email?: string;
  description?: string;
}

const API = '/api/v1/rssi';

@Injectable({ providedIn: 'root' })
export class RssiService {
  private http = inject(HttpClient);

  getClients(): Observable<RssiClient[]> {
    return this.http.get<RssiClient[]>(`${API}/clients`);
  }

  createClient(data: RssiClientCreate): Observable<RssiClient> {
    return this.http.post<RssiClient>(`${API}/clients`, data);
  }

  updateClient(id: number, data: Partial<RssiClientCreate>): Observable<RssiClient> {
    return this.http.put<RssiClient>(`${API}/clients/${id}`, data);
  }

  deleteClient(id: number): Observable<void> {
    return this.http.delete<void>(`${API}/clients/${id}`);
  }
}
