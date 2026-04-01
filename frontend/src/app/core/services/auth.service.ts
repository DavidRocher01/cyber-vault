import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { tap } from 'rxjs';
import { environment } from '../../../environments/environment';

const ACCESS_KEY = 'cv_token';
const REFRESH_KEY = 'cv_refresh';
const EMAIL_KEY = 'cv_email';
const API = environment.apiUrl;

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  constructor(private http: HttpClient) {}

  login(email: string, password: string) {
    return this.http.post<TokenResponse>(`${API}/auth/login`, { email, password }).pipe(
      tap(res => {
        localStorage.setItem(ACCESS_KEY, res.access_token);
        localStorage.setItem(REFRESH_KEY, res.refresh_token);
        localStorage.setItem(EMAIL_KEY, email);
      })
    );
  }

  register(email: string, password: string) {
    return this.http.post(`${API}/auth/register`, { email, password });
  }

  refresh() {
    const refresh_token = this.getRefreshToken();
    if (!refresh_token) throw new Error('No refresh token');
    return this.http.post<TokenResponse>(`${API}/auth/refresh`, { refresh_token }).pipe(
      tap(res => {
        localStorage.setItem(ACCESS_KEY, res.access_token);
        localStorage.setItem(REFRESH_KEY, res.refresh_token);
      })
    );
  }

  logout() {
    const refresh_token = this.getRefreshToken();
    if (refresh_token) {
      this.http.post(`${API}/auth/logout`, { refresh_token }).subscribe({ error: () => {} });
    }
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(EMAIL_KEY);
  }

  getToken(): string | null {
    return localStorage.getItem(ACCESS_KEY);
  }

  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_KEY);
  }

  getCurrentEmail(): string | null {
    return localStorage.getItem(EMAIL_KEY);
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }
}
