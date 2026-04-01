import { describe, it, expect, beforeEach } from 'vitest';
import { PasswordGeneratorService } from './password-generator.service';

describe('PasswordGeneratorService', () => {
  let service: PasswordGeneratorService;

  beforeEach(() => {
    service = new PasswordGeneratorService();
  });

  it('génère un mot de passe de la longueur demandée', () => {
    expect(service.generate(16)).toHaveLength(16);
    expect(service.generate(32)).toHaveLength(32);
  });

  it('deux appels successifs donnent des résultats différents', () => {
    expect(service.generate()).not.toBe(service.generate());
  });

  it('n\'utilise que des caractères du charset autorisé', () => {
    const pwd = service.generate(200);
    expect(pwd).toMatch(/^[a-zA-Z0-9!@#$%^&*()\-_+=\[\]{}|;:,.<>?]+$/);
  });

  it('la longueur par défaut est 16', () => {
    expect(service.generate()).toHaveLength(16);
  });
});
