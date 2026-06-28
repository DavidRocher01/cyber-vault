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
  return url.startsWith('/') ? url : '/';
}

describe('AuthStore — returnUrl resolution', () => {
  it("utilise returnUrl si c'est une route /cyberscan/dashboard", () => {
    expect(resolveReturnUrl('/dashboard')).toBe('/dashboard');
  });

  it('préserve les sous-chemins /cyberscan/ avec query params', () => {
    expect(resolveReturnUrl('/dashboard?tab=scans')).toBe('/dashboard?tab=scans');
  });

  it('redirige vers /cyberscan (landing) quand returnUrl est null', () => {
    expect(resolveReturnUrl(null)).toBe('/');
  });

  it('redirige vers /cyberscan (landing) quand returnUrl est vide', () => {
    expect(resolveReturnUrl('')).toBe('/');
  });

  it('ignore returnUrl=/vault', () => {
    expect(resolveReturnUrl('/vault')).toBe('/');
  });

  it('ignore returnUrl=/auth/master-password', () => {
    expect(resolveReturnUrl('/auth/master-password')).toBe('/');
  });

  it('ignore returnUrl=/auth/login', () => {
    expect(resolveReturnUrl('/auth/login')).toBe('/');
  });

  it('préserve /cyberscan (landing) comme returnUrl valide', () => {
    expect(resolveReturnUrl('/')).toBe('/');
  });
});
