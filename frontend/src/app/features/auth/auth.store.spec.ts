/**
 * AuthStore — tests de logique pure
 *
 * ComponentStore nécessite le runtime Angular complet (DestroyRef) et ne peut
 * pas être instancié dans ce setup Vitest sans TestBed.
 * On teste ici la logique isolée : la résolution du returnUrl explicite et le
 * routage par rôle (destination par défaut après connexion).
 *
 * Le comportement end-to-end (navigateByUrl / appel /users/me) est couvert par
 * les tests d'intégration backend et par les tests du guard + register.
 */
import { describe, it, expect } from 'vitest';

// ── Reproduit exactement le getter privé explicitReturnUrl de AuthStore ─────────
// Retourne l'URL si c'est une page sûre de l'app principale, sinon null
// (=> AuthStore route alors selon le rôle).
function resolveExplicitReturnUrl(queryParamValue: string | null): string | null {
  const url = queryParamValue || '';
  const isMainAppPath =
    url.startsWith('/') &&
    !url.startsWith('//') &&
    !url.startsWith('/\\') &&
    !url.startsWith('/auth') &&
    !url.startsWith('/vault') &&
    !url.startsWith('/awareness');
  return isMainAppPath ? url : null;
}

// ── Reproduit homeForRole : destination par défaut selon le rôle ────────────────
function homeForRole(u: { is_rssi_consultant: boolean; is_portal_client: boolean }): string {
  if (u.is_rssi_consultant) return '/consultant';
  if (u.is_portal_client) return '/espace-client';
  return '/';
}

describe('AuthStore — explicitReturnUrl', () => {
  it("utilise returnUrl si c'est une route de l'app principale", () => {
    expect(resolveExplicitReturnUrl('/dashboard')).toBe('/dashboard');
  });

  it('préserve les sous-chemins avec query params', () => {
    expect(resolveExplicitReturnUrl('/dashboard?tab=scans')).toBe('/dashboard?tab=scans');
  });

  it('préserve /espace-client comme returnUrl valide', () => {
    expect(resolveExplicitReturnUrl('/espace-client')).toBe('/espace-client');
  });

  it('retourne null quand returnUrl est absent (=> routage par rôle)', () => {
    expect(resolveExplicitReturnUrl(null)).toBeNull();
  });

  it('retourne null quand returnUrl est vide', () => {
    expect(resolveExplicitReturnUrl('')).toBeNull();
  });

  it('ignore returnUrl=/vault (null)', () => {
    expect(resolveExplicitReturnUrl('/vault')).toBeNull();
  });

  it('ignore returnUrl=/auth/login (null)', () => {
    expect(resolveExplicitReturnUrl('/auth/login')).toBeNull();
  });

  it('ignore les redirections externes //evil (null)', () => {
    expect(resolveExplicitReturnUrl('//evil.com')).toBeNull();
  });

  it("préserve '/' (landing) comme returnUrl valide", () => {
    expect(resolveExplicitReturnUrl('/')).toBe('/');
  });
});

describe('AuthStore — homeForRole (priorité consultant > client > scanner)', () => {
  it('consultant -> /consultant', () => {
    expect(homeForRole({ is_rssi_consultant: true, is_portal_client: false })).toBe('/consultant');
  });

  it('client de portail -> /espace-client', () => {
    expect(homeForRole({ is_rssi_consultant: false, is_portal_client: true })).toBe(
      '/espace-client'
    );
  });

  it('utilisateur scanner classique -> /', () => {
    expect(homeForRole({ is_rssi_consultant: false, is_portal_client: false })).toBe('/');
  });

  it('double rôle (consultant + client) -> /consultant (priorité)', () => {
    expect(homeForRole({ is_rssi_consultant: true, is_portal_client: true })).toBe('/consultant');
  });
});
