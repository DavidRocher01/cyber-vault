import { Injectable, PLATFORM_ID, Inject } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { tap } from 'rxjs';

// access_token et crypto_salt en sessionStorage (XSS safer — disparaissent à la fermeture de l'onglet)
// Le refresh_token httpOnly cookie assure la persistance entre sessions
const ACCESS_KEY = 'cv_token';
const EMAIL_KEY = 'cv_email'; // localStorage : non sensible, identification UI
const CRYPTO_SALT_KEY = 'cv_crypto_salt';
const API = '/api/v1';

// SSR-safe storage stubs
const noopStorage: Storage = {
  length: 0,
  clear() {},
  getItem() {
    return null;
  },
  key() {
    return null;
  },
  removeItem() {},
  setItem() {},
};

export interface AccessTokenResponse {
  access_token: string;
  token_type: string;
  crypto_salt?: string | null;
}

export type LoginResponse = AccessTokenResponse | { requires_2fa: true };

export interface CurrentUser {
  id: number;
  email: string;
  is_active: boolean;
  totp_enabled: boolean;
  is_rssi_consultant: boolean;
  is_portal_client: boolean;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private get session(): Storage {
    return isPlatformBrowser(this.platformId) ? sessionStorage : noopStorage;
  }
  private get local(): Storage {
    return isPlatformBrowser(this.platformId) ? localStorage : noopStorage;
  }

  constructor(
    private http: HttpClient,
    private router: Router,
    @Inject(PLATFORM_ID) private platformId: object
  ) {}

  login(email: string, password: string, totpCode?: string) {
    const body: Record<string, string> = { email, password };
    if (totpCode) body['totp_code'] = totpCode;
    return this.http.post<LoginResponse>(`${API}/auth/login`, body, { withCredentials: true }).pipe(
      tap(res => {
        if ('access_token' in res) {
          this.session.setItem(ACCESS_KEY, res.access_token);
          this.local.setItem(EMAIL_KEY, email);
          if (res.crypto_salt) {
            this.session.setItem(CRYPTO_SALT_KEY, res.crypto_salt);
          }
        }
      })
    );
  }

  register(email: string, password: string) {
    return this.http.post(`${API}/auth/register`, { email, password });
  }

  me() {
    return this.http.get<CurrentUser>(`${API}/users/me`, { withCredentials: true });
  }

  refresh() {
    // refresh_token is sent automatically as httpOnly cookie
    return this.http
      .post<AccessTokenResponse>(`${API}/auth/refresh`, {}, { withCredentials: true })
      .pipe(
        tap(res => {
          this.session.setItem(ACCESS_KEY, res.access_token);
          if (res.crypto_salt) this.session.setItem(CRYPTO_SALT_KEY, res.crypto_salt);
        })
      );
  }

  logout() {
    // refresh_token cookie is sent automatically; server revokes + clears it
    this.http
      .post(`${API}/auth/logout`, {}, { withCredentials: true })
      .subscribe({ error: () => {} });
    this.session.removeItem(ACCESS_KEY);
    this.session.removeItem(CRYPTO_SALT_KEY);
    this.local.removeItem(EMAIL_KEY);
    this.router.navigate(['/']);
  }

  getToken(): string | null {
    return this.session.getItem(ACCESS_KEY);
  }

  getCurrentEmail(): string | null {
    return this.local.getItem(EMAIL_KEY);
  }

  getCryptoSalt(): string | null {
    return this.session.getItem(CRYPTO_SALT_KEY);
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }
}
