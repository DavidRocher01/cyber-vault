import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Collaborator {
  id: number;
  site_id: number;
  email: string;
  role: string;
  status: string;
  invited_at: string;
  accepted_at: string | null;
}

const API = '/api/v1/collab';

@Injectable({ providedIn: 'root' })
export class CollabService {
  private http = inject(HttpClient);

  list(siteId: number): Observable<Collaborator[]> {
    return this.http.get<Collaborator[]>(`${API}/sites/${siteId}/collaborators`);
  }

  invite(siteId: number, email: string, role: string): Observable<Collaborator> {
    return this.http.post<Collaborator>(`${API}/sites/${siteId}/collaborators`, { email, role });
  }

  updateRole(siteId: number, collabId: number, role: string): Observable<Collaborator> {
    return this.http.put<Collaborator>(`${API}/sites/${siteId}/collaborators/${collabId}`, {
      role,
    });
  }

  remove(siteId: number, collabId: number): Observable<void> {
    return this.http.delete<void>(`${API}/sites/${siteId}/collaborators/${collabId}`);
  }

  acceptInvite(token: string): Observable<Collaborator> {
    return this.http.get<Collaborator>(`${API}/accept/${token}`);
  }
}
