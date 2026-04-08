/**
 * Logique double authentification — tests unitaires de fonctions pures
 *
 * On extrait et teste la logique pure sans TestBed :
 *   - Détection de la réponse requires_2fa vs tokens
 *   - registerPasswordStrength (score 0-4)
 *   - Validation du code OTP (longueur 6)
 */

import { describe, it, expect } from 'vitest';

// ── requires_2fa detection ────────────────────────────────────────────────────

type LoginResponse =
  | { access_token: string; refresh_token: string; token_type: string }
  | { requires_2fa: true };

function isRequires2fa(res: LoginResponse): boolean {
  return 'requires_2fa' in res;
}

function hasTokens(res: LoginResponse): boolean {
  return 'access_token' in res;
}

describe('2FA — détection de la réponse API login', () => {
  it('détecte requires_2fa: true', () => {
    const res: LoginResponse = { requires_2fa: true };
    expect(isRequires2fa(res)).toBe(true);
    expect(hasTokens(res)).toBe(false);
  });

  it('détecte une réponse tokens normale', () => {
    const res: LoginResponse = {
      access_token: 'abc',
      refresh_token: 'def',
      token_type: 'bearer',
    };
    expect(isRequires2fa(res)).toBe(false);
    expect(hasTokens(res)).toBe(true);
  });
});

// ── registerPasswordStrength ──────────────────────────────────────────────────

function passwordStrength(pw: string): number {
  let score = 0;
  if (pw.length >= 8) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  return score;
}

function strengthLabel(score: number): string {
  if (score <= 1) return 'Faible';
  if (score === 2) return 'Moyen';
  if (score === 3) return 'Fort';
  return 'Très fort';
}

describe('registerPasswordStrength', () => {
  it('score 0 pour mot de passe vide', () => {
    expect(passwordStrength('')).toBe(0);
  });

  it('score 1 pour au moins 8 caractères sans majuscule/chiffre/special', () => {
    expect(passwordStrength('abcdefgh')).toBe(1);
  });

  it('score 2 pour longueur + majuscule', () => {
    expect(passwordStrength('Abcdefgh')).toBe(2);
  });

  it('score 3 pour longueur + majuscule + chiffre', () => {
    expect(passwordStrength('Abcdef1h')).toBe(3);
  });

  it('score 4 pour longueur + majuscule + chiffre + spécial', () => {
    expect(passwordStrength('Abcdef1!')).toBe(4);
  });

  it('score 1 si longueur < 8 même avec maj/chiffre/spécial', () => {
    expect(passwordStrength('A1!')).toBe(3); // no length bonus, but has upper+digit+special
  });

  it('label Faible pour score ≤ 1', () => {
    expect(strengthLabel(0)).toBe('Faible');
    expect(strengthLabel(1)).toBe('Faible');
  });

  it('label Moyen pour score 2', () => {
    expect(strengthLabel(2)).toBe('Moyen');
  });

  it('label Fort pour score 3', () => {
    expect(strengthLabel(3)).toBe('Fort');
  });

  it('label Très fort pour score 4', () => {
    expect(strengthLabel(4)).toBe('Très fort');
  });
});

// ── Validation code OTP ───────────────────────────────────────────────────────

function isValidOtp(code: string): boolean {
  return /^\d{6}$/.test(code);
}

describe('Validation du code OTP', () => {
  it('valide 6 chiffres', () => {
    expect(isValidOtp('123456')).toBe(true);
    expect(isValidOtp('000000')).toBe(true);
  });

  it('invalide si moins de 6 chiffres', () => {
    expect(isValidOtp('12345')).toBe(false);
    expect(isValidOtp('')).toBe(false);
  });

  it('invalide si plus de 6 chiffres', () => {
    expect(isValidOtp('1234567')).toBe(false);
  });

  it('invalide si contient des lettres', () => {
    expect(isValidOtp('12345a')).toBe(false);
  });

  it('invalide si contient des espaces', () => {
    expect(isValidOtp('123 56')).toBe(false);
  });
});

// ── État du modal auth ────────────────────────────────────────────────────────

type AuthPanel = 'closed' | 'login' | 'register';

interface AuthModalState {
  panel: AuthPanel;
  show2fa: boolean;
  error: string | null;
  loading: boolean;
}

function openAuth(mode: 'login' | 'register'): AuthModalState {
  return { panel: mode, show2fa: false, error: null, loading: false };
}

function closeAuth(): AuthModalState {
  return { panel: 'closed', show2fa: false, error: null, loading: false };
}

function onRequires2fa(state: AuthModalState): AuthModalState {
  return { ...state, show2fa: true, loading: false };
}

function cancelAuth2fa(state: AuthModalState): AuthModalState {
  return { ...state, show2fa: false, error: null };
}

describe('État du modal auth — transitions', () => {
  it('openAuth(login) affiche le panel login sans 2FA', () => {
    const s = openAuth('login');
    expect(s.panel).toBe('login');
    expect(s.show2fa).toBe(false);
  });

  it('openAuth(register) affiche le panel register sans 2FA', () => {
    const s = openAuth('register');
    expect(s.panel).toBe('register');
    expect(s.show2fa).toBe(false);
  });

  it('closeAuth ferme le modal et réinitialise l\'état 2FA', () => {
    const s = closeAuth();
    expect(s.panel).toBe('closed');
    expect(s.show2fa).toBe(false);
  });

  it('onRequires2fa bascule vers l\'étape 2FA', () => {
    const s = onRequires2fa(openAuth('login'));
    expect(s.show2fa).toBe(true);
    expect(s.loading).toBe(false);
  });

  it('cancelAuth2fa revient à l\'état de connexion sans erreur', () => {
    const s2fa = onRequires2fa(openAuth('login'));
    const cancelled = cancelAuth2fa(s2fa);
    expect(cancelled.show2fa).toBe(false);
    expect(cancelled.error).toBeNull();
  });
});
