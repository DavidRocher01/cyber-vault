import { Injectable } from '@angular/core';
import { ComponentStore } from '@ngrx/component-store';
import { ActivatedRoute, Router } from '@angular/router';
import { tapResponse } from '@ngrx/operators';
import { switchMap } from 'rxjs';

import { AuthService } from '../../core/services/auth.service';
import { extractApiError } from '../../core/http-error';

interface AuthState {
  loading: boolean;
  error: string | null;
  requires2fa: boolean;
  pendingEmail: string | null;
  pendingPassword: string | null;
}

@Injectable()
export class AuthStore extends ComponentStore<AuthState> {
  readonly loading$ = this.select(s => s.loading);
  readonly error$ = this.select(s => s.error);
  readonly requires2fa$ = this.select(s => s.requires2fa);

  constructor(
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute
  ) {
    super({
      loading: false,
      error: null,
      requires2fa: false,
      pendingEmail: null,
      pendingPassword: null,
    });
  }

  // returnUrl explicite et sûr, sinon null (=> on route alors selon le rôle).
  // N'honore que les pages de l'app principale (racine) ; rejette les redirections
  // externes (//evil, /\evil) et les zones a part (/auth = boucle de login,
  // /vault = flow crypto, /awareness = portail magic-link).
  private get explicitReturnUrl(): string | null {
    const url = this.route.snapshot.queryParamMap.get('returnUrl') || '';
    const isMainAppPath =
      url.startsWith('/') &&
      !url.startsWith('//') &&
      !url.startsWith('/\\') &&
      !url.startsWith('/auth') &&
      !url.startsWith('/vault') &&
      !url.startsWith('/awareness');
    return isMainAppPath ? url : null;
  }

  // Destination par defaut selon le role (priorite : consultant > client > scanner).
  private homeForRole(u: { is_rssi_consultant: boolean; is_portal_client: boolean }): string {
    if (u.is_rssi_consultant) return '/consultant';
    if (u.is_portal_client) return '/espace-client';
    return '/';
  }

  // Apres connexion : honore un returnUrl explicite, sinon route selon le role.
  private navigateAfterLogin(): void {
    const explicit = this.explicitReturnUrl;
    if (explicit) {
      this.router.navigateByUrl(explicit);
      return;
    }
    this.authService.me().subscribe({
      next: u => this.router.navigateByUrl(this.homeForRole(u)),
      error: () => this.router.navigateByUrl('/'),
    });
  }

  readonly login = this.effect<{ email: string; password: string }>(credentials$ =>
    credentials$.pipe(
      switchMap(({ email, password }) => {
        this.patchState({ loading: true, error: null });
        return this.authService.login(email, password).pipe(
          tapResponse(
            res => {
              if ('requires_2fa' in res) {
                this.patchState({
                  loading: false,
                  requires2fa: true,
                  pendingEmail: email,
                  pendingPassword: password,
                });
              } else {
                this.patchState({ loading: false, requires2fa: false });
                this.navigateAfterLogin();
              }
            },
            (err: any) => {
              const msg = extractApiError(err, 'Erreur de connexion');
              this.patchState({ loading: false, error: msg });
            }
          )
        );
      })
    )
  );

  readonly loginWith2FA = this.effect<{ totpCode: string }>(payload$ =>
    payload$.pipe(
      switchMap(({ totpCode }) => {
        const { pendingEmail, pendingPassword } = this.get();
        if (!pendingEmail || !pendingPassword) return [];
        this.patchState({ loading: true, error: null });
        return this.authService.login(pendingEmail, pendingPassword, totpCode).pipe(
          tapResponse(
            () => {
              this.patchState({
                loading: false,
                requires2fa: false,
                pendingEmail: null,
                pendingPassword: null,
              });
              this.navigateAfterLogin();
            },
            (err: any) => {
              const msg = extractApiError(err, 'Code invalide');
              this.patchState({ loading: false, error: msg });
            }
          )
        );
      })
    )
  );

  cancelTwoFa() {
    this.patchState({ requires2fa: false, pendingEmail: null, pendingPassword: null, error: null });
  }

  clearError() {
    this.patchState({ error: null });
  }
}
