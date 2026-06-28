import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class CryptoService {
  private static readonly ITERATIONS = 600_000;

  private key: CryptoKey | null = null;

  hasKey(): boolean {
    return !!this.key;
  }

  /**
   * Derive the vault encryption key from the master password.
   * @param masterPassword  User-supplied master password (never sent to server)
   * @param saltOrEmail     Prefer the base64-encoded crypto_salt from the server.
   *                        Falls back to email if salt is not yet available (legacy sessions).
   * @param iterations      PBKDF2 iteration count
   */
  async deriveKey(
    masterPassword: string,
    saltOrEmail: string,
    iterations = CryptoService.ITERATIONS
  ): Promise<void> {
    const enc = new TextEncoder();
    let saltBytes: Uint8Array;
    try {
      // If saltOrEmail is base64 (44 chars for 32 bytes), decode it; otherwise treat as email string
      if (/^[A-Za-z0-9+/]{43}=?$/.test(saltOrEmail)) {
        saltBytes = Uint8Array.from(atob(saltOrEmail), c => c.charCodeAt(0));
      } else {
        saltBytes = enc.encode(saltOrEmail);
      }
    } catch {
      saltBytes = enc.encode(saltOrEmail);
    }
    const keyMaterial = await crypto.subtle.importKey(
      'raw',
      enc.encode(masterPassword),
      'PBKDF2',
      false,
      ['deriveKey']
    );
    this.key = await crypto.subtle.deriveKey(
      { name: 'PBKDF2', salt: saltBytes, iterations, hash: 'SHA-256' },
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
    const ciphertext = await crypto.subtle.encrypt(
      { name: 'AES-GCM', iv },
      this.key,
      enc.encode(plaintext)
    );
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
    try {
      return await this.decrypt(encryptedBase64);
    } catch {
      return null;
    }
  }

  clearKey(): void {
    this.key = null;
  }
}
