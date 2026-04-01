import { HttpInterceptorFn, HttpErrorResponse, HttpRequest, HttpHandlerFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, switchMap, throwError } from 'rxjs';

import { AuthService } from '../services/auth.service';
import { CryptoService } from '../services/crypto.service';

const addToken = (req: HttpRequest<unknown>, token: string) =>
  req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  const cryptoService = inject(CryptoService);
  const router = inject(Router);
  const token = authService.getToken();

  const authReq = token ? addToken(req, token) : req;

  return next(authReq).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401 && authService.getRefreshToken()) {
        return authService.refresh().pipe(
          switchMap(res => next(addToken(req, res.access_token))),
          catchError(() => {
            authService.logout();
            cryptoService.clearKey();
            router.navigate(['/auth/login']);
            return throwError(() => error);
          })
        );
      }
      if (error.status === 401) {
        authService.logout();
        cryptoService.clearKey();
        router.navigate(['/auth/login']);
      }
      if (error.status === 429) {
        console.warn('Rate limit atteint, réessayez plus tard.');
      }
      if (error.status >= 500) {
        console.error('Erreur serveur:', error.message);
      }
      return throwError(() => error);
    })
  );
};
