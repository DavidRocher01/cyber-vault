import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface UserProfile {
  id: number;
  email: string;
  is_active: boolean;
  totp_enabled: boolean;
}

export interface NotificationPreferences {
  notif_scan_done: boolean;
  notif_scan_critical: boolean;
  notif_url_scan_done: boolean;
  notif_code_scan_done: boolean;
  notif_ssl_expiry: boolean;
}

export interface TwoFactorSetup {
  qr_code_b64: string;
  secret: string;
}

const API = '/api/v1';

@Injectable({ providedIn: 'root' })
export class UserService {
  private http = inject(HttpClient);

  getProfile(): Observable<UserProfile> {
    return this.http.get<UserProfile>(`${API}/users/me`);
  }

  updateEmail(email: string, currentPassword: string): Observable<UserProfile> {
    return this.http.put<UserProfile>(`${API}/users/me/email`, { email, current_password: currentPassword });
  }

  updatePassword(currentPassword: string, newPassword: string): Observable<void> {
    return this.http.put<void>(`${API}/users/me/password`, { current_password: currentPassword, new_password: newPassword });
  }

  setup2FA(): Observable<TwoFactorSetup> {
    return this.http.post<TwoFactorSetup>(`${API}/users/me/2fa/setup`, {});
  }

  enable2FA(code: string): Observable<UserProfile> {
    return this.http.post<UserProfile>(`${API}/users/me/2fa/enable`, { code });
  }

  disable2FA(password: string, code: string): Observable<UserProfile> {
    return this.http.post<UserProfile>(`${API}/users/me/2fa/disable`, { password, code });
  }

  exportMyData(): string {
    return `${API}/users/me/export`;
  }

  exportMyDataBlob(): Observable<Blob> {
    return this.http.get(`${API}/users/me/export`, { responseType: 'blob' });
  }

  deleteAccount(password: string): Observable<void> {
    return this.http.delete<void>(`${API}/users/me`, { body: { password } });
  }

  getNotificationPreferences(): Observable<NotificationPreferences> {
    return this.http.get<NotificationPreferences>(`${API}/users/me/notification-preferences`);
  }

  updateNotificationPreferences(prefs: NotificationPreferences): Observable<NotificationPreferences> {
    return this.http.put<NotificationPreferences>(`${API}/users/me/notification-preferences`, prefs);
  }
}
