import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface UserProfile {
  id: number;
  email: string;
  is_active: boolean;
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
}
