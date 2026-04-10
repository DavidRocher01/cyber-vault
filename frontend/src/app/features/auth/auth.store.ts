import { Injectable } from '@angular/core';
import { ComponentStore } from '@ngrx/component-store';
import { ActivatedRoute, Router } from '@angular/router';
import { tapResponse } from '@ngrx/operators';
import { switchMap } from 'rxjs';

import { AuthService } from '../../core/services/auth.service';

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
    private route: ActivatedRoute,
  ) {
    super({ loading: false, error: null, requires2fa: false, pendingEmail: null, pendingPassword: null });
  }

  private get returnUrl(): string {
    return this.route.snapshot.queryParamMap.get('returnUrl') || '/cyberscan/dashboard';
  }

  readonly login = this.effect<{ email: string; password: string }>(credentials$ =>
    credentials$.pipe(
      switchMap(({ email, password }) => {
        this.patchState({ loading: true, error: null });
        return this.authService.login(email, password).pipe(
          tapResponse(
            (res) => {
              if ('requires_2fa' in res) {
                this.patchState({ loading: false, requires2fa: true, pendingEmail: email, pendingPassword: password });
              } else {
                this.patchState({ loading: false, requires2fa: false });
                this.router.navigateByUrl(this.returnUrl);
              }
            },
            (err: any) => {
              const msg = err.error?.detail ?? 'Erreur de connexion';
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
              this.patchState({ loading: false, requires2fa: false, pendingEmail: null, pendingPassword: null });
              this.router.navigateByUrl(this.returnUrl);
            },
            (err: any) => {
              const msg = err.error?.detail ?? 'Code invalide';
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
