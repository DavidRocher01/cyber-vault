import { inject } from '@angular/core';
import { CanActivateFn, Router, RouterStateSnapshot } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { map, catchError } from 'rxjs/operators';
import { of } from 'rxjs';
import { AuthService } from '../services/auth.service';

/**
 * Protège l'espace client RSSI : autorise seulement un compte rattaché à un RssiClient.
 * On s'appuie sur /portal/me (200 => client lié, 403 => non). Redirige sinon.
 */
export const rssiClientGuard: CanActivateFn = (_route, state: RouterStateSnapshot) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const http = inject(HttpClient);

  if (!auth.isAuthenticated()) {
    return router.createUrlTree(['/auth/login'], { queryParams: { returnUrl: state.url } });
  }

  return http.get('/api/v1/portal/me').pipe(
    map(() => true),
    catchError(() => of(router.createUrlTree(['/'])))
  );
};
