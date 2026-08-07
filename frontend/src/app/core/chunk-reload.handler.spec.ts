import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ErrorHandler } from '@angular/core';

import { ChunkReloadHandler, estEchecDeChargement } from './chunk-reload.handler';

/**
 * CE QUE CES TESTS PROTÈGENT. Un onglet ouvert pendant un déploiement demande
 * des morceaux que `s3 sync --delete` a supprimés. Sans ce gestionnaire, la
 * navigation échoue et Angular ne dit rien : le clic paraît mort. Vu en
 * production le 2026-08-07 sur les pages NIS2 et ISO 27001.
 *
 * Les deux garde-fous comptent autant que le rechargement lui-même : ne pas
 * avaler les autres erreurs, et ne jamais boucler.
 */

/** Construit le gestionnaire sans DI, en fixant la plateforme. */
function make(navigateur = true): ChunkReloadHandler {
  const h = Object.create(ChunkReloadHandler.prototype) as ChunkReloadHandler;
  (h as any).plateforme = navigateur ? 'browser' : 'server';
  (h as any).defaut = { handleError: vi.fn() };
  return h;
}

function defaut(h: ChunkReloadHandler) {
  return (h as any).defaut.handleError;
}

describe('estEchecDeChargement()', () => {
  const echecs = [
    new Error('ChunkLoadError: Loading chunk 42 failed'),
    new Error('Failed to fetch dynamically imported module: https://x/chunk-AB.js'),
    new Error('error loading dynamically imported module'),
    new Error('Importing a module script failed.'),
    new Error('Loading CSS chunk 7 failed'),
  ];

  it.each(echecs)('reconnaît « %s »', e => {
    expect(estEchecDeChargement(e)).toBe(true);
  });

  it('ne confond pas avec une erreur applicative ordinaire', () => {
    expect(estEchecDeChargement(new Error('Cannot read properties of undefined'))).toBe(false);
    expect(estEchecDeChargement(new Error('Http failure response: 500'))).toBe(false);
  });

  it('ne lève pas sur null, undefined ou une chaîne', () => {
    expect(estEchecDeChargement(null)).toBe(false);
    expect(estEchecDeChargement(undefined)).toBe(false);
    expect(estEchecDeChargement('ChunkLoadError')).toBe(true);
  });
});

describe('ChunkReloadHandler', () => {
  let reload: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    reload = vi.fn();
    vi.stubGlobal('window', { location: { reload } });
    const magasin = new Map<string, string>();
    vi.stubGlobal('sessionStorage', {
      getItem: (k: string) => magasin.get(k) ?? null,
      setItem: (k: string, v: string) => void magasin.set(k, v),
    });
  });

  afterEach(() => vi.unstubAllGlobals());

  it('recharge la page sur un morceau manquant', () => {
    const h = make();
    h.handleError(new Error('ChunkLoadError: Loading chunk 3 failed'));
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it('NE RECHARGE PAS deux fois — sinon boucle infinie', () => {
    // Si le morceau manque pour une autre raison qu'un bundle périmé, recharger
    // à chaque fois enfermerait l'utilisateur dans une boucle.
    const h = make();
    h.handleError(new Error('ChunkLoadError'));
    h.handleError(new Error('ChunkLoadError'));
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it('remonte l’erreur au second passage plutôt que de la taire', () => {
    const h = make();
    h.handleError(new Error('ChunkLoadError'));
    h.handleError(new Error('ChunkLoadError'));
    expect(defaut(h)).toHaveBeenCalledTimes(1);
  });

  it('N’AVALE PAS les autres erreurs', () => {
    // Un attrape-tout priverait la console des erreurs réelles.
    const h = make();
    const boum = new Error('Cannot read properties of undefined');
    h.handleError(boum);
    expect(reload).not.toHaveBeenCalled();
    expect(defaut(h)).toHaveBeenCalledWith(boum);
  });

  it('ne recharge rien côté serveur (SSR)', () => {
    // `window` n'existe pas au prérendu : y toucher casserait le build.
    const h = make(false);
    h.handleError(new Error('ChunkLoadError'));
    expect(reload).not.toHaveBeenCalled();
  });

  it('ne recharge pas si le garde-fou ne peut pas être écrit', () => {
    // Sans garde-fou, le prochain chargement repartirait : boucle infinie.
    vi.stubGlobal('sessionStorage', {
      getItem: () => null,
      setItem: () => {
        throw new Error('QuotaExceededError');
      },
    });
    const h = make();
    h.handleError(new Error('ChunkLoadError'));
    expect(reload).not.toHaveBeenCalled();
    expect(defaut(h)).toHaveBeenCalledTimes(1);
  });

  it('ne recharge pas si le stockage est inaccessible en lecture', () => {
    vi.stubGlobal('sessionStorage', {
      getItem: () => {
        throw new Error('SecurityError');
      },
      setItem: () => undefined,
    });
    const h = make();
    h.handleError(new Error('ChunkLoadError'));
    expect(reload).not.toHaveBeenCalled();
  });

  it('est bien un ErrorHandler', () => {
    expect(typeof new ErrorHandler().handleError).toBe('function');
    expect(typeof make().handleError).toBe('function');
  });
});
