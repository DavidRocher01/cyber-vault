import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { tap } from 'rxjs';
import { environment } from '../../../environments/environment';

const TOKEN_KEY = 'cv_token';
const API = environment.apiUrl;

@Injectable({ providedIn: 'root' })
export class AuthService {
  constructor(private http: HttpClient) {}

  login(email: string, password: string) {
    return this.http.post<{ access_token: string }>(`${API}/auth/login`, { email, password }).pipe(
      tap(res => localStorage.setItem(TOKEN_KEY, res.access_token))
    );
  }

  register(email: string, password: string) {
    return this.http.post(`${API}/auth/register`, { email, password });
  }

  logout() {
    localStorage.removeItem(TOKEN_KEY);
  }

  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }
}
