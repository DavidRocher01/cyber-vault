import { Injectable, signal } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class AdminAuthService {
  private readonly STORAGE_KEY = 'admin_key';

  authenticated = signal(false);
  adminKey = signal('');

  constructor(private http: HttpClient) {
    const stored = sessionStorage.getItem(this.STORAGE_KEY);
    if (stored) {
      this.adminKey.set(stored);
      this.authenticated.set(true);
    }
  }

  headers(): HttpHeaders {
    return new HttpHeaders({ 'X-Admin-Key': this.adminKey() });
  }

  verify(key: string): Observable<unknown> {
    return this.http.get('/api/v1/admin/stats', {
      headers: new HttpHeaders({ 'X-Admin-Key': key }),
    });
  }

  login(key: string): void {
    this.adminKey.set(key);
    this.authenticated.set(true);
    sessionStorage.setItem(this.STORAGE_KEY, key);
  }

  logout(): void {
    this.adminKey.set('');
    this.authenticated.set(false);
    sessionStorage.removeItem(this.STORAGE_KEY);
  }
}
