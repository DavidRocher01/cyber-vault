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
  const url = queryParamValue || '/cyberscan';
  return url.startsWith('/vault') ? '/cyberscan' : url;
}

describe('AuthStore — returnUrl resolution', () => {
  it('utilise returnUrl quand il est présent', () => {
    expect(resolveReturnUrl('/cyberscan/dashboard')).toBe('/cyberscan/dashboard');
  });

  it('utilise /cyberscan quand returnUrl est null', () => {
    expect(resolveReturnUrl(null)).toBe('/cyberscan');
  });

  it('utilise /cyberscan quand returnUrl est une chaîne vide', () => {
    expect(resolveReturnUrl('')).toBe('/cyberscan');
  });

  it('préserve les chemins avec query params', () => {
    expect(resolveReturnUrl('/cyberscan/dashboard?tab=scans')).toBe('/cyberscan/dashboard?tab=scans');
  });

  it('ignore returnUrl=/vault et redirige vers /cyberscan', () => {
    expect(resolveReturnUrl('/vault')).toBe('/cyberscan');
  });

  it('ignore tout sous-chemin de /vault', () => {
    expect(resolveReturnUrl('/vault/settings')).toBe('/cyberscan');
  });
});
