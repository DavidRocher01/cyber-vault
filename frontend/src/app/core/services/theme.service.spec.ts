import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { Injector, PLATFORM_ID, runInInjectionContext } from '@angular/core';
import { DOCUMENT } from '@angular/common';

import { ThemeService } from './theme.service';

const CLE = 'cs_theme';

/**
 * Ce service etait EXCLU de la mesure de couverture, sans justification ecrite,
 * et n'avait aucun test : 12,5 % une fois l'exclusion levee le 2026-08-18.
 * Il ecrit dans `localStorage` et touche `documentElement` — deux choses qui
 * n'existent pas au prerendu.
 */
function creer(plateforme: 'browser' | 'server') {
  const classes = new Set<string>();
  const faux = {
    documentElement: {
      classList: {
        toggle: (nom: string, actif: boolean) => (actif ? classes.add(nom) : classes.delete(nom)),
      },
    },
  };
  const injector = Injector.create({
    providers: [
      { provide: PLATFORM_ID, useValue: plateforme },
      { provide: DOCUMENT, useValue: faux },
      { provide: ThemeService, useClass: ThemeService },
    ],
  });
  const service = runInInjectionContext(injector, () => injector.get(ThemeService));
  return { service, classes };
}

describe('ThemeService — dans le navigateur', () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => localStorage.clear());

  it('demarre en sombre quand rien n’est stocke', () => {
    expect(creer('browser').service.theme()).toBe('dark');
  });

  it('relit le theme choisi precedemment', () => {
    localStorage.setItem(CLE, 'light');

    expect(creer('browser').service.theme()).toBe('light');
  });

  it('bascule, persiste, et pose la classe sur la racine', () => {
    const { service, classes } = creer('browser');

    service.toggle();

    expect(service.theme()).toBe('light');
    expect(localStorage.getItem(CLE)).toBe('light');
    expect(classes.has('light-mode')).toBe(true);
  });

  it('rebascule en sombre et retire la classe', () => {
    localStorage.setItem(CLE, 'light');
    const { service, classes } = creer('browser');

    service.toggle();

    expect(service.theme()).toBe('dark');
    expect(localStorage.getItem(CLE)).toBe('dark');
    expect(classes.has('light-mode')).toBe(false);
  });

  it('apply() aligne la page sur le theme deja charge', () => {
    // Au demarrage, le signal vient du stockage mais le DOM ne sait rien encore.
    localStorage.setItem(CLE, 'light');
    const { service, classes } = creer('browser');
    expect(classes.has('light-mode')).toBe(false);

    service.apply();

    expect(classes.has('light-mode')).toBe(true);
  });
});

describe('ThemeService — au prerendu', () => {
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

  it('demarre en sombre sans toucher au stockage', () => {
    expect(creer('server').service.theme()).toBe('dark');
  });

  it('bascule en memoire seulement, sans toucher au DOM', () => {
    const { service, classes } = creer('server');

    expect(() => service.toggle()).not.toThrow();
    expect(service.theme()).toBe('light');
    expect(classes.size).toBe(0);
  });

  it('apply() ne fait rien', () => {
    const { service, classes } = creer('server');

    expect(() => service.apply()).not.toThrow();
    expect(classes.size).toBe(0);
  });
});
