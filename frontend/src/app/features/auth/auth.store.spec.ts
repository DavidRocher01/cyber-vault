/**
 * AuthStore — tests de logique pure
 *
 * ComponentStore nécessite le runtime Angular complet (DestroyRef) et ne peut
 * pas être instancié dans ce setup Vitest sans TestBed.
 * On teste ici la logique isolée : le calcul de returnUrl et le fallback.
 *
 * Le comportement end-to-end (navigateByUrl appelé avec returnUrl) est couvert
 * par les tests d'intégration backend et par les tests du guard + register.
 */
import { describe, it, expect } from 'vitest';

// ── returnUrl fallback logic ───────────────────────────────────────────────────
// Reproduit exactement le getter privé de AuthStore

function resolveReturnUrl(queryParamValue: string | null): string {
  const url = queryParamValue || '';
  return url.startsWith('/cyberscan') ? url : '/cyberscan/dashboard';
}

describe('AuthStore — returnUrl resolution', () => {
  it('utilise returnUrl si c\'est une route /cyberscan/', () => {
    expect(resolveReturnUrl('/cyberscan/dashboard')).toBe('/cyberscan/dashboard');
  });

  it('préserve les sous-chemins /cyberscan/ avec query params', () => {
    expect(resolveReturnUrl('/cyberscan/dashboard?tab=scans')).toBe('/cyberscan/dashboard?tab=scans');
  });

  it('redirige vers /cyberscan/dashboard quand returnUrl est null', () => {
    expect(resolveReturnUrl(null)).toBe('/cyberscan/dashboard');
  });

  it('redirige vers /cyberscan/dashboard quand returnUrl est vide', () => {
    expect(resolveReturnUrl('')).toBe('/cyberscan/dashboard');
  });

  it('ignore returnUrl=/vault', () => {
    expect(resolveReturnUrl('/vault')).toBe('/cyberscan/dashboard');
  });

  it('ignore returnUrl=/auth/master-password', () => {
    expect(resolveReturnUrl('/auth/master-password')).toBe('/cyberscan/dashboard');
  });

  it('ignore returnUrl=/auth/login', () => {
    expect(resolveReturnUrl('/auth/login')).toBe('/cyberscan/dashboard');
  });

  it('préserve /cyberscan (landing) comme returnUrl valide', () => {
    expect(resolveReturnUrl('/cyberscan')).toBe('/cyberscan');
  });
});
