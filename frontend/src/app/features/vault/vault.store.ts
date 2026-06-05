import { Injectable } from '@angular/core';
import { ComponentStore } from '@ngrx/component-store';
import { tapResponse } from '@ngrx/operators';
import { from, switchMap, concatMap, map, tap } from 'rxjs';

import { VaultItem, VaultItemCreate, VaultService } from '../../core/services/vault.service';
import { CryptoService } from '../../core/services/crypto.service';

interface VaultItemUpdate extends Partial<VaultItemCreate> {
  id: number;
}

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

  constructor(
    private vaultService: VaultService,
    private cryptoService: CryptoService
  ) {
    super({ items: [], loading: false, error: null });
  }

  readonly loadItems = this.effect<void>(trigger$ =>
    trigger$.pipe(
      tap(() => this.patchState({ loading: true, error: null })),
      switchMap(() =>
        this.vaultService.getAll().pipe(
          tapResponse(
            items => {
              this.patchState({ items, loading: false });
              // Migrate legacy plaintext items in the background (non-blocking)
              this.vaultService.migrateLegacyItems().catch(() => {});
            },
            (err: any) =>
              this.patchState({
                loading: false,
                error: err.error?.detail ?? 'Erreur de chargement',
              })
          )
        )
      )
    )
  );

  readonly createItem = this.effect<VaultItemCreate>(payload$ =>
    payload$.pipe(
      concatMap(payload =>
        from(
          Promise.all([
            this.cryptoService.encrypt(payload.password_encrypted),
            this.vaultService.buildEncryptedPayload({
              title: payload.title,
              username: payload.username,
              url: payload.url,
              notes: payload.notes,
            }),
          ])
        ).pipe(
          map(([encPwd, encFields]) => ({
            ...payload,
            password_encrypted: encPwd,
            ...encFields,
          }))
        )
      ),
      concatMap(payload =>
        this.vaultService.create(payload).pipe(
          tapResponse(
            item => this.patchState(s => ({ items: [...s.items, item] })),
            (err: any) => this.patchState({ error: err.error?.detail ?? 'Erreur de création' })
          )
        )
      )
    )
  );

  readonly updateItem = this.effect<VaultItemUpdate>(payload$ =>
    payload$.pipe(
      concatMap(({ id, password_encrypted, ...rest }) =>
        from(
          Promise.all([
            password_encrypted
              ? this.cryptoService.encrypt(password_encrypted)
              : Promise.resolve(null),
            rest.title !== undefined
              ? this.vaultService.buildEncryptedPayload({
                  title: rest.title ?? '',
                  username: rest.username,
                  url: rest.url,
                  notes: rest.notes,
                })
              : Promise.resolve({}),
          ])
        ).pipe(
          map(([encPwd, encFields]) => ({
            id,
            ...rest,
            ...(encPwd ? { password_encrypted: encPwd } : {}),
            ...encFields,
          }))
        )
      ),
      concatMap(({ id, ...payload }) =>
        this.vaultService.update(id, payload).pipe(
          tapResponse(
            updated =>
              this.patchState(s => ({ items: s.items.map(i => (i.id === id ? updated : i)) })),
            (err: any) => this.patchState({ error: err.error?.detail ?? 'Erreur de modification' })
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
