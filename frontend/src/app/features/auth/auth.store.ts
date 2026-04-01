import { Injectable } from '@angular/core';
import { ComponentStore } from '@ngrx/component-store';
import { Router } from '@angular/router';
import { tapResponse } from '@ngrx/operators';
import { switchMap } from 'rxjs';
import { HotToastService } from '@ngneat/hot-toast';

import { AuthService } from '../../core/services/auth.service';

interface AuthState {
  loading: boolean;
  error: string | null;
}

@Injectable()
export class AuthStore extends ComponentStore<AuthState> {
  readonly loading$ = this.select(s => s.loading);
  readonly error$ = this.select(s => s.error);

  constructor(
    private authService: AuthService,
    private router: Router,
    private toast: HotToastService
  ) {
    super({ loading: false, error: null });
  }

  readonly login = this.effect<{ email: string; password: string }>(credentials$ =>
    credentials$.pipe(
      switchMap(({ email, password }) => {
        this.patchState({ loading: true, error: null });
        return this.authService.login(email, password).pipe(
          tapResponse(
            () => {
              this.patchState({ loading: false });
              this.router.navigate(['/auth/master-password']);
            },
            (err: any) => {
              const msg = err.error?.detail ?? 'Erreur de connexion';
              this.patchState({ loading: false, error: msg });
              this.toast.error(msg);
            }
          )
        );
      })
    )
  );
}
