import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../../environments/environment';
import { CryptoService } from './crypto.service';

export type VaultCategory = 'login' | 'card' | 'note' | 'wifi' | 'other';

export interface VaultItem {
  id: number;
  title: string | null;
  username: string | null;
  password_encrypted: string;
  url: string | null;
  notes: string | null;
  category: VaultCategory;
  title_encrypted: string | null;
  username_encrypted: string | null;
  url_encrypted: string | null;
  notes_encrypted: string | null;
  // Decrypted display values (populated client-side after decryption)
  _title?: string | null;
  _username?: string | null;
  _url?: string | null;
  _notes?: string | null;
}

export interface VaultItemCreate {
  // Plaintext fields are nullable so legacy migration can clear them server-side.
  title?: string | null;
  username?: string | null;
  password_encrypted: string;
  url?: string | null;
  notes?: string | null;
  category?: VaultCategory;
  title_encrypted?: string;
  username_encrypted?: string;
  url_encrypted?: string;
  notes_encrypted?: string;
}

const API = environment.apiUrl;

@Injectable({ providedIn: 'root' })
export class VaultService {
  constructor(
    private http: HttpClient,
    private crypto: CryptoService
  ) {}

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

  /** Decrypt display fields of a VaultItem. Returns the item with `_title`, `_username`, etc. populated. */
  async decryptItem(item: VaultItem): Promise<VaultItem> {
    const result = { ...item };
    if (item.title_encrypted) {
      result._title = (await this.crypto.tryDecrypt(item.title_encrypted)) ?? item.title;
    } else {
      result._title = item.title;
    }
    if (item.username_encrypted) {
      result._username = await this.crypto.tryDecrypt(item.username_encrypted);
    } else {
      result._username = item.username;
    }
    if (item.url_encrypted) {
      result._url = await this.crypto.tryDecrypt(item.url_encrypted);
    } else {
      result._url = item.url;
    }
    if (item.notes_encrypted) {
      result._notes = await this.crypto.tryDecrypt(item.notes_encrypted);
    } else {
      result._notes = item.notes;
    }
    return result;
  }

  /**
   * Returns a copy of the item with title/username/url/notes set to their
   * decrypted plaintext (in-memory only, never sent back). Legacy items that
   * still carry plaintext but no *_encrypted keep their existing values.
   */
  async hydrateForDisplay(item: VaultItem): Promise<VaultItem> {
    const out = { ...item };
    if (item.title_encrypted)
      out.title = (await this.crypto.tryDecrypt(item.title_encrypted)) ?? item.title;
    if (item.username_encrypted)
      out.username = (await this.crypto.tryDecrypt(item.username_encrypted)) ?? item.username;
    if (item.url_encrypted)
      out.url = (await this.crypto.tryDecrypt(item.url_encrypted)) ?? item.url;
    if (item.notes_encrypted)
      out.notes = (await this.crypto.tryDecrypt(item.notes_encrypted)) ?? item.notes;
    return out;
  }

  /** Encrypt an item's display fields and return a create/update payload with *_encrypted fields. */
  async buildEncryptedPayload(plain: {
    title: string;
    username?: string | null;
    url?: string | null;
    notes?: string | null;
  }): Promise<{
    title_encrypted: string;
    username_encrypted?: string;
    url_encrypted?: string;
    notes_encrypted?: string;
  }> {
    const result: Partial<VaultItemCreate> = {
      title_encrypted: await this.crypto.encrypt(plain.title),
    };
    if (plain.username) result.username_encrypted = await this.crypto.encrypt(plain.username);
    if (plain.url) result.url_encrypted = await this.crypto.encrypt(plain.url);
    if (plain.notes) result.notes_encrypted = await this.crypto.encrypt(plain.notes);
    return result as { title_encrypted: string };
  }

  /**
   * Migrate legacy items that have plaintext title/username/url/notes but no encrypted versions.
   * Called once after successful vault unlock.
   */
  async migrateLegacyItems(): Promise<void> {
    if (!this.crypto.hasKey()) return;
    const items = await firstValueFrom(this.getAll());
    const legacyItems = items.filter(i => !i.title_encrypted);
    for (const item of legacyItems) {
      const encrypted = await this.buildEncryptedPayload({
        title: item.title ?? '',
        username: item.username,
        url: item.url,
        notes: item.notes,
      });
      // Encrypt the legacy fields AND clear the plaintext columns server-side.
      await firstValueFrom(
        this.update(item.id, { ...encrypted, title: null, username: null, url: null, notes: null })
      );
    }
  }
}
