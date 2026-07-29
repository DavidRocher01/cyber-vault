import { Injectable, signal } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';

/**
 * Authentification admin (X-Admin-Key) — durcissement audit 2026-07-27 S6 (#8/#17).
 *
 * La clé admin n'est JAMAIS persistée (ni sessionStorage ni localStorage) : elle
 * ne vit que dans un signal en mémoire, le temps de la session de l'onglet.
 * Conséquences :
 *  - plus de secret admin au repos, lisible trivialement par une éventuelle XSS ;
 *  - un rechargement complet (F5) ou un nouvel onglet re-demande la clé (re-saisie
 *    par session), la navigation SPA la conserve (service `providedIn: 'root'`) ;
 *  - aucune API navigateur (storage/window) n'est touchée → SSR-safe par
 *    construction, plus besoin de garde isPlatformBrowser.
 *
 * Défense en profondeur complémentaire côté infra (hors code) : CSP sur la SPA
 * (coupe le canal d'exfiltration) + rotation d'ADMIN_API_KEY dans Secrets Manager.
 */
@Injectable({ providedIn: 'root' })
export class AdminAuthService {
  authenticated = signal(false);
  adminKey = signal('');

  constructor(private http: HttpClient) {}

  headers(): HttpHeaders {
    return new HttpHeaders({ 'X-Admin-Key': this.adminKey() });
  }

  verify(key: string): Observable<unknown> {
    return this.http.get('/api/v1/admin/stats', {
      headers: new HttpHeaders({ 'X-Admin-Key': key }),
    });
  }

  login(key: string): void {
    this.adminKey.set(key);
    this.authenticated.set(true);
  }

  logout(): void {
    this.adminKey.set('');
    this.authenticated.set(false);
  }
}
