import {
  HttpInterceptorFn,
  HttpErrorResponse,
  HttpRequest,
  HttpHandlerFn,
} from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, retry, switchMap, throwError, timer } from 'rxjs';
import { HotToastService } from '@ngneat/hot-toast';

import { AuthService } from '../services/auth.service';
import { CryptoService } from '../services/crypto.service';

const addToken = (req: HttpRequest<unknown>, token: string) =>
  req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  const cryptoService = inject(CryptoService);
  const router = inject(Router);
  const toast = inject(HotToastService);
  const token = authService.getToken();

  const authReq = token ? addToken(req, token) : req;

  return next(authReq).pipe(
    retry({
      count: 1,
      delay: err => {
        if (err instanceof HttpErrorResponse && err.status >= 500 && req.method === 'GET') {
          return timer(1000);
        }
        return throwError(() => err);
      },
    }),
    catchError((error: HttpErrorResponse) => {
      // Don't redirect on 401 from auth endpoints (login/register return 401 for bad credentials)
      const isAuthEndpoint = req.url.includes('/auth/login') || req.url.includes('/auth/register');
      if (error.status === 401 && !isAuthEndpoint && authService.isAuthenticated()) {
        return authService.refresh().pipe(
          switchMap(res => next(addToken(req, res.access_token))),
          catchError(() => {
            authService.logout();
            cryptoService.clearKey();
            router.navigate(['/']);
            return throwError(() => error);
          })
        );
      }
      if (error.status === 401 && !isAuthEndpoint) {
        authService.logout();
        cryptoService.clearKey();
        router.navigate(['/']);
      }
      if (error.status === 429) {
        const msg = error.error?.detail ?? 'Trop de requêtes. Réessayez dans quelques instants.';
        toast.warning(msg);
      }
      if (error.status >= 500) {
        console.error('Erreur serveur:', error.message);
      }
      return throwError(() => error);
    })
  );
};
