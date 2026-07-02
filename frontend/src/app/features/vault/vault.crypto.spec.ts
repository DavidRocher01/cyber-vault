import { describe, it, expect, beforeEach } from 'vitest';
import { CryptoService } from '../../core/services/crypto.service';
import { VaultService, VaultItem } from '../../core/services/vault.service';

// Invariants de chiffrement zero-knowledge du vault.
//
// Le vault chiffre ses champs d'affichage (title/username/url/notes) via
// VaultService.buildEncryptedPayload (qui délègue à CryptoService.encrypt) et
// les déchiffre via hydrateForDisplay / decryptItem. Le mot de passe est
// chiffré directement par CryptoService.encrypt dans VaultStore.
//
// On teste ici la composition réelle CryptoService + VaultService avec la vraie
// WebCrypto (crypto.subtle / AES-GCM / PBKDF2), fournie par le runtime Node dans
// l'environnement Vitest (cf. crypto.service.spec.ts existant).

// Nombre d'itérations faible pour ne pas ralentir la suite (cf. crypto.service.spec.ts).
const ITER = 1_000;

// HttpClient factice : les méthodes crypto testées ici ne touchent jamais le réseau.
const httpStub: any = {
  get: () => {
    throw new Error('HTTP ne doit pas être appelé dans ce test');
  },
  post: () => {
    throw new Error('HTTP ne doit pas être appelé dans ce test');
  },
  patch: () => {
    throw new Error('HTTP ne doit pas être appelé dans ce test');
  },
  delete: () => {
    throw new Error('HTTP ne doit pas être appelé dans ce test');
  },
};

/** Construit un VaultItem minimal en surchargeant les champs pertinents. */
function makeItem(overrides: Partial<VaultItem>): VaultItem {
  return {
    id: 1,
    title: null,
    username: null,
    password_encrypted: '',
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

describe('Vault — invariants de chiffrement zero-knowledge', () => {
  let crypto1: CryptoService;
  let vault1: VaultService;

  beforeEach(async () => {
    crypto1 = new CryptoService();
    await crypto1.deriveKey('masterpass123', 'user@test.com', ITER);
    vault1 = new VaultService(httpStub, crypto1);
  });

  describe('buildEncryptedPayload → hydrateForDisplay (round-trip des champs)', () => {
    it('round-trip: les champs déchiffrés correspondent au clair d’origine', async () => {
      const plain = {
        title: 'GitHub',
        username: 'david@example.com',
        url: 'https://github.com',
        notes: 'note secrète avec accents éàü et symboles !@#$%',
      };
      const enc = await vault1.buildEncryptedPayload(plain);

      const item = makeItem({
        title_encrypted: enc.title_encrypted,
        username_encrypted: enc.username_encrypted ?? null,
        url_encrypted: enc.url_encrypted ?? null,
        notes_encrypted: enc.notes_encrypted ?? null,
      });

      const hydrated = await vault1.hydrateForDisplay(item);
      expect(hydrated.title).toBe(plain.title);
      expect(hydrated.username).toBe(plain.username);
      expect(hydrated.url).toBe(plain.url);
      expect(hydrated.notes).toBe(plain.notes);
    });

    it('round-trip via decryptItem: peuple les champs _title/_username/_url/_notes', async () => {
      const plain = { title: 'AWS', username: 'root', url: 'https://aws', notes: 'n' };
      const enc = await vault1.buildEncryptedPayload(plain);

      const item = makeItem({
        title_encrypted: enc.title_encrypted,
        username_encrypted: enc.username_encrypted ?? null,
        url_encrypted: enc.url_encrypted ?? null,
        notes_encrypted: enc.notes_encrypted ?? null,
      });

      const decrypted = await vault1.decryptItem(item);
      expect(decrypted._title).toBe(plain.title);
      expect(decrypted._username).toBe(plain.username);
      expect(decrypted._url).toBe(plain.url);
      expect(decrypted._notes).toBe(plain.notes);
    });

    it('les champs optionnels vides ne produisent PAS de blob chiffré', async () => {
      const enc = await vault1.buildEncryptedPayload({ title: 'Seul', username: '', url: null });
      expect(enc.title_encrypted).toBeTypeOf('string');
      expect(enc.title_encrypted.length).toBeGreaterThan(0);
      // username vide et url null : pas de clé *_encrypted
      expect(enc.username_encrypted).toBeUndefined();
      expect(enc.url_encrypted).toBeUndefined();
      expect(enc.notes_encrypted).toBeUndefined();
    });
  });

  describe('confidentialité: le ciphertext ne fuit pas le clair', () => {
    it('aucun champ chiffré ne contient le clair (en clair ni en base64)', async () => {
      const plain = {
        title: 'MonTitreSecret',
        username: 'utilisateurSecret',
        url: 'https://cible-secrete.example',
        notes: 'NotesUltraConfidentielles',
      };
      const enc = await vault1.buildEncryptedPayload(plain);
      const blobs = [
        enc.title_encrypted,
        enc.username_encrypted,
        enc.url_encrypted,
        enc.notes_encrypted,
      ];
      for (const value of Object.values(plain)) {
        const b64 = btoa(value);
        for (const blob of blobs) {
          expect(blob ?? '').not.toContain(value);
          expect(blob ?? '').not.toContain(b64);
        }
      }
    });

    it('deux chiffrements du même clair donnent des blobs différents (IV aléatoire)', async () => {
      const a = await vault1.buildEncryptedPayload({ title: 'idem' });
      const b = await vault1.buildEncryptedPayload({ title: 'idem' });
      expect(a.title_encrypted).not.toBe(b.title_encrypted);
      // ...mais les deux redonnent bien le même clair une fois déchiffrés
      expect(await crypto1.decrypt(a.title_encrypted)).toBe('idem');
      expect(await crypto1.decrypt(b.title_encrypted)).toBe('idem');
    });
  });

  describe('isolation par clé: une mauvaise clé ne déchiffre pas (pas de fuite en clair)', () => {
    it('hydrateForDisplay avec une clé dérivée d’un autre master ne rend pas le clair', async () => {
      const plain = { title: 'TitreConfidentiel', username: 'userX' };
      const enc = await vault1.buildEncryptedPayload(plain);

      // Un second service avec un master password DIFFÉRENT → clé différente.
      const cryptoWrong = new CryptoService();
      await cryptoWrong.deriveKey('AUTREmaster999', 'user@test.com', ITER);
      const vaultWrong = new VaultService(httpStub, cryptoWrong);

      const item = makeItem({
        title: null, // aucun fallback plaintext
        username: null,
        title_encrypted: enc.title_encrypted,
        username_encrypted: enc.username_encrypted ?? null,
      });

      const hydrated = await vaultWrong.hydrateForDisplay(item);
      // tryDecrypt échoue → ?? item.title (null). Jamais le clair d'origine.
      expect(hydrated.title).not.toBe(plain.title);
      expect(hydrated.title).toBeNull();
      expect(hydrated.username).not.toBe(plain.username);
      expect(hydrated.username).toBeNull();
    });

    it('decrypt() direct avec une mauvaise clé lève une exception (intégrité AES-GCM)', async () => {
      const enc = await vault1.buildEncryptedPayload({ title: 'x' });

      const cryptoWrong = new CryptoService();
      await cryptoWrong.deriveKey('mauvais', 'user@test.com', ITER);

      await expect(cryptoWrong.decrypt(enc.title_encrypted)).rejects.toThrow();
    });

    it('un ciphertext altéré (tampering) échoue au déchiffrement', async () => {
      const enc = await vault1.buildEncryptedPayload({ title: 'integrite' });
      // Corrompt le dernier caractère base64 → le tag GCM ne valide plus.
      const bytes = Uint8Array.from(atob(enc.title_encrypted), c => c.charCodeAt(0));
      bytes[bytes.length - 1] ^= 0xff;
      const tampered = btoa(String.fromCharCode(...bytes));

      // tryDecrypt renvoie null (pas de clair), decrypt lève.
      expect(await crypto1.tryDecrypt(tampered)).toBeNull();
    });
  });

  describe('garde-fou: pas de chiffrement sans clé initialisée', () => {
    it('buildEncryptedPayload sans clé dérivée lève (aucun blob produit)', async () => {
      const noKeyCrypto = new CryptoService();
      const noKeyVault = new VaultService(httpStub, noKeyCrypto);
      expect(noKeyCrypto.hasKey()).toBe(false);
      await expect(noKeyVault.buildEncryptedPayload({ title: 'x' })).rejects.toThrow();
    });
  });

  describe('champs legacy: fallback plaintext quand pas de blob *_encrypted', () => {
    it('hydrateForDisplay laisse le plaintext legacy intact si aucun *_encrypted', async () => {
      const item = makeItem({
        title: 'legacyTitre',
        username: 'legacyUser',
        url: 'legacyUrl',
        notes: 'legacyNotes',
      });
      const hydrated = await vault1.hydrateForDisplay(item);
      expect(hydrated.title).toBe('legacyTitre');
      expect(hydrated.username).toBe('legacyUser');
      expect(hydrated.url).toBe('legacyUrl');
      expect(hydrated.notes).toBe('legacyNotes');
    });

    it('decryptItem: un blob indéchiffrable retombe sur le plaintext existant pour le titre', async () => {
      // title_encrypted présent mais chiffré avec une AUTRE clé → tryDecrypt null.
      const cryptoOther = new CryptoService();
      await cryptoOther.deriveKey('autre', 'user@test.com', ITER);
      const foreign = await cryptoOther.encrypt('titreEtranger');

      const item = makeItem({ title: 'fallbackTitre', title_encrypted: foreign });
      const decrypted = await vault1.decryptItem(item);
      // _title = tryDecrypt(...) ?? item.title → item.title (fallback)
      expect(decrypted._title).toBe('fallbackTitre');
    });
  });
});
