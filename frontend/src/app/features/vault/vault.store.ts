import { Injectable } from '@angular/core';
import { ComponentStore } from '@ngrx/component-store';
import { tapResponse } from '@ngrx/operators';
import { switchMap, tap } from 'rxjs';

import { VaultItem, VaultItemCreate, VaultService } from '../../core/services/vault.service';
import { CryptoService } from '../../core/services/crypto.service';

interface VaultState {
  items: VaultItem[];
  loading: boolean;
  error: string | null;
}

@Injectable()
export class VaultStore extends ComponentStore<VaultState> {
  readonly items$ = this.select(s => s.items);
  readonly loading$ = this.select(s => s.loading);
  readonly error$ = this.select(s => s.error);

  constructor(private vaultService: VaultService, private cryptoService: CryptoService) {
    super({ items: [], loading: false, error: null });
  }

  readonly loadItems = this.effect<void>(trigger$ =>
    trigger$.pipe(
      tap(() => this.patchState({ loading: true, error: null })),
      switchMap(() =>
        this.vaultService.getAll().pipe(
          tapResponse(
            items => this.patchState({ items, loading: false }),
            (err: any) => this.patchState({ loading: false, error: err.error?.detail ?? 'Erreur de chargement' })
          )
        )
      )
    )
  );

  readonly createItem = this.effect<VaultItemCreate>(payload$ =>
    payload$.pipe(
      switchMap(async payload => {
        const encrypted = await this.cryptoService.encrypt(payload.password_encrypted);
        return { ...payload, password_encrypted: encrypted };
      }),
      switchMap(payload =>
        this.vaultService.create(payload).pipe(
          tapResponse(
            item => this.patchState(s => ({ items: [...s.items, item] })),
            (err: any) => this.patchState({ error: err.error?.detail ?? 'Erreur de création' })
          )
        )
      )
    )
  );

  readonly deleteItem = this.effect<number>(id$ =>
    id$.pipe(
      switchMap(id =>
        this.vaultService.delete(id).pipe(
          tapResponse(
            () => this.patchState(s => ({ items: s.items.filter(i => i.id !== id) })),
            (err: any) => this.patchState({ error: err.error?.detail ?? 'Erreur de suppression' })
          )
        )
      )
    )
  );
}
