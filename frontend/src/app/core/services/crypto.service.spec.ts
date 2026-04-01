import { describe, it, expect, beforeEach } from 'vitest';
import { CryptoService } from './crypto.service';

describe('CryptoService', () => {
  let service: CryptoService;

  beforeEach(() => {
    service = new CryptoService();
  });

  it('hasKey() retourne false avant dérivation', () => {
    expect(service.hasKey()).toBe(false);
  });

  it('hasKey() retourne true après deriveKey()', async () => {
    await service.deriveKey('masterpass123', 'user@test.com');
    expect(service.hasKey()).toBe(true);
  });

  it('encrypt/decrypt est un round-trip correct', async () => {
    await service.deriveKey('masterpass123', 'user@test.com');
    const plain = 'monMotDePasse!@#';
    const encrypted = await service.encrypt(plain);
    expect(encrypted).not.toBe(plain);
    const decrypted = await service.decrypt(encrypted);
    expect(decrypted).toBe(plain);
  });

  it('deux chiffrements identiques donnent des ciphertexts différents (IV aléatoire)', async () => {
    await service.deriveKey('masterpass123', 'user@test.com');
    const a = await service.encrypt('test');
    const b = await service.encrypt('test');
    expect(a).not.toBe(b);
  });

  it('clearKey() remet hasKey() à false', async () => {
    await service.deriveKey('masterpass123', 'user@test.com');
    service.clearKey();
    expect(service.hasKey()).toBe(false);
  });

  it('deux emails différents → clés différentes → déchiffrement échoue', async () => {
    await service.deriveKey('masterpass123', 'user@test.com');
    const encrypted = await service.encrypt('secret');
    await service.deriveKey('masterpass123', 'autre@test.com');
    await expect(service.decrypt(encrypted)).rejects.toThrow();
  });
});
