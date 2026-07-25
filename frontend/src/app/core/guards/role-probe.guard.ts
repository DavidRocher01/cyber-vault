import { inject } from '@angular/core';
import { CanActivateFn, Router, RouterStateSnapshot } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { map, catchError } from 'rxjs/operators';
import { of } from 'rxjs';
import { AuthService } from '../services/auth.service';

/**
 * Fabrique de guard « sonde de rôle » : exige un utilisateur authentifié, puis
 * interroge `probeUrl` ; `authorize(body)` décide de l'accès. Non authentifié →
 * redirection vers /auth/login (avec returnUrl) ; non autorisé ou erreur réseau
 * → redirection vers la racine. Factorise rssiGuard et rssiClientGuard.
 */
export function roleProbeGuard(
  probeUrl: string,
  authorize: (body: unknown) => boolean
): CanActivateFn {
  return (_route, state: RouterStateSnapshot) => {
    const auth = inject(AuthService);
    const router = inject(Router);
    const http = inject(HttpClient);

    if (!auth.isAuthenticated()) {
      return router.createUrlTree(['/auth/login'], { queryParams: { returnUrl: state.url } });
    }

    return http.get(probeUrl).pipe(
      map(body => authorize(body) || router.createUrlTree(['/'])),
      catchError(() => of(router.createUrlTree(['/'])))
    );
  };
}
