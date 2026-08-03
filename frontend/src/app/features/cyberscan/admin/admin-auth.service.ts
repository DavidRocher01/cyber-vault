import { Injectable, inject, signal } from '@angular/core';
import { Observable, catchError, map, of, tap } from 'rxjs';

import { AuthService } from '../../../core/services/auth.service';

/**
 * Accès au back-office : un compte portant `users.is_admin`.
 *
 * L'intercepteur d'authentification pose déjà le jeton, il n'y a donc rien à
 * transmettre de plus — d'où l'absence de méthode `headers()`.
 *
 * Historique, parce qu'il explique la forme de ce service : jusqu'au
 * 2026-08-02, l'accès passait par une clé `X-Admin-Key` saisie à la main, un
 * secret partagé statique sans identité ni révocation relevé par l'audit du
 * 2026-07-27. La clé a d'abord cessé d'être injectée en production, puis le
 * repli a été retiré du code, ici comme côté serveur.
 */
@Injectable({ providedIn: 'root' })
export class AdminAuthService {
  private auth = inject(AuthService);

  authenticated = signal(false);
  /** Tant que la vérification n'a pas répondu, ne rien afficher : montrer un
   * écran de refus puis le remplacer produirait un clignotement. */
  verificationEnCours = signal(true);

  /**
   * Vérifie que le compte connecté est administrateur.
   *
   * Un échec n'est pas une erreur : la plupart des visiteurs de `/admin` ne
   * sont simplement pas connectés.
   */
  verifierCompte(): Observable<boolean> {
    return this.auth.me().pipe(
      map(user => user.is_admin === true),
      catchError(() => of(false)),
      tap(estAdmin => {
        this.authenticated.set(estAdmin);
        this.verificationEnCours.set(false);
      })
    );
  }

  logout(): void {
    this.authenticated.set(false);
  }
}
