import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { Injector, PLATFORM_ID, runInInjectionContext } from '@angular/core';

import { I18nService } from './i18n.service';

const CLE = 'cs_lang';

/**
 * Ce service etait EXCLU de la mesure de couverture, sans justification ecrite,
 * et n'avait aucun test : 21,4 % une fois l'exclusion levee le 2026-08-18.
 */
function creer(plateforme: 'browser' | 'server') {
  const injector = Injector.create({
    providers: [
      { provide: PLATFORM_ID, useValue: plateforme },
      { provide: I18nService, useClass: I18nService },
    ],
  });
  return runInInjectionContext(injector, () => injector.get(I18nService));
}

describe('I18nService — dans le navigateur', () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => localStorage.clear());

  it('demarre en francais quand rien n’est stocke', () => {
    expect(creer('browser').lang()).toBe('fr');
  });

  it('relit la langue choisie precedemment', () => {
    localStorage.setItem(CLE, 'en');

    expect(creer('browser').lang()).toBe('en');
  });

  it('traduit dans la langue courante', () => {
    const service = creer('browser');

    expect(service.t('nav.logout')).toBe('Déconnexion');

    service.toggle();

    expect(service.t('nav.logout')).toBe('Logout');
  });

  it('bascule et persiste', () => {
    const service = creer('browser');

    service.toggle();

    expect(service.lang()).toBe('en');
    expect(localStorage.getItem(CLE)).toBe('en');
  });

  it('rend la cle telle quelle si elle est inconnue', () => {
    // Repli volontaire : mieux vaut afficher `panier.vide` qu'une chaine vide,
    // parce que la cle brute se voit et se corrige.
    expect(creer('browser').t('cle.qui.n.existe.pas')).toBe('cle.qui.n.existe.pas');
  });
});

describe('I18nService — les deux dictionnaires se correspondent', () => {
  /**
   * CE QUE CE TEST DEFEND. Une cle presente en francais mais absente en anglais
   * ne provoque aucune erreur : `t()` retourne la cle brute. Un visiteur
   * anglophone lit donc « nav.dashboard » a l'ecran, et rien ne le signale —
   * ni compilation, ni execution. C'est le genre de defaut qu'on ne voit qu'en
   * production, et seulement si quelqu'un pense a changer de langue.
   */
  it('aucune cle ne manque d’un cote ou de l’autre', () => {
    const service = creer('browser');
    const enFrancais = new Set<string>();
    const enAnglais = new Set<string>();

    // On passe par `t()` plutot que par le dictionnaire, qui n'est pas exporte :
    // une cle absente se trahit en renvoyant sa propre valeur.
    const toutesLesCles = [
      'nav.home',
      'nav.dashboard',
      'nav.logout',
      'nav.profile',
      'hero.title',
      'hero.subtitle',
      'hero.cta',
      'hero.pricing',
      'pricing.title',
      'pricing.subtitle',
      'pricing.monthly',
      'pricing.choose',
      'faq.title',
      'dashboard.sites',
      'dashboard.add',
      'dashboard.scan',
      'dashboard.noSites',
      'scan.all',
      'scan.done',
      'scan.running',
      'scan.error',
      'plan.manage',
    ];

    for (const cle of toutesLesCles) {
      if (service.t(cle) !== cle) enFrancais.add(cle);
    }
    service.toggle();
    for (const cle of toutesLesCles) {
      if (service.t(cle) !== cle) enAnglais.add(cle);
    }

    const manquantesEnAnglais = [...enFrancais].filter(c => !enAnglais.has(c));
    const manquantesEnFrancais = [...enAnglais].filter(c => !enFrancais.has(c));

    expect(manquantesEnAnglais, 'traduites en fr, pas en en').toEqual([]);
    expect(manquantesEnFrancais, 'traduites en en, pas en fr').toEqual([]);
    // Garde du garde : une liste vide ferait passer les deux assertions.
    expect(enFrancais.size).toBe(toutesLesCles.length);
  });
});

describe('I18nService — au prerendu', () => {
  const vrai = globalThis.localStorage;

  beforeEach(() => {
    Object.defineProperty(globalThis, 'localStorage', {
      configurable: true,
      get() {
        throw new ReferenceError('localStorage is not defined');
      },
    });
  });

  afterEach(() => {
    Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: vrai });
  });

  it('demarre en francais sans toucher au stockage', () => {
    expect(creer('server').lang()).toBe('fr');
  });

  it('bascule en memoire seulement', () => {
    const service = creer('server');

    expect(() => service.toggle()).not.toThrow();
    expect(service.lang()).toBe('en');
  });
});
