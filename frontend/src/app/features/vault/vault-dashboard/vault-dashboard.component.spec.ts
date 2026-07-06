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
