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
          // Decrypt display fields in-memory (server only ever stores opaque blobs)
          switchMap(items =>
            from(Promise.all(items.map(i => this.vaultService.hydrateForDisplay(i))))
          ),
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
      concatMap(plain =>
        from(
          Promise.all([
            this.cryptoService.encrypt(plain.password_encrypted),
            this.vaultService.buildEncryptedPayload({
              title: plain.title ?? '',
              username: plain.username,
              url: plain.url,
              notes: plain.notes,
            }),
          ])
        ).pipe(
          map(([encPwd, encFields]) => ({
            // Zero-knowledge: send ONLY encrypted fields + category (no plaintext)
            send: {
              category: plain.category,
              password_encrypted: encPwd,
              ...encFields,
            } as VaultItemCreate,
            plain,
          }))
        )
      ),
      concatMap(({ send, plain }) =>
        this.vaultService.create(send).pipe(
          tapResponse(
            item =>
              // Server returns null plaintext; show the values we already hold locally
              this.patchState(s => ({
                items: [
                  ...s.items,
                  {
                    ...item,
                    title: plain.title ?? null,
                    username: plain.username ?? null,
                    url: plain.url ?? null,
                    notes: plain.notes ?? null,
                  },
                ],
              })),
            (err: any) => this.patchState({ error: err.error?.detail ?? 'Erreur de création' })
          )
        )
      )
    )
  );

  readonly updateItem = this.effect<VaultItemUpdate>(payload$ =>
    payload$.pipe(
      concatMap(({ id, password_encrypted, title, username, url, notes, category }) =>
        from(
          Promise.all([
            password_encrypted
              ? this.cryptoService.encrypt(password_encrypted)
              : Promise.resolve(null),
            title !== undefined
              ? this.vaultService.buildEncryptedPayload({
                  title: title ?? '',
                  username,
                  url,
                  notes,
                })
              : Promise.resolve({}),
          ])
        ).pipe(
          map(([encPwd, encFields]) => ({
            id,
            // Zero-knowledge: send only category + encrypted fields (no plaintext)
            send: {
              ...(category !== undefined ? { category } : {}),
              ...(encPwd ? { password_encrypted: encPwd } : {}),
              ...encFields,
            } as Partial<VaultItemCreate>,
            plain: { title, username, url, notes },
          }))
        )
      ),
      concatMap(({ id, send, plain }) =>
        this.vaultService.update(id, send).pipe(
          tapResponse(
            updated =>
              // Server returns null plaintext; keep the values we already hold locally
              this.patchState(s => ({
                items: s.items.map(i =>
                  i.id === id
                    ? {
                        ...updated,
                        title: plain.title !== undefined ? (plain.title ?? null) : i.title,
                        username:
                          plain.username !== undefined ? (plain.username ?? null) : i.username,
                        url: plain.url !== undefined ? (plain.url ?? null) : i.url,
                        notes: plain.notes !== undefined ? (plain.notes ?? null) : i.notes,
                      }
                    : i
                ),
              })),
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
