import { describe, it, expect, beforeEach, vi } from 'vitest';
import { of } from 'rxjs';
import { VaultService } from './vault.service';

describe('VaultService', () => {
  let service: VaultService;
  let httpMock: any;

  beforeEach(() => {
    httpMock = {
      get: vi.fn(),
      post: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
    };
    service = new VaultService(httpMock);
  });

  it('getAll() appelle GET sur /vault/', () => {
    httpMock.get.mockReturnValue(of([]));
    service.getAll().subscribe();
    expect(httpMock.get).toHaveBeenCalledWith(expect.stringContaining('/vault/'));
  });

  it('create() appelle POST sur /vault/ avec le payload', () => {
    const payload = { title: 'GitHub', password_encrypted: 'enc123' };
    httpMock.post.mockReturnValue(
      of({ id: 1, ...payload, username: null, url: null, notes: null })
    );
    service.create(payload).subscribe();
    expect(httpMock.post).toHaveBeenCalledWith(expect.stringContaining('/vault/'), payload);
  });

  it('delete() appelle DELETE sur /vault/:id', () => {
    httpMock.delete.mockReturnValue(of(null));
    service.delete(42).subscribe();
    expect(httpMock.delete).toHaveBeenCalledWith(expect.stringContaining('/vault/42'));
  });

  it('update() appelle PATCH sur /vault/:id avec le payload', () => {
    const payload = { title: 'Nouveau titre' };
    httpMock.patch.mockReturnValue(of({ id: 1, ...payload }));
    service.update(1, payload).subscribe();
    expect(httpMock.patch).toHaveBeenCalledWith(expect.stringContaining('/vault/1'), payload);
  });
});

function make(http: any, crypto: any): VaultService {
  const s = Object.create(VaultService.prototype) as VaultService;
  (s as any).http = http;
  (s as any).crypto = crypto;
  return s;
}

describe('VaultService — decryptItem()', () => {
  it('déchiffre tous les champs *_encrypted présents', async () => {
    const crypto = {
      tryDecrypt: vi.fn().mockImplementation((c: string) => Promise.resolve('D:' + c)),
    };
    const s = make({}, crypto);
    const item: any = {
      id: 1,
      title: 'old',
      username: 'oldU',
      url: 'oldUrl',
      notes: 'oldN',
      password_encrypted: 'p',
      category: 'login',
      title_encrypted: 'te',
      username_encrypted: 'ue',
      url_encrypted: 'urle',
      notes_encrypted: 'ne',
    };
    const out = await s.decryptItem(item);
    expect(out._title).toBe('D:te');
    expect(out._username).toBe('D:ue');
    expect(out._url).toBe('D:urle');
    expect(out._notes).toBe('D:ne');
    // l'original n'est pas muté
    expect(item._title).toBeUndefined();
  });

  it('retombe sur les champs plaintext quand aucun *_encrypted', async () => {
    const crypto = { tryDecrypt: vi.fn() };
    const s = make({}, crypto);
    const item: any = {
      id: 2,
      title: 'clairTitre',
      username: 'clairUser',
      url: 'clairUrl',
      notes: 'clairNotes',
      password_encrypted: 'p',
      category: 'login',
      title_encrypted: null,
      username_encrypted: null,
      url_encrypted: null,
      notes_encrypted: null,
    };
    const out = await s.decryptItem(item);
    expect(out._title).toBe('clairTitre');
    expect(out._username).toBe('clairUser');
    expect(out._url).toBe('clairUrl');
    expect(out._notes).toBe('clairNotes');
    expect(crypto.tryDecrypt).not.toHaveBeenCalled();
  });

  it('_title retombe sur item.title si le déchiffrement du titre échoue (null)', async () => {
    const crypto = { tryDecrypt: vi.fn().mockResolvedValue(null) };
    const s = make({}, crypto);
    const item: any = {
      id: 3,
      title: 'fallbackTitre',
      username: null,
      url: null,
      notes: null,
      password_encrypted: 'p',
      category: 'login',
      title_encrypted: 'te',
      username_encrypted: null,
      url_encrypted: null,
      notes_encrypted: null,
    };
    const out = await s.decryptItem(item);
    // titre a le fallback ?? item.title
    expect(out._title).toBe('fallbackTitre');
  });

  it('_username reste null si tryDecrypt renvoie null (pas de fallback)', async () => {
    const crypto = { tryDecrypt: vi.fn().mockResolvedValue(null) };
    const s = make({}, crypto);
    const item: any = {
      id: 4,
      title: 't',
      username: 'ignoré',
      url: null,
      notes: null,
      password_encrypted: 'p',
      category: 'login',
      title_encrypted: null,
      username_encrypted: 'ue',
      url_encrypted: null,
      notes_encrypted: null,
    };
    const out = await s.decryptItem(item);
    expect(out._username).toBeNull();
  });
});

describe('VaultService — hydrateForDisplay()', () => {
  it('remplace les champs par leur plaintext déchiffré', async () => {
    const crypto = {
      tryDecrypt: vi.fn().mockImplementation((c: string) => Promise.resolve('D:' + c)),
    };
    const s = make({}, crypto);
    const item: any = {
      id: 1,
      title: 'old',
      username: 'oldU',
      url: 'oldUrl',
      notes: 'oldN',
      password_encrypted: 'p',
      category: 'login',
      title_encrypted: 'te',
      username_encrypted: 'ue',
      url_encrypted: 'urle',
      notes_encrypted: 'ne',
    };
    const out = await s.hydrateForDisplay(item);
    expect(out.title).toBe('D:te');
    expect(out.username).toBe('D:ue');
    expect(out.url).toBe('D:urle');
    expect(out.notes).toBe('D:ne');
  });

  it('garde les valeurs legacy quand aucun *_encrypted', async () => {
    const crypto = { tryDecrypt: vi.fn() };
    const s = make({}, crypto);
    const item: any = {
      id: 2,
      title: 'legacyT',
      username: 'legacyU',
      url: 'legacyUrl',
      notes: 'legacyN',
      password_encrypted: 'p',
      category: 'login',
      title_encrypted: null,
      username_encrypted: null,
      url_encrypted: null,
      notes_encrypted: null,
    };
    const out = await s.hydrateForDisplay(item);
    expect(out.title).toBe('legacyT');
    expect(out.username).toBe('legacyU');
    expect(out.url).toBe('legacyUrl');
    expect(out.notes).toBe('legacyN');
    expect(crypto.tryDecrypt).not.toHaveBeenCalled();
  });

  it('retombe sur la valeur d’origine si le déchiffrement échoue (null)', async () => {
    const crypto = { tryDecrypt: vi.fn().mockResolvedValue(null) };
    const s = make({}, crypto);
    const item: any = {
      id: 3,
      title: 'origT',
      username: 'origU',
      url: 'origUrl',
      notes: 'origN',
      password_encrypted: 'p',
      category: 'login',
      title_encrypted: 'te',
      username_encrypted: 'ue',
      url_encrypted: 'urle',
      notes_encrypted: 'ne',
    };
    const out = await s.hydrateForDisplay(item);
    expect(out.title).toBe('origT');
    expect(out.username).toBe('origU');
    expect(out.url).toBe('origUrl');
    expect(out.notes).toBe('origN');
  });
});

describe('VaultService — buildEncryptedPayload()', () => {
  it('chiffre uniquement le titre quand les champs optionnels sont absents', async () => {
    const crypto = {
      encrypt: vi.fn().mockImplementation((v: string) => Promise.resolve('E:' + v)),
    };
    const s = make({}, crypto);
    const payload = await s.buildEncryptedPayload({ title: 'Mon titre' });
    expect(payload).toEqual({ title_encrypted: 'E:Mon titre' });
    expect((payload as any).username_encrypted).toBeUndefined();
    expect(crypto.encrypt).toHaveBeenCalledTimes(1);
  });

  it('chiffre tous les champs fournis', async () => {
    const crypto = {
      encrypt: vi.fn().mockImplementation((v: string) => Promise.resolve('E:' + v)),
    };
    const s = make({}, crypto);
    const payload = await s.buildEncryptedPayload({
      title: 'T',
      username: 'U',
      url: 'https://x',
      notes: 'N',
    });
    expect(payload).toEqual({
      title_encrypted: 'E:T',
      username_encrypted: 'E:U',
      url_encrypted: 'E:https://x',
      notes_encrypted: 'E:N',
    });
    expect(crypto.encrypt).toHaveBeenCalledTimes(4);
  });

  it('ignore les champs optionnels vides / null (falsy)', async () => {
    const crypto = {
      encrypt: vi.fn().mockImplementation((v: string) => Promise.resolve('E:' + v)),
    };
    const s = make({}, crypto);
    const payload = await s.buildEncryptedPayload({
      title: 'T',
      username: '',
      url: null,
      notes: undefined,
    });
    expect(payload).toEqual({ title_encrypted: 'E:T' });
    expect(crypto.encrypt).toHaveBeenCalledTimes(1);
  });
});

describe('VaultService — migrateLegacyItems()', () => {
  it('early-return sans clé de chiffrement', async () => {
    const crypto = { hasKey: vi.fn().mockReturnValue(false), encrypt: vi.fn() };
    const http = { get: vi.fn() };
    const s = make(http, crypto);
    await s.migrateLegacyItems();
    expect(http.get).not.toHaveBeenCalled();
    expect(crypto.encrypt).not.toHaveBeenCalled();
  });

  it('migre uniquement les items legacy (sans title_encrypted) et purge le plaintext', async () => {
    const crypto = {
      hasKey: vi.fn().mockReturnValue(true),
      encrypt: vi.fn().mockImplementation((v: string) => Promise.resolve('E:' + v)),
    };
    const items = [
      { id: 1, title: 'legacy', username: 'u1', url: 'url1', notes: 'n1', title_encrypted: null },
      { id: 2, title: 'déjà chiffré', title_encrypted: 'te', username: 'x', url: 'y', notes: 'z' },
    ];
    const http = {
      get: vi.fn().mockReturnValue(of(items)),
      patch: vi.fn().mockReturnValue(of({})),
    };
    const s = make(http, crypto);
    await s.migrateLegacyItems();
    // un seul item migré (id 1)
    expect(http.patch).toHaveBeenCalledTimes(1);
    const [url, body] = http.patch.mock.calls[0];
    expect(url).toContain('/vault/1');
    expect(body).toMatchObject({
      title_encrypted: 'E:legacy',
      username_encrypted: 'E:u1',
      url_encrypted: 'E:url1',
      notes_encrypted: 'E:n1',
      title: null,
      username: null,
      url: null,
      notes: null,
    });
  });

  it('utilise une chaîne vide quand le titre legacy est null', async () => {
    const crypto = {
      hasKey: vi.fn().mockReturnValue(true),
      encrypt: vi.fn().mockImplementation((v: string) => Promise.resolve('E:' + v)),
    };
    const items = [
      { id: 5, title: null, username: null, url: null, notes: null, title_encrypted: null },
    ];
    const http = {
      get: vi.fn().mockReturnValue(of(items)),
      patch: vi.fn().mockReturnValue(of({})),
    };
    const s = make(http, crypto);
    await s.migrateLegacyItems();
    expect(crypto.encrypt).toHaveBeenCalledWith('');
    const [, body] = http.patch.mock.calls[0];
    expect(body.title_encrypted).toBe('E:');
  });

  it('ne fait aucun PATCH quand tous les items sont déjà chiffrés', async () => {
    const crypto = {
      hasKey: vi.fn().mockReturnValue(true),
      encrypt: vi.fn(),
    };
    const items = [{ id: 9, title: 't', title_encrypted: 'te' }];
    const http = {
      get: vi.fn().mockReturnValue(of(items)),
      patch: vi.fn(),
    };
    const s = make(http, crypto);
    await s.migrateLegacyItems();
    expect(http.patch).not.toHaveBeenCalled();
    expect(crypto.encrypt).not.toHaveBeenCalled();
  });
});
