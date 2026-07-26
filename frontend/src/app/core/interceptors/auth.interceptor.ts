import {
  HttpInterceptorFn,
  HttpErrorResponse,
  HttpRequest,
  HttpHandlerFn,
} from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import {
  Observable,
  catchError,
  finalize,
  map,
  retry,
  shareReplay,
  switchMap,
  take,
  throwError,
  timer,
} from 'rxjs';
import { HotToastService } from '@ngneat/hot-toast';

import { AuthService } from '../services/auth.service';
import { CryptoService } from '../services/crypto.service';
import { extractApiError } from '../http-error';

const addToken = (req: HttpRequest<unknown>, token: string) =>
  req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });

// Refresh « single-flight » : le refresh_token est ROTÉ côté serveur à chaque appel
// (l'ancien cookie est invalidé). Si deux requêtes tombent en 401 en même temps et
// lancent chacune leur propre refresh, le 2e présente un cookie déjà périmé → 401 →
// déconnexion intempestive. On partage donc UN SEUL refresh entre toutes les requêtes
// 401 concurrentes via shareReplay, et on le réarme (null) une fois terminé.
let sharedRefresh$: Observable<string> | null = null;

const sharedRefresh = (authService: AuthService): Observable<string> => {
  if (!sharedRefresh$) {
    sharedRefresh$ = authService.refresh().pipe(
      map(res => res.access_token),
      shareReplay({ bufferSize: 1, refCount: false }),
      finalize(() => {
        sharedRefresh$ = null;
      })
    );
  }
  return sharedRefresh$;
};

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  const cryptoService = inject(CryptoService);
  const router = inject(Router);
  const toast = inject(HotToastService);
  const token = authService.getToken();

  const authReq = token ? addToken(req, token) : req;

  const forceLogout = () => {
    authService.logout();
    cryptoService.clearKey();
    router.navigate(['/']);
  };

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
      // Ne pas tenter de refresh sur les endpoints d'auth eux-mêmes :
      // - login/register renvoient 401 pour de mauvais identifiants ;
      // - refresh/logout : éviter une récursion de refresh (un refresh qui 401
      //   doit se propager et déclencher la déconnexion, pas relancer un refresh).
      const isAuthEndpoint =
        req.url.includes('/auth/login') ||
        req.url.includes('/auth/register') ||
        req.url.includes('/auth/refresh') ||
        req.url.includes('/auth/logout');

      if (error.status === 401 && !isAuthEndpoint && authService.isAuthenticated()) {
        // Toutes les requêtes 401 concurrentes s'abonnent au MÊME refresh (single-flight),
        // puis rejouent leur propre requête avec le nouveau token.
        return sharedRefresh(authService).pipe(
          take(1),
          switchMap(newToken => next(addToken(req, newToken))),
          catchError(() => {
            forceLogout();
            return throwError(() => error);
          })
        );
      }
      if (error.status === 401 && !isAuthEndpoint) {
        forceLogout();
      }
      if (error.status === 429) {
        const msg = extractApiError(error, 'Trop de requêtes. Réessayez dans quelques instants.');
        toast.warning(msg);
      }
      if (error.status >= 500) {
        console.error('Erreur serveur:', error.message);
      }
      return throwError(() => error);
    })
  );
};
