import { inject } from '@angular/core';
import { CanActivateFn, Router, RouterStateSnapshot } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { map, catchError } from 'rxjs/operators';
import { of } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const rssiGuard: CanActivateFn = (_route, state: RouterStateSnapshot) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const http = inject(HttpClient);

  if (!auth.isAuthenticated()) {
    return router.createUrlTree(['/auth/login'], { queryParams: { returnUrl: state.url } });
  }

  return http.get<{ is_rssi_consultant: boolean }>('/api/v1/users/me').pipe(
    map(user => user.is_rssi_consultant || router.createUrlTree(['/cyberscan'])),
    catchError(() => of(router.createUrlTree(['/cyberscan']))),
  );
};
