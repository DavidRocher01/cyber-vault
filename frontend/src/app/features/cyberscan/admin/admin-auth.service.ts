import { Injectable, inject, signal } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, catchError, map, of, tap } from 'rxjs';

import { AuthService } from '../../../core/services/auth.service';

/**
 * Accès au back-office — deux voies, le temps de la bascule.
 *
 * 1. **Compte administrateur** (`users.is_admin`) : voie cible. L'intercepteur
 *    d'authentification pose déjà le jeton, il n'y a rien à faire de plus. Le
 *    droit est porté par une identité, donc traçable, révocable, et couvert par
 *    la 2FA du compte.
 * 2. **Clé `X-Admin-Key`** : secret partagé statique, relevé par l'audit du
 *    2026-07-27. Voie de repli, à supprimer une fois le premier compte
 *    administrateur créé et vérifié en production
 *    (cf. `docs/S6_INFRA_CHECKLIST.md` §0).
 *
 * Couper la clé avant qu'un compte admin n'existe rendrait le back-office
 * inaccessible : les deux voies coexistent donc, exactement comme côté serveur.
 *
 * La clé n'est JAMAIS persistée (durcissement S6) : elle ne vit que dans un
 * signal en mémoire, le temps de l'onglet. Aucune API de stockage n'est touchée,
 * donc SSR-safe par construction.
 */
@Injectable({ providedIn: 'root' })
export class AdminAuthService {
  private http = inject(HttpClient);
  private auth = inject(AuthService);

  authenticated = signal(false);
  adminKey = signal('');
  /** Vrai quand l'accès passe par un compte, faux quand il passe par la clé. */
  parCompte = signal(false);
  /** Tant que la vérification du compte n'a pas répondu, ne rien afficher :
   * montrer l'écran de clé puis le remplacer produirait un clignotement. */
  verificationEnCours = signal(true);

  /**
   * Tente l'accès par le compte connecté. Renvoie `true` si c'est un admin.
   *
   * Un échec n'est pas une erreur : la plupart des visiteurs de `/admin` ne sont
   * simplement pas connectés. On retombe alors sur l'écran de clé.
   */
  verifierCompte(): Observable<boolean> {
    return this.auth.me().pipe(
      map(user => user.is_admin === true),
      catchError(() => of(false)),
      tap(estAdmin => {
        if (estAdmin) {
          this.parCompte.set(true);
          this.authenticated.set(true);
        }
        this.verificationEnCours.set(false);
      })
    );
  }

  /**
   * En-têtes des appels admin.
   *
   * En mode compte, on ne renvoie RIEN : l'intercepteur pose déjà
   * `Authorization`, et ajouter une clé vide ferait échouer la comparaison
   * côté serveur sur les routes qui l'acceptent encore.
   */
  headers(): HttpHeaders {
    return this.parCompte()
      ? new HttpHeaders()
      : new HttpHeaders({ 'X-Admin-Key': this.adminKey() });
  }

  verify(key: string): Observable<unknown> {
    return this.http.get('/api/v1/admin/stats', {
      headers: new HttpHeaders({ 'X-Admin-Key': key }),
    });
  }

  login(key: string): void {
    this.adminKey.set(key);
    this.parCompte.set(false);
    this.authenticated.set(true);
  }

  logout(): void {
    this.adminKey.set('');
    this.parCompte.set(false);
    this.authenticated.set(false);
  }
}
