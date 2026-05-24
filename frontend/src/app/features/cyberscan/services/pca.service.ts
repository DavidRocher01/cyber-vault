import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface PcaSystem {
  name: string;
  description: string;
  rto_hours: number;
  rpo_hours: number;
  responsible: string;
}

export interface PcaTeamMember {
  name: string;
  role: string;
  phone: string;
  email: string;
}

export interface PcaPayload {
  company: { name: string; sector: string; contact: string; email: string; phone: string };
  critical_systems: PcaSystem[];
  response_team: PcaTeamMember[];
  communication_plan: string;
}

@Injectable({ providedIn: 'root' })
export class PcaService {
  private http = inject(HttpClient);

  generate(payload: PcaPayload): Observable<Blob> {
    return this.http.post('/api/v1/pca/generate', payload, { responseType: 'blob' });
  }
}
