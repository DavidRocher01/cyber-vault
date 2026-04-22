import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class CryptoService {
  private static readonly ITERATIONS = 600_000;

  private key: CryptoKey | null = null;

  hasKey(): boolean {
    return !!this.key;
  }

  async deriveKey(masterPassword: string, email: string, iterations = CryptoService.ITERATIONS): Promise<void> {
    const enc = new TextEncoder();
    const keyMaterial = await crypto.subtle.importKey(
      'raw',
      enc.encode(masterPassword),
      'PBKDF2',
      false,
      ['deriveKey']
    );
    this.key = await crypto.subtle.deriveKey(
      { name: 'PBKDF2', salt: enc.encode(email), iterations, hash: 'SHA-256' },
      keyMaterial,
      { name: 'AES-GCM', length: 256 },
      false,
      ['encrypt', 'decrypt']
    );
  }

  async encrypt(plaintext: string): Promise<string> {
    if (!this.key) throw new Error('Clé de chiffrement non initialisée');
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const enc = new TextEncoder();
    const ciphertext = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, this.key, enc.encode(plaintext));
    const combined = new Uint8Array(iv.byteLength + ciphertext.byteLength);
    combined.set(iv, 0);
    combined.set(new Uint8Array(ciphertext), iv.byteLength);
    return btoa(String.fromCharCode(...combined));
  }

  async decrypt(encryptedBase64: string): Promise<string> {
    if (!this.key) throw new Error('Clé de chiffrement non initialisée');
    const combined = Uint8Array.from(atob(encryptedBase64), c => c.charCodeAt(0));
    const iv = combined.slice(0, 12);
    const ciphertext = combined.slice(12);
    const decrypted = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, this.key, ciphertext);
    return new TextDecoder().decode(decrypted);
  }

  /** Returns null instead of throwing — useful for migration canary checks. */
  async tryDecrypt(encryptedBase64: string): Promise<string | null> {
    try { return await this.decrypt(encryptedBase64); }
    catch { return null; }
  }

  clearKey(): void {
    this.key = null;
  }
}
