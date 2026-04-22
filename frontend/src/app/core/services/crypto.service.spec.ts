import { describe, it, expect, beforeEach } from 'vitest';
import { CryptoService } from './crypto.service';

// Low iteration count so PBKDF2 doesn't slow down the test suite.
const ITER = 1_000;

describe('CryptoService', () => {
  let service: CryptoService;

  beforeEach(() => {
    service = new CryptoService();
  });

  it('hasKey() retourne false avant dérivation', () => {
    expect(service.hasKey()).toBe(false);
  });

  it('hasKey() retourne true après deriveKey()', async () => {
    await service.deriveKey('masterpass123', 'user@test.com', ITER);
    expect(service.hasKey()).toBe(true);
  });

  it('encrypt/decrypt est un round-trip correct', async () => {
    await service.deriveKey('masterpass123', 'user@test.com', ITER);
    const plain = 'monMotDePasse!@#';
    const encrypted = await service.encrypt(plain);
    expect(encrypted).not.toBe(plain);
    const decrypted = await service.decrypt(encrypted);
    expect(decrypted).toBe(plain);
  });

  it('deux chiffrements identiques donnent des ciphertexts différents (IV aléatoire)', async () => {
    await service.deriveKey('masterpass123', 'user@test.com', ITER);
    const a = await service.encrypt('test');
    const b = await service.encrypt('test');
    expect(a).not.toBe(b);
  });

  it('clearKey() remet hasKey() à false', async () => {
    await service.deriveKey('masterpass123', 'user@test.com', ITER);
    service.clearKey();
    expect(service.hasKey()).toBe(false);
  });

  it('deux emails différents → clés différentes → déchiffrement échoue', async () => {
    await service.deriveKey('masterpass123', 'user@test.com', ITER);
    const encrypted = await service.encrypt('secret');
    await service.deriveKey('masterpass123', 'autre@test.com', ITER);
    await expect(service.decrypt(encrypted)).rejects.toThrow();
  });

  it('tryDecrypt retourne null au lieu de lever une exception', async () => {
    await service.deriveKey('masterpass123', 'user@test.com', ITER);
    const encrypted = await service.encrypt('secret');
    await service.deriveKey('masterpass123', 'autre@test.com', ITER);
    expect(await service.tryDecrypt(encrypted)).toBeNull();
  });
});
