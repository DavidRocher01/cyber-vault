import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { Injector, PLATFORM_ID, runInInjectionContext } from '@angular/core';

import { CookieBannerComponent } from './cookie-banner.component';

const CLE = 'cyberscan_cookie_consent';

function creer(plateforme: 'browser' | 'server' = 'browser') {
  const injector = Injector.create({
    providers: [{ provide: PLATFORM_ID, useValue: plateforme }],
  });
  // Le constructeur lit `localStorage` : il doit s'executer DANS le contexte
  // d'injection, sinon `inject(PLATFORM_ID)` echoue.
  return runInInjectionContext(injector, () => new CookieBannerComponent());
}

describe('CookieBannerComponent', () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => vi.restoreAllMocks());

  it("s'affiche quand aucun choix n'a encore ete fait", () => {
    expect(creer().visible()).toBe(true);
  });

  // Le point qui compte pour le RGPD : un consentement recueilli ne doit pas
  // etre redemande a chaque visite, sinon le choix de l'utilisateur ne veut
  // plus rien dire.
  it.each(['accepted', 'rejected'])('reste masque si le choix "%s" est deja enregistre', choix => {
    localStorage.setItem(CLE, choix);
    expect(creer().visible()).toBe(false);
  });

  it('accept() enregistre le consentement et referme le bandeau', () => {
    const c = creer();
    c.accept();

    expect(localStorage.getItem(CLE)).toBe('accepted');
    expect(c.visible()).toBe(false);
  });

  it('reject() enregistre le REFUS et referme le bandeau', () => {
    const c = creer();
    c.reject();

    // Un refus doit s'ecrire, pas seulement masquer : sans trace, le bandeau
    // reviendrait a la visite suivante et le refus serait sans effet.
    expect(localStorage.getItem(CLE)).toBe('rejected');
    expect(c.visible()).toBe(false);
  });

  it('accept() et reject() enregistrent des valeurs distinctes', () => {
    const a = creer();
    a.accept();
    const accepte = localStorage.getItem(CLE);

    localStorage.clear();
    const r = creer();
    r.reject();

    // Si les deux ecrivaient la meme valeur, on ne pourrait plus prouver ce que
    // l'utilisateur a choisi — ce qui est exactement ce qu'un controle demande.
    expect(accepte).not.toBe(localStorage.getItem(CLE));
  });

  describe('rendu serveur', () => {
    it('ne touche pas au stockage et laisse le bandeau masque', () => {
      // On rend `localStorage` explosif : si le composant y touche cote serveur,
      // le test echoue au lieu de passer par chance. Le prerendu casserait.
      const piege = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
        throw new Error('localStorage touche pendant le rendu serveur');
      });
      vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
        throw new Error('localStorage touche pendant le rendu serveur');
      });

      const c = creer('server');
      expect(c.visible()).toBe(false);

      // Les actions restent inoffensives : elles peuvent etre appelees par du
      // code d'hydratation avant que la plateforme ne soit celle du navigateur.
      expect(() => c.accept()).not.toThrow();
      expect(() => c.reject()).not.toThrow();
      expect(piege).not.toHaveBeenCalled();
    });
  });
});
