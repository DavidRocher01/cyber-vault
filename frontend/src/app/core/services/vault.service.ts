import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

export type VaultCategory = 'login' | 'card' | 'note' | 'wifi' | 'other';

export interface VaultItem {
  id: number;
  title: string;
  username: string | null;
  password_encrypted: string;
  url: string | null;
  notes: string | null;
  category: VaultCategory;
}

export interface VaultItemCreate {
  title: string;
  username?: string;
  password_encrypted: string;
  url?: string;
  notes?: string;
  category?: VaultCategory;
}

const API = environment.apiUrl;

@Injectable({ providedIn: 'root' })
export class VaultService {
  constructor(private http: HttpClient) {}

  getAll() {
    return this.http.get<VaultItem[]>(`${API}/vault/`);
  }

  create(payload: VaultItemCreate) {
    return this.http.post<VaultItem>(`${API}/vault/`, payload);
  }

  update(id: number, payload: Partial<VaultItemCreate>) {
    return this.http.patch<VaultItem>(`${API}/vault/${id}`, payload);
  }

  delete(id: number) {
    return this.http.delete(`${API}/vault/${id}`);
  }
}
