import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { tap } from 'rxjs';

const ACCESS_KEY = 'cv_token';
const EMAIL_KEY = 'cv_email';
const API = '/api/v1';

export interface AccessTokenResponse {
  access_token: string;
  token_type: string;
}

export type LoginResponse = AccessTokenResponse | { requires_2fa: true };

@Injectable({ providedIn: 'root' })
export class AuthService {
  constructor(
    private http: HttpClient,
    private router: Router
  ) {}

  login(email: string, password: string, totpCode?: string) {
    const body: Record<string, string> = { email, password };
    if (totpCode) body['totp_code'] = totpCode;
    return this.http.post<LoginResponse>(`${API}/auth/login`, body, { withCredentials: true }).pipe(
      tap(res => {
        if ('access_token' in res) {
          localStorage.setItem(ACCESS_KEY, res.access_token);
          localStorage.setItem(EMAIL_KEY, email);
        }
      })
    );
  }

  register(email: string, password: string) {
    return this.http.post(`${API}/auth/register`, { email, password });
  }

  refresh() {
    // refresh_token is sent automatically as httpOnly cookie
    return this.http
      .post<AccessTokenResponse>(`${API}/auth/refresh`, {}, { withCredentials: true })
      .pipe(
        tap(res => {
          localStorage.setItem(ACCESS_KEY, res.access_token);
        })
      );
  }

  logout() {
    // refresh_token cookie is sent automatically; server revokes + clears it
    this.http
      .post(`${API}/auth/logout`, {}, { withCredentials: true })
      .subscribe({ error: () => {} });
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(EMAIL_KEY);
    this.router.navigate(['/cyberscan']);
  }

  getToken(): string | null {
    return localStorage.getItem(ACCESS_KEY);
  }

  getCurrentEmail(): string | null {
    return localStorage.getItem(EMAIL_KEY);
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }
}
