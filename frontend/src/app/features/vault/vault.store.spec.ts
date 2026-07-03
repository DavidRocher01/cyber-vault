/**
 * VaultStore — tests de logique (ComponentStore + effects rxjs + intégration crypto)
 *
 * Le VaultStore est un ComponentStore NgRx. Il a besoin d'un contexte
 * d'injection Angular (DestroyRef) : on l'instancie via Injector.create +
 * runInInjectionContext (même pattern que les autres specs du projet), sans
 * TestBed (l'environnement de test Angular n'est pas initialisé ici).
 *
 * Toutes les dépendances externes sont MOCKÉES : VaultService (retours rxjs
 * `of(...)` / `throwError`) et CryptoService. Aucun appel réseau réel, aucune
 * WebCrypto : les tests sont déterministes.
 *
 * On couvre :
 *  - l'état initial et les sélecteurs (items$, loading$, error$)
 *  - loadItems : loading -> loaded (avec hydrateForDisplay) et loading -> error
 *  - createItem : chiffrement (encrypt + buildEncryptedPayload) puis append, et branche erreur
 *  - updateItem : chiffrement conditionnel (mdp/champs) puis merge local, et branche erreur
 *  - deleteItem : retrait de l'item, et branche erreur
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Injector, runInInjectionContext } from '@angular/core';
import { of, throwError, firstValueFrom } from 'rxjs';

import { VaultStore } from './vault.store';
import { VaultItem, VaultItemCreate, VaultService } from '../../core/services/vault.service';
import { CryptoService } from '../../core/services/crypto.service';

// ── Fabriques de données ────────────────────────────────────────────────────────

/** Construit un VaultItem minimal en surchargeant les champs pertinents. */
function makeItem(overrides: Partial<VaultItem> = {}): VaultItem {
  return {
    id: 1,
    title: null,
    username: null,
    password_encrypted: 'pw-blob',
    url: null,
    notes: null,
    category: 'login',
    title_encrypted: null,
    username_encrypted: null,
    url_encrypted: null,
    notes_encrypted: null,
    ...overrides,
  };
}

// ── Mocks des services ───────────────────────────────────────────────────────────

/**
 * Mock de VaultService. Par défaut tout réussit :
 *  - getAll -> of([])
 *  - create/update -> renvoient l'item passé (echo minimal)
 *  - delete -> of(null)
 *  - hydrateForDisplay -> identité (Promise)
 *  - buildEncryptedPayload -> blobs déterministes
 *  - migrateLegacyItems -> Promise résolue
 */
function makeVaultServiceMock() {
  return {
    getAll: vi.fn().mockReturnValue(of<VaultItem[]>([])),
    create: vi.fn((payload: VaultItemCreate) =>
      of(makeItem({ id: 42, ...payload, title: null, username: null, url: null, notes: null }))
    ),
    update: vi.fn((id: number, payload: Partial<VaultItemCreate>) =>
      of(makeItem({ id, ...payload, title: null, username: null, url: null, notes: null }))
    ),
    delete: vi.fn().mockReturnValue(of(null)),
    hydrateForDisplay: vi.fn((item: VaultItem) => Promise.resolve(item)),
    buildEncryptedPayload: vi.fn((plain: { title: string; username?: string | null }) =>
      Promise.resolve({
        title_encrypted: `enc(${plain.title})`,
        ...(plain.username ? { username_encrypted: `enc(${plain.username})` } : {}),
      })
    ),
    migrateLegacyItems: vi.fn().mockResolvedValue(undefined),
  };
}

function makeCryptoServiceMock() {
  return {
    encrypt: vi.fn((plain: string) => Promise.resolve(`enc(${plain})`)),
  };
}

// ── Setup ────────────────────────────────────────────────────────────────────────

let vaultMock: ReturnType<typeof makeVaultServiceMock>;
let cryptoMock: ReturnType<typeof makeCryptoServiceMock>;
let store: VaultStore;

function setup() {
  vaultMock = makeVaultServiceMock();
  cryptoMock = makeCryptoServiceMock();

  const injector = Injector.create({
    providers: [
      { provide: VaultService, useValue: vaultMock },
      { provide: CryptoService, useValue: cryptoMock },
    ],
  });
  // ComponentStore appelle inject(DestroyRef) dans son constructeur → contexte requis.
  store = runInInjectionContext(
    injector,
    () =>
      new VaultStore(vaultMock as unknown as VaultService, cryptoMock as unknown as CryptoService)
  );
}

/** Laisse les microtâches (Promises internes aux effects) se résoudre. */
async function flush(): Promise<void> {
  // Plusieurs tours de boucle pour Promise.all + from(...) + tapResponse.
  for (let i = 0; i < 5; i++) {
    await Promise.resolve();
  }
}

/** Lit la valeur courante d'un sélecteur du store. */
function current<T>(selector$: import('rxjs').Observable<T>): Promise<T> {
  return firstValueFrom(selector$);
}

beforeEach(() => setup());

// ── État initial & sélecteurs ────────────────────────────────────────────────────

describe('VaultStore — état initial et sélecteurs', () => {
  it('démarre avec items=[], loading=false, error=null', async () => {
    expect(await current(store.items$)).toEqual([]);
    expect(await current(store.loading$)).toBe(false);
    expect(await current(store.error$)).toBeNull();
  });
});

// ── loadItems ────────────────────────────────────────────────────────────────────

describe('VaultStore — loadItems', () => {
  it('charge et hydrate les items ; loading repasse à false, pas d’erreur', async () => {
    const raw = [makeItem({ id: 1, title: 'A' }), makeItem({ id: 2, title: 'B' })];
    vaultMock.getAll.mockReturnValue(of(raw));
    // hydrateForDisplay ajoute un marqueur pour prouver qu'il a bien été appelé.
    vaultMock.hydrateForDisplay.mockImplementation((it: VaultItem) =>
      Promise.resolve({ ...it, title: `${it.title}-hydrated` })
    );

    store.loadItems();
    await flush();

    const items = await current(store.items$);
    expect(items.map(i => i.title)).toEqual(['A-hydrated', 'B-hydrated']);
    expect(await current(store.loading$)).toBe(false);
    expect(await current(store.error$)).toBeNull();
    expect(vaultMock.hydrateForDisplay).toHaveBeenCalledTimes(2);
  });

  it('déclenche migrateLegacyItems en arrière-plan après un chargement réussi', async () => {
    vaultMock.getAll.mockReturnValue(of([makeItem({ id: 1 })]));
    store.loadItems();
    await flush();
    expect(vaultMock.migrateLegacyItems).toHaveBeenCalledTimes(1);
  });

  it('ignore silencieusement un échec de migrateLegacyItems (non bloquant)', async () => {
    vaultMock.getAll.mockReturnValue(of([makeItem({ id: 1 })]));
    vaultMock.migrateLegacyItems.mockRejectedValue(new Error('migration KO'));
    store.loadItems();
    await flush();
    // Le chargement reste réussi malgré l'échec de migration.
    expect((await current(store.items$)).length).toBe(1);
    expect(await current(store.error$)).toBeNull();
  });

  it('sur erreur HTTP : loading=false et message issu de err.error.detail', async () => {
    vaultMock.getAll.mockReturnValue(throwError(() => ({ error: { detail: 'boom serveur' } })));
    store.loadItems();
    await flush();
    expect(await current(store.loading$)).toBe(false);
    expect(await current(store.error$)).toBe('boom serveur');
  });

  it('sur erreur sans detail : message de chargement par défaut', async () => {
    vaultMock.getAll.mockReturnValue(throwError(() => ({})));
    store.loadItems();
    await flush();
    expect(await current(store.error$)).toBe('Erreur de chargement');
  });
});

// ── createItem ───────────────────────────────────────────────────────────────────

describe('VaultStore — createItem', () => {
  it('chiffre le mot de passe et les champs puis ajoute l’item avec le clair local', async () => {
    store.createItem({
      title: 'GitHub',
      username: 'david',
      password_encrypted: 'secret',
      url: 'https://gh',
      notes: 'n',
      category: 'login',
    });
    await flush();

    // Le mot de passe passe par crypto.encrypt.
    expect(cryptoMock.encrypt).toHaveBeenCalledWith('secret');
    // Les champs d'affichage passent par buildEncryptedPayload.
    expect(vaultMock.buildEncryptedPayload).toHaveBeenCalledWith({
      title: 'GitHub',
      username: 'david',
      url: 'https://gh',
      notes: 'n',
    });

    // Le payload envoyé ne contient QUE des champs chiffrés + category (zero-knowledge).
    const sent = vaultMock.create.mock.calls[0][0] as VaultItemCreate;
    expect(sent.category).toBe('login');
    expect(sent.password_encrypted).toBe('enc(secret)');
    expect(sent.title_encrypted).toBe('enc(GitHub)');
    expect(sent.username_encrypted).toBe('enc(david)');
    expect((sent as any).title).toBeUndefined();
    expect((sent as any).username).toBeUndefined();

    // L'item ajouté au state porte le clair local (pas le null renvoyé par le serveur).
    const items = await current(store.items$);
    expect(items).toHaveLength(1);
    expect(items[0].id).toBe(42);
    expect(items[0].title).toBe('GitHub');
    expect(items[0].username).toBe('david');
    expect(items[0].url).toBe('https://gh');
    expect(items[0].notes).toBe('n');
  });

  it('title/username/url/notes absents deviennent null dans le state local', async () => {
    store.createItem({ password_encrypted: 'p', category: 'note' });
    await flush();
    const items = await current(store.items$);
    expect(items[0].title).toBeNull();
    expect(items[0].username).toBeNull();
    expect(items[0].url).toBeNull();
    expect(items[0].notes).toBeNull();
    // buildEncryptedPayload reçoit title='' quand title est absent.
    expect(vaultMock.buildEncryptedPayload).toHaveBeenCalledWith({
      title: '',
      username: undefined,
      url: undefined,
      notes: undefined,
    });
  });

  it('sur erreur de create : renseigne error sans muter items', async () => {
    vaultMock.create.mockReturnValue(throwError(() => ({ error: { detail: 'create KO' } })));
    store.createItem({ title: 'X', password_encrypted: 'p' });
    await flush();
    expect(await current(store.error$)).toBe('create KO');
    expect(await current(store.items$)).toEqual([]);
  });

  it('sur erreur de create sans detail : message de création par défaut', async () => {
    vaultMock.create.mockReturnValue(throwError(() => ({})));
    store.createItem({ title: 'X', password_encrypted: 'p' });
    await flush();
    expect(await current(store.error$)).toBe('Erreur de création');
  });
});

// ── updateItem ───────────────────────────────────────────────────────────────────

describe('VaultStore — updateItem', () => {
  beforeEach(async () => {
    // Pré-charge un item existant dans le state pour tester le merge.
    vaultMock.getAll.mockReturnValue(
      of([
        makeItem({ id: 7, title: 'Ancien', username: 'oldUser', url: 'oldUrl', notes: 'oldNote' }),
      ])
    );
    store.loadItems();
    await flush();
  });

  it('chiffre le mdp et les champs fournis puis merge le clair local sur l’item ciblé', async () => {
    store.updateItem({
      id: 7,
      password_encrypted: 'newpass',
      title: 'Nouveau',
      username: 'newUser',
      category: 'card',
    });
    await flush();

    expect(cryptoMock.encrypt).toHaveBeenCalledWith('newpass');
    expect(vaultMock.buildEncryptedPayload).toHaveBeenCalledWith({
      title: 'Nouveau',
      username: 'newUser',
      url: undefined,
      notes: undefined,
    });

    const [sentId, sent] = vaultMock.update.mock.calls[0];
    expect(sentId).toBe(7);
    expect(sent.category).toBe('card');
    expect(sent.password_encrypted).toBe('enc(newpass)');
    expect(sent.title_encrypted).toBe('enc(Nouveau)');

    const items = await current(store.items$);
    const updated = items.find(i => i.id === 7)!;
    expect(updated.title).toBe('Nouveau');
    expect(updated.username).toBe('newUser');
    // url/notes non fournis (undefined) → on garde l'ancienne valeur locale.
    expect(updated.url).toBe('oldUrl');
    expect(updated.notes).toBe('oldNote');
  });

  it('sans password_encrypted : ne chiffre pas de mdp et n’envoie pas password_encrypted', async () => {
    store.updateItem({ id: 7, title: 'JusteTitre' });
    await flush();

    expect(cryptoMock.encrypt).not.toHaveBeenCalled();
    const [, sent] = vaultMock.update.mock.calls[0];
    expect(sent.password_encrypted).toBeUndefined();
    expect(sent.title_encrypted).toBe('enc(JusteTitre)');
    // category non fournie → absente du payload.
    expect('category' in sent).toBe(false);
  });

  it('sans champ title (undefined) : buildEncryptedPayload n’est pas appelé', async () => {
    store.updateItem({ id: 7, password_encrypted: 'onlypass' });
    await flush();
    expect(vaultMock.buildEncryptedPayload).not.toHaveBeenCalled();
    const [, sent] = vaultMock.update.mock.calls[0];
    expect(sent.password_encrypted).toBe('enc(onlypass)');
    // Aucun *_encrypted de champ d'affichage.
    expect(sent.title_encrypted).toBeUndefined();
  });

  it('title explicitement null → clair local devient null', async () => {
    store.updateItem({ id: 7, title: null });
    await flush();
    const updated = (await current(store.items$)).find(i => i.id === 7)!;
    expect(updated.title).toBeNull();
    // buildEncryptedPayload reçoit '' (title ?? '').
    expect(vaultMock.buildEncryptedPayload).toHaveBeenCalledWith({
      title: '',
      username: undefined,
      url: undefined,
      notes: undefined,
    });
  });

  it('champs username/url/notes explicitement fournis : merge sur les valeurs fournies', async () => {
    store.updateItem({
      id: 7,
      title: 'T',
      username: 'freshUser',
      url: 'https://fresh',
      notes: 'freshNotes',
    });
    await flush();
    const updated = (await current(store.items$)).find(i => i.id === 7)!;
    expect(updated.username).toBe('freshUser');
    expect(updated.url).toBe('https://fresh');
    expect(updated.notes).toBe('freshNotes');
  });

  it('username/url/notes explicitement null : merge sur null (pas conservation de l’ancien)', async () => {
    store.updateItem({ id: 7, title: 'T', username: null, url: null, notes: null });
    await flush();
    const updated = (await current(store.items$)).find(i => i.id === 7)!;
    expect(updated.username).toBeNull();
    expect(updated.url).toBeNull();
    expect(updated.notes).toBeNull();
  });

  it('ne touche pas les autres items du state', async () => {
    // Ajoute un second item.
    vaultMock.create.mockReturnValue(of(makeItem({ id: 8 })));
    store.createItem({ title: 'Autre', password_encrypted: 'p' });
    await flush();

    store.updateItem({ id: 7, title: 'MàJ' });
    await flush();

    const items = await current(store.items$);
    const other = items.find(i => i.id === 8)!;
    expect(other.title).toBe('Autre');
  });

  it('sur erreur de update : renseigne error', async () => {
    vaultMock.update.mockReturnValue(throwError(() => ({ error: { detail: 'update KO' } })));
    store.updateItem({ id: 7, title: 'X' });
    await flush();
    expect(await current(store.error$)).toBe('update KO');
  });

  it('sur erreur de update sans detail : message de modification par défaut', async () => {
    vaultMock.update.mockReturnValue(throwError(() => ({})));
    store.updateItem({ id: 7, title: 'X' });
    await flush();
    expect(await current(store.error$)).toBe('Erreur de modification');
  });
});

// ── deleteItem ───────────────────────────────────────────────────────────────────

describe('VaultStore — deleteItem', () => {
  beforeEach(async () => {
    vaultMock.getAll.mockReturnValue(
      of([makeItem({ id: 1, title: 'un' }), makeItem({ id: 2, title: 'deux' })])
    );
    store.loadItems();
    await flush();
  });

  it('retire l’item ciblé du state', async () => {
    store.deleteItem(1);
    await flush();
    expect(vaultMock.delete).toHaveBeenCalledWith(1);
    const items = await current(store.items$);
    expect(items.map(i => i.id)).toEqual([2]);
  });

  it('sur erreur de delete : renseigne error et conserve les items', async () => {
    vaultMock.delete.mockReturnValue(throwError(() => ({ error: { detail: 'delete KO' } })));
    store.deleteItem(1);
    await flush();
    expect(await current(store.error$)).toBe('delete KO');
    expect((await current(store.items$)).map(i => i.id)).toEqual([1, 2]);
  });

  it('sur erreur de delete sans detail : message de suppression par défaut', async () => {
    vaultMock.delete.mockReturnValue(throwError(() => ({})));
    store.deleteItem(1);
    await flush();
    expect(await current(store.error$)).toBe('Erreur de suppression');
  });
});
