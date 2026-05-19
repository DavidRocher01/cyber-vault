import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface DarkwebBreach {
  name: string;
  domain: string;
  breach_date: string;
  pwn_count: number;
  data_classes: string[];
  is_sensitive: boolean;
}

export interface DarkwebStatus {
  email: string;
  total_breaches: number;
  status: string;
  checked_at: string | null;
  breaches: DarkwebBreach[];
  error: string | null;
  fresh: boolean;
}

const API = '/api/v1/darkweb';

@Injectable({ providedIn: 'root' })
export class DarkwebService {
  private http = inject(HttpClient);

  getStatus(): Observable<DarkwebStatus> {
    return this.http.get<DarkwebStatus>(`${API}/status`);
  }

  runCheck(): Observable<DarkwebStatus> {
    return this.http.post<DarkwebStatus>(`${API}/check`, {});
  }
}
