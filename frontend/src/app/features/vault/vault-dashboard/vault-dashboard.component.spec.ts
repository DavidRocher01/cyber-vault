/**
 * VaultDashboardComponent — logique métier (helpers d'affichage, formatage/validation
 * carte, force de mot de passe, filtrage/comptage réactif, état du formulaire).
 * Le chiffrement lui-même (CryptoService) est couvert ailleurs et n'est pas re-testé ;
 * on mocke tous les services injectés — aucun appel réseau ni crypto réel.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Injector, runInInjectionContext, DestroyRef, signal } from '@angular/core';
import { FormBuilder } from '@angular/forms';
import { Router } from '@angular/router';
import { BehaviorSubject, of } from 'rxjs';
import { HotToastService } from '@ngneat/hot-toast';

import { VaultDashboardComponent } from './vault-dashboard.component';
import { VaultStore } from '../vault.store';
import { AuthService } from '../../../core/services/auth.service';
import { CryptoService } from '../../../core/services/crypto.service';
import { ClipboardService } from '../../../core/services/clipboard.service';
import { PasswordGeneratorService } from '../../../core/services/password-generator.service';
import type { VaultItem } from '../../../core/services/vault.service';

function item(partial: Partial<VaultItem>): VaultItem {
  return {
    id: 1,
    title: 'Titre',
    username: '',
    url: '',
    notes: '',
    category: 'login',
    password_encrypted: '',
    ...partial,
  } as VaultItem;
}

function make() {
  const items$ = new BehaviorSubject<VaultItem[]>([]);
  const store = {
    items$,
    loading$: of(false),
    error$: of(null),
    loadItems: vi.fn(),
    createItem: vi.fn(),
    updateItem: vi.fn(),
    deleteItem: vi.fn(),
  };
  const auth = { logout: vi.fn() };
  const crypto = { decrypt: vi.fn(), clearKey: vi.fn() };
  const injector = Injector.create({
    providers: [
      { provide: VaultStore, useValue: store },
      { provide: AuthService, useValue: auth },
      { provide: CryptoService, useValue: crypto },
      { provide: ClipboardService, useValue: { copy: vi.fn() } },
      { provide: PasswordGeneratorService, useValue: { generate: vi.fn(() => 'GEN') } },
      {
        provide: HotToastService,
        useValue: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
      },
      { provide: Router, useValue: {} },
      { provide: FormBuilder, useClass: FormBuilder },
      { provide: DestroyRef, useValue: { onDestroy: () => () => {} } },
    ],
  });
  const comp = runInInjectionContext(injector, () => new VaultDashboardComponent());
  return { comp, store, items$, auth, crypto };
}

// Fabrique un faux event d'input avec une valeur cible mutable.
function inputEvent(value: string) {
  const input = { value } as HTMLInputElement;
  return { event: { target: input } as unknown as Event, input };
}

describe('VaultDashboardComponent — passwordStrength', () => {
  it('vide -> largeur 0% et label vide', () => {
    const { comp } = make();
    comp.form.controls.password_encrypted.setValue('');
    expect(comp.passwordStrength.width).toBe('0%');
    expect(comp.passwordStrength.label).toBe('');
  });

  it('mot de passe faible', () => {
    const { comp } = make();
    comp.form.controls.password_encrypted.setValue('abc');
    expect(comp.passwordStrength.label).toBe('Faible');
  });

  it('mot de passe excellent (long + variété)', () => {
    const { comp } = make();
    comp.form.controls.password_encrypted.setValue('Abcdefgh12345678!@');
    expect(comp.passwordStrength.label).toBe('Excellent');
    expect(comp.passwordStrength.width).toBe('100%');
  });

  it('progression croissante de la largeur avec la complexité', () => {
    const { comp } = make();
    comp.form.controls.password_encrypted.setValue('abcdefgh');
    const weak = parseInt(comp.passwordStrength.width);
    comp.form.controls.password_encrypted.setValue('Abcdefgh1!');
    const stronger = parseInt(comp.passwordStrength.width);
    expect(stronger).toBeGreaterThan(weak);
  });
});

describe('VaultDashboardComponent — formatage carte', () => {
  it('onCardNumberInput groupe par blocs de 4 et garde 16 chiffres max', () => {
    const { comp } = make();
    const { event, input } = inputEvent('4111abc1111111111111999');
    comp.onCardNumberInput(event);
    expect(comp.form.controls.cardNumber.value).toBe('4111 1111 1111 1111');
    expect(input.value).toBe('4111 1111 1111 1111');
  });

  it('onCvvInput ne garde que les chiffres, 4 max', () => {
    const { comp } = make();
    const { event } = inputEvent('12a34567');
    comp.onCvvInput(event);
    expect(comp.form.controls.cardCvv.value).toBe('1234');
  });

  it('onExpiryInput formate MM/YY', () => {
    const { comp } = make();
    const { event } = inputEvent('1225');
    comp.onExpiryInput(event);
    expect(comp.form.controls.cardExpiry.value).toBe('12/25');
  });

  it('onExpiryInput plafonne le mois à 12', () => {
    const { comp } = make();
    const { event } = inputEvent('1330');
    comp.onExpiryInput(event);
    expect(comp.form.controls.cardExpiry.value).toBe('12/30');
  });

  it('onCardholderInput met en majuscules et retire les chiffres', () => {
    const { comp } = make();
    const { event } = inputEvent("john123 o'neil-2");
    comp.onCardholderInput(event);
    expect(comp.form.controls.username.value).toBe("JOHN O'NEIL-");
  });
});

describe('VaultDashboardComponent — cardErrors (Luhn / cvv / expiry)', () => {
  it("numéro valide (Luhn) -> pas d'erreur de numéro", () => {
    const { comp } = make();
    comp.form.controls.cardNumber.setValue('4111 1111 1111 1111');
    expect(comp.cardErrors.number).toBeUndefined();
  });

  it('numéro trop court', () => {
    const { comp } = make();
    comp.form.controls.cardNumber.setValue('4111');
    expect(comp.cardErrors.number).toBe('Numéro trop court');
  });

  it('numéro qui échoue Luhn', () => {
    const { comp } = make();
    comp.form.controls.cardNumber.setValue('4111 1111 1111 1112');
    expect(comp.cardErrors.number).toBe('Numéro invalide');
  });

  it('cvv trop court', () => {
    const { comp } = make();
    comp.form.controls.cardCvv.setValue('12');
    expect(comp.cardErrors.cvv).toBe('3 ou 4 chiffres requis');
  });

  it('cvv à 3 chiffres -> valide', () => {
    const { comp } = make();
    comp.form.controls.cardCvv.setValue('123');
    expect(comp.cardErrors.cvv).toBeUndefined();
  });

  it('carte expirée', () => {
    const { comp } = make();
    comp.form.controls.cardExpiry.setValue('01/20');
    expect(comp.cardErrors.expiry).toBe('Carte expirée');
  });

  it("date future -> pas d'erreur d'expiration", () => {
    const { comp } = make();
    comp.form.controls.cardExpiry.setValue('12/40');
    expect(comp.cardErrors.expiry).toBeUndefined();
  });
});

describe('VaultDashboardComponent — helpers carte', () => {
  it('cardNumberDigitCount ignore les espaces', () => {
    const { comp } = make();
    comp.form.controls.cardNumber.setValue('4111 1111 11');
    expect(comp.cardNumberDigitCount).toBe(10);
  });

  it('isCardFormValid: faux sans titre', () => {
    const { comp } = make();
    comp.form.controls.cardNumber.setValue('4111 1111 1111 1111');
    expect(comp.isCardFormValid).toBe(false);
  });

  it('isCardFormValid: vrai avec titre + numéro Luhn valide', () => {
    const { comp } = make();
    comp.form.controls.title.setValue('Visa');
    comp.form.controls.cardNumber.setValue('4111 1111 1111 1111');
    expect(comp.isCardFormValid).toBe(true);
  });

  it('parseCardData: null pour entrée nulle', () => {
    expect(make().comp.parseCardData(null)).toBeNull();
  });

  it('parseCardData: null pour texte non-JSON', () => {
    expect(make().comp.parseCardData('pas du json')).toBeNull();
  });

  it('parseCardData: extrait number/cvv/expiry depuis un JSON', () => {
    const parsed = make().comp.parseCardData(
      JSON.stringify({ number: '4111', cvv: '123', expiry: '12/30' })
    );
    expect(parsed).toEqual({ number: '4111', cvv: '123', expiry: '12/30' });
  });

  it('maskCardNumber: valeur vide -> masque complet', () => {
    expect(make().comp.maskCardNumber('')).toBe('•••• •••• •••• ••••');
  });

  it('maskCardNumber: expose seulement les 4 derniers', () => {
    expect(make().comp.maskCardNumber('4111 1111 1111 1234')).toBe('•••• •••• •••• 1234');
  });
});

describe('VaultDashboardComponent — isSubmitValid', () => {
  it('faux sans titre', () => {
    const { comp } = make();
    expect(comp.isSubmitValid()).toBe(false);
  });

  it('login: vrai avec titre + mot de passe', () => {
    const { comp } = make();
    comp.form.patchValue({ title: 'A', category: 'login', password_encrypted: 'pw' });
    expect(comp.isSubmitValid()).toBe(true);
  });

  it('login: faux sans mot de passe', () => {
    const { comp } = make();
    comp.form.patchValue({ title: 'A', category: 'login', password_encrypted: '' });
    expect(comp.isSubmitValid()).toBe(false);
  });

  it('note: vrai avec seulement le titre', () => {
    const { comp } = make();
    comp.form.patchValue({ title: 'Note', category: 'note' });
    expect(comp.isSubmitValid()).toBe(true);
  });

  it('card: délègue à isCardFormValid', () => {
    const { comp } = make();
    comp.form.patchValue({ title: 'Visa', category: 'card', cardNumber: '4111 1111 1111 1111' });
    expect(comp.isSubmitValid()).toBe(true);
  });
});

describe('VaultDashboardComponent — filteredItems (réactif)', () => {
  it('sans filtre -> tous les éléments', () => {
    const { comp, items$ } = make();
    items$.next([item({ id: 1 }), item({ id: 2 })]);
    expect(comp.filteredItems()).toHaveLength(2);
  });

  it('filtre par catégorie active', () => {
    const { comp, items$ } = make();
    items$.next([
      item({ id: 1, category: 'login' }),
      item({ id: 2, category: 'card' }),
      item({ id: 3, category: 'login' }),
    ]);
    comp.activeCategory.set('card');
    const res = comp.filteredItems();
    expect(res).toHaveLength(1);
    expect(res[0].id).toBe(2);
  });

  it('filtre par recherche sur titre/username (insensible à la casse)', () => {
    const { comp, items$ } = make();
    items$.next([
      item({ id: 1, title: 'Gmail', username: 'a@x.com' }),
      item({ id: 2, title: 'GitHub', username: 'b@y.com' }),
    ]);
    comp.searchQuery.set('git');
    const res = comp.filteredItems();
    expect(res).toHaveLength(1);
    expect(res[0].id).toBe(2);
  });

  it('combine catégorie et recherche', () => {
    const { comp, items$ } = make();
    items$.next([
      item({ id: 1, title: 'Gmail', category: 'login' }),
      item({ id: 2, title: 'Gmail card', category: 'card' }),
    ]);
    comp.activeCategory.set('login');
    comp.searchQuery.set('gmail');
    expect(comp.filteredItems().map(i => i.id)).toEqual([1]);
  });
});

describe('VaultDashboardComponent — categoryCounts (réactif)', () => {
  it('compte le total et par catégorie', () => {
    const { comp, items$ } = make();
    items$.next([
      item({ id: 1, category: 'login' }),
      item({ id: 2, category: 'login' }),
      item({ id: 3, category: 'card' }),
    ]);
    const counts = comp.categoryCounts();
    expect(counts.all).toBe(3);
    expect(counts.login).toBe(2);
    expect(counts.card).toBe(1);
  });

  it('total 0 quand le coffre est vide', () => {
    const { comp } = make();
    expect(comp.categoryCounts().all).toBe(0);
  });
});

describe('VaultDashboardComponent — état du formulaire', () => {
  it('formTitle: "Nouvelle entrée" en création', () => {
    const { comp } = make();
    expect(comp.formTitle).toBe('Nouvelle entrée');
  });

  it('formTitle: "Modifier l\'entrée" en édition', () => {
    const { comp } = make();
    comp.editingItem.set(item({ id: 7 }));
    expect(comp.formTitle).toBe("Modifier l'entrée");
  });

  it('openCreate: réinitialise, ouvre le formulaire, sans élément en édition', () => {
    const { comp } = make();
    comp.editingItem.set(item({ id: 9 }));
    comp.openCreate();
    expect(comp.showForm()).toBe(true);
    expect(comp.editingItem()).toBeNull();
    expect(comp.form.controls.category.value).toBe('login');
  });

  it("openEdit: charge l'élément et n'expose pas le mot de passe chiffré", () => {
    const { comp } = make();
    comp.openEdit(item({ id: 4, title: 'X', category: 'wifi', password_encrypted: 'ENC' }));
    expect(comp.editingItem()?.id).toBe(4);
    expect(comp.showForm()).toBe(true);
    expect(comp.form.controls.title.value).toBe('X');
    expect(comp.form.controls.category.value).toBe('wifi');
    expect(comp.form.controls.password_encrypted.value).toBe('');
  });

  it("closeForm: ferme et vide l'édition", () => {
    const { comp } = make();
    comp.openEdit(item({ id: 4 }));
    comp.closeForm();
    expect(comp.showForm()).toBe(false);
    expect(comp.editingItem()).toBeNull();
  });

  it('generatePassword: injecte la valeur générée et révèle le champ', () => {
    const { comp } = make();
    comp.generatePassword();
    expect(comp.form.controls.password_encrypted.value).toBe('GEN');
    expect(comp.showPasswordInForm()).toBe(true);
  });
});

describe('VaultDashboardComponent — submit()', () => {
  it('création login sans secret -> aucun appel au store', () => {
    const { comp, store } = make();
    comp.form.patchValue({ title: 'A', category: 'login', password_encrypted: '' });
    comp.submit();
    expect(store.createItem).not.toHaveBeenCalled();
  });

  it('création login valide -> createItem appelé et formulaire fermé', () => {
    const { comp, store } = make();
    comp.form.patchValue({ title: 'A', category: 'login', password_encrypted: 'pw' });
    comp.submit();
    expect(store.createItem).toHaveBeenCalledTimes(1);
    expect(comp.showForm()).toBe(false);
  });

  it('création carte -> secret sérialisé en JSON (number/cvv/expiry)', () => {
    const { comp, store } = make();
    comp.form.patchValue({
      title: 'Visa',
      category: 'card',
      cardNumber: '4111 1111 1111 1111',
      cardCvv: '123',
      cardExpiry: '12/30',
    });
    comp.submit();
    const payload = store.createItem.mock.calls[0][0];
    const secret = JSON.parse(payload.password_encrypted);
    expect(secret.number).toBe('4111 1111 1111 1111');
    expect(secret.cvv).toBe('123');
    expect(secret.expiry).toBe('12/30');
  });

  it("édition -> updateItem appelé avec l'id existant", () => {
    const { comp, store } = make();
    comp.openEdit(item({ id: 42, title: 'X', category: 'login' }));
    comp.form.controls.password_encrypted.setValue('newpw');
    comp.submit();
    expect(store.updateItem).toHaveBeenCalledTimes(1);
    expect(store.updateItem.mock.calls[0][0].id).toBe(42);
  });
});

describe('VaultDashboardComponent — delete() & logout()', () => {
  it('delete: appelle le store et nettoie le mot de passe révélé', () => {
    const { comp, store } = make();
    comp.revealedPasswords[5] = 'secret';
    comp.delete(5);
    expect(store.deleteItem).toHaveBeenCalledWith(5);
    expect(comp.revealedPasswords[5]).toBeUndefined();
  });

  it('logout: purge la clé crypto puis déconnecte', () => {
    const { comp, auth, crypto } = make();
    comp.logout();
    expect(crypto.clearKey).toHaveBeenCalled();
    expect(auth.logout).toHaveBeenCalled();
  });
});

describe('VaultDashboardComponent — passwordStrength (paliers intermédiaires)', () => {
  it('score 2 -> Moyen', () => {
    const { comp } = make();
    comp.form.controls.password_encrypted.setValue('abcdefghijklmnop'); // long, minuscules only
    expect(comp.passwordStrength.label).toBe('Moyen');
  });

  it('score 3 -> Bon', () => {
    const { comp } = make();
    comp.form.controls.password_encrypted.setValue('Abcdefgh1'); // len>=8 + maj + chiffre
    expect(comp.passwordStrength.label).toBe('Bon');
  });

  it('score 4 -> Fort', () => {
    const { comp } = make();
    comp.form.controls.password_encrypted.setValue('Abcdefgh1!'); // len>=8 + maj + chiffre + spécial
    expect(comp.passwordStrength.label).toBe('Fort');
    expect(comp.passwordStrength.width).toBe('85%');
  });
});

describe('VaultDashboardComponent — onExpiryInput (suppression)', () => {
  it("en suppression sous 2 chiffres, ne ré-insère pas le '/'", () => {
    const { comp } = make();
    const input = { value: '1' } as HTMLInputElement;
    (input as any)._prevExpiry = '12'; // saisie précédente plus longue -> suppression
    comp.onExpiryInput({ target: input } as unknown as Event);
    expect(comp.form.controls.cardExpiry.value).toBe('1');
    expect(input.value).toBe('1');
  });
});

describe('VaultDashboardComponent — cardErrors (mois invalide)', () => {
  it('mois 00 -> "Mois invalide"', () => {
    const { comp } = make();
    comp.form.controls.cardExpiry.setValue('00/30');
    expect(comp.cardErrors.expiry).toBe('Mois invalide (01–12)');
  });
});

describe('VaultDashboardComponent — _luhn (chiffre doublé > 9)', () => {
  it('accepte un numéro Mastercard test valide (branche n>9)', () => {
    const { comp } = make();
    comp.form.controls.cardNumber.setValue('5555 5555 5555 4444');
    expect(comp.cardErrors.number).toBeUndefined();
  });
});

describe('VaultDashboardComponent — parseCardData / maskCardNumber (branches)', () => {
  it('parseCardData: JSON valide sans clés carte -> null', () => {
    expect(make().comp.parseCardData(JSON.stringify({ foo: 'bar' }))).toBeNull();
  });

  it('parseCardData: complète les champs manquants par des chaînes vides', () => {
    const parsed = make().comp.parseCardData(JSON.stringify({ number: '4111' }));
    expect(parsed).toEqual({ number: '4111', cvv: '', expiry: '' });
  });

  it('maskCardNumber: numéro de moins de 4 chiffres reste tel quel', () => {
    expect(make().comp.maskCardNumber('12')).toBe('•••• •••• •••• 12');
  });
});

describe('VaultDashboardComponent — filteredItems (username null)', () => {
  it('gère un username null lors de la recherche par titre', () => {
    const { comp, items$ } = make();
    items$.next([item({ id: 1, title: 'Gmail', username: null as any })]);
    comp.searchQuery.set('gmail');
    expect(comp.filteredItems().map(i => i.id)).toEqual([1]);
  });
});

describe('VaultDashboardComponent — submit() (branches restantes)', () => {
  it('création sans titre -> aucun appel au store', () => {
    const { comp, store } = make();
    comp.form.patchValue({ title: '', category: 'login', password_encrypted: 'pw' });
    comp.submit();
    expect(store.createItem).not.toHaveBeenCalled();
  });

  it('création carte sans numéro -> aucun appel au store', () => {
    const { comp, store } = make();
    comp.form.patchValue({ title: 'Visa', category: 'card', cardNumber: '' });
    comp.submit();
    expect(store.createItem).not.toHaveBeenCalled();
  });

  it("création note -> secret vide et pas d'exigence de mot de passe", () => {
    const { comp, store } = make();
    comp.form.patchValue({ title: 'Note', category: 'note', notes: 'contenu' });
    comp.submit();
    expect(store.createItem).toHaveBeenCalledTimes(1);
    expect(store.createItem.mock.calls[0][0].password_encrypted).toBe('');
    expect(comp.showForm()).toBe(false);
  });

  it('édition sans nouveau secret -> updateItem sans champ password_encrypted', () => {
    const { comp, store } = make();
    comp.openEdit(item({ id: 3, title: 'X', category: 'login', password_encrypted: 'OLD' }));
    // password_encrypted du formulaire vidé par openEdit -> pas réécrit
    comp.submit();
    const payload = store.updateItem.mock.calls[0][0];
    expect(payload.id).toBe(3);
    expect('password_encrypted' in payload).toBe(false);
  });
});

describe('VaultDashboardComponent — toggleReveal()', () => {
  it('déjà révélé -> masque (supprime la clé)', async () => {
    const { comp } = make();
    comp.revealedPasswords[1] = 'clair';
    await comp.toggleReveal(item({ id: 1, password_encrypted: 'ENC' }));
    expect(comp.revealedPasswords[1]).toBeUndefined();
  });

  it('sans secret chiffré -> chaîne vide sans déchiffrement', async () => {
    const { comp, crypto } = make();
    await comp.toggleReveal(item({ id: 2, password_encrypted: '' }));
    expect(comp.revealedPasswords[2]).toBe('');
    expect(crypto.decrypt).not.toHaveBeenCalled();
  });

  it('déchiffrement OK -> stocke le clair', async () => {
    const { comp, crypto } = make();
    crypto.decrypt.mockResolvedValue('motdepasse');
    await comp.toggleReveal(item({ id: 3, password_encrypted: 'ENC' }));
    expect(comp.revealedPasswords[3]).toBe('motdepasse');
  });

  it('échec de déchiffrement -> null + toast erreur', async () => {
    const { comp, crypto } = make();
    crypto.decrypt.mockRejectedValue(new Error('boom'));
    const toast = (comp as any).toast;
    await comp.toggleReveal(item({ id: 4, password_encrypted: 'ENC' }));
    expect(comp.revealedPasswords[4]).toBeNull();
    expect(toast.error).toHaveBeenCalledWith('Erreur de déchiffrement');
  });
});

describe('VaultDashboardComponent — copyPassword()', () => {
  it('sans secret -> avertit et ne copie rien', async () => {
    const { comp } = make();
    const toast = (comp as any).toast;
    const clip = (comp as any).clipboardService;
    await comp.copyPassword(item({ id: 1, password_encrypted: '' }));
    expect(toast.warning).toHaveBeenCalledWith('Aucun secret à copier');
    expect(clip.copy).not.toHaveBeenCalled();
  });

  it('login -> copie le clair et marque copiedId', async () => {
    const { comp, crypto } = make();
    crypto.decrypt.mockResolvedValue('secret42');
    const clip = (comp as any).clipboardService;
    const toast = (comp as any).toast;
    await comp.copyPassword(item({ id: 5, category: 'login', password_encrypted: 'ENC' }));
    expect(clip.copy).toHaveBeenCalledWith('secret42');
    expect(comp.copiedId).toBe(5);
    expect(toast.success).toHaveBeenCalledWith(expect.stringContaining('Mot de passe copié'));
  });

  it('réinitialise copiedId après le délai (30s presse-papiers)', async () => {
    vi.useFakeTimers();
    try {
      const { comp, crypto } = make();
      crypto.decrypt.mockResolvedValue('secret42');
      await comp.copyPassword(item({ id: 9, category: 'login', password_encrypted: 'ENC' }));
      expect(comp.copiedId).toBe(9);
      vi.advanceTimersByTime(2000);
      expect(comp.copiedId).toBeNull();
    } finally {
      vi.useRealTimers();
    }
  });

  it('carte -> copie uniquement le numéro extrait du JSON', async () => {
    const { comp, crypto } = make();
    crypto.decrypt.mockResolvedValue(JSON.stringify({ number: '4111 1111 1111 1111', cvv: '123' }));
    const clip = (comp as any).clipboardService;
    const toast = (comp as any).toast;
    await comp.copyPassword(item({ id: 6, category: 'card', password_encrypted: 'ENC' }));
    expect(clip.copy).toHaveBeenCalledWith('4111 1111 1111 1111');
    expect(toast.success).toHaveBeenCalledWith(expect.stringContaining('Numéro de carte copié'));
  });

  it('carte avec clair non-JSON -> copie le clair brut', async () => {
    const { comp, crypto } = make();
    crypto.decrypt.mockResolvedValue('pas-du-json');
    const clip = (comp as any).clipboardService;
    await comp.copyPassword(item({ id: 7, category: 'card', password_encrypted: 'ENC' }));
    expect(clip.copy).toHaveBeenCalledWith('pas-du-json');
  });

  it('échec de déchiffrement -> toast erreur, pas de copie', async () => {
    const { comp, crypto } = make();
    crypto.decrypt.mockRejectedValue(new Error('boom'));
    const clip = (comp as any).clipboardService;
    const toast = (comp as any).toast;
    await comp.copyPassword(item({ id: 8, category: 'login', password_encrypted: 'ENC' }));
    expect(clip.copy).not.toHaveBeenCalled();
    expect(toast.error).toHaveBeenCalledWith('Erreur de déchiffrement');
  });
});

describe('VaultDashboardComponent — exportVault()', () => {
  const flush = async () => {
    await Promise.resolve();
    await new Promise(r => setTimeout(r, 0));
    await new Promise(r => setTimeout(r, 0));
  };

  it('déchiffre chaque secret et déclenche le téléchargement blob', async () => {
    const { comp, crypto, items$ } = make();
    crypto.decrypt.mockResolvedValue('clair');
    items$.next([
      item({ id: 1, title: 'A', password_encrypted: 'ENC' }),
      item({ id: 2, title: 'B', password_encrypted: '' }),
    ]);
    const anchor = { href: '', download: '', click: vi.fn() };
    const createSpy = vi
      .spyOn(document, 'createElement')
      .mockReturnValue(anchor as unknown as HTMLAnchorElement);
    (URL as any).createObjectURL = vi.fn(() => 'blob:x');
    (URL as any).revokeObjectURL = vi.fn();
    const toast = (comp as any).toast;

    await comp.exportVault();
    await flush();

    expect(crypto.decrypt).toHaveBeenCalledTimes(1); // seul l'item avec secret
    expect(anchor.click).toHaveBeenCalled();
    expect((URL as any).revokeObjectURL).toHaveBeenCalledWith('blob:x');
    expect(toast.success).toHaveBeenCalledWith('Export téléchargé');
    createSpy.mockRestore();
  });

  it('un secret indéchiffrable est exporté avec password null (pas de crash)', async () => {
    const { comp, crypto, items$ } = make();
    crypto.decrypt.mockRejectedValue(new Error('boom'));
    items$.next([item({ id: 1, title: 'A', password_encrypted: 'ENC' })]);
    const anchor = { href: '', download: '', click: vi.fn() };
    const createSpy = vi
      .spyOn(document, 'createElement')
      .mockReturnValue(anchor as unknown as HTMLAnchorElement);
    (URL as any).createObjectURL = vi.fn(() => 'blob:y');
    (URL as any).revokeObjectURL = vi.fn();
    const toast = (comp as any).toast;

    await comp.exportVault();
    await flush();

    expect(anchor.click).toHaveBeenCalled();
    expect(toast.success).toHaveBeenCalledWith('Export téléchargé');
    createSpy.mockRestore();
  });
});

describe('VaultDashboardComponent — ngOnInit / openCreate (effets différés)', () => {
  it('ngOnInit charge les items et efface le titulaire en catégorie carte', () => {
    vi.useFakeTimers();
    try {
      const { comp, store } = make();
      comp.ngOnInit();
      expect(store.loadItems).toHaveBeenCalled();
      comp.form.controls.username.setValue('AUTOFILL');
      comp.form.controls.category.setValue('card');
      vi.advanceTimersByTime(60);
      expect(comp.form.controls.username.value).toBe('');
    } finally {
      vi.useRealTimers();
    }
  });

  it('openCreate efface le titulaire après le tick de rendu', () => {
    vi.useFakeTimers();
    try {
      const { comp } = make();
      comp.openCreate();
      comp.form.controls.username.setValue('AUTOFILL');
      vi.advanceTimersByTime(60);
      expect(comp.form.controls.username.value).toBe('');
    } finally {
      vi.useRealTimers();
    }
  });
});

describe('VaultDashboardComponent — métadonnées statiques', () => {
  it('categories couvre toutes les catégories + "Tout"', () => {
    const ids = make().comp.categories.map(c => c.id);
    expect(ids).toEqual(['all', 'login', 'card', 'note', 'wifi', 'other']);
  });

  it('categoryIcons associe une icône à chaque catégorie', () => {
    const { comp } = make();
    expect(comp.categoryIcons['login']).toBe('person');
    expect(comp.categoryIcons['card']).toBe('credit_card');
    expect(Object.keys(comp.categoryIcons)).toHaveLength(5);
  });
});
