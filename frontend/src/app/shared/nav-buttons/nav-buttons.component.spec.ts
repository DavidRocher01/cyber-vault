import { describe, it, expect, vi } from 'vitest';
import { Injector, runInInjectionContext, signal } from '@angular/core';

import { NavButtonsComponent } from './nav-buttons.component';
import { NavHistoryService } from '../../core/services/nav-history.service';

/**
 * Ce composant est impose sur CHAQUE page par `CLAUDE.md`. Une regression ici
 * ne casse pas un ecran mais tous. Son propre service a deja son spec ; ce qui
 * est verifie ici, c'est le cablage : delegation au service et etat de survol.
 */
function creer(options: { arriere?: boolean; avant?: boolean } = {}) {
  const back = vi.fn();
  const forward = vi.fn();
  const faux = {
    back,
    forward,
    canGoBack: signal(options.arriere ?? false),
    canGoForward: signal(options.avant ?? false),
  };

  const injector = Injector.create({
    providers: [{ provide: NavHistoryService, useValue: faux }],
  });
  const composant = runInInjectionContext(injector, () => new NavButtonsComponent());
  return { composant, back, forward, faux };
}

describe('NavButtonsComponent', () => {
  it('expose les deux capacites de navigation du service', () => {
    const { composant } = creer({ arriere: true, avant: false });

    expect(composant.nav.canGoBack()).toBe(true);
    expect(composant.nav.canGoForward()).toBe(false);
  });

  it('delegue au service plutot que de manipuler l historique lui-meme', () => {
    const { composant, back, forward } = creer({ arriere: true, avant: true });

    composant.nav.back();
    composant.nav.forward();

    expect(back).toHaveBeenCalledOnce();
    expect(forward).toHaveBeenCalledOnce();
  });

  describe('etat de survol', () => {
    it('demarre sans aucun bouton survole', () => {
      const { composant } = creer();

      expect(composant.hoverBack).toBe(false);
      expect(composant.hoverFwd).toBe(false);
    });

    it('n allume que le bouton vise', () => {
      const { composant } = creer();

      composant.setHover('back', true);

      // Le piege du parametre unique : une inversion allumerait l'autre bouton,
      // et le survol se verrait sur la mauvaise fleche.
      expect(composant.hoverBack).toBe(true);
      expect(composant.hoverFwd).toBe(false);

      composant.setHover('fwd', true);
      composant.setHover('back', false);

      expect(composant.hoverBack).toBe(false);
      expect(composant.hoverFwd).toBe(true);
    });

    it('eteint le survol quand la souris quitte le bouton', () => {
      const { composant } = creer();

      composant.setHover('fwd', true);
      composant.setHover('fwd', false);

      // Sans cela, la teinte resterait allumee apres le depart du curseur.
      expect(composant.hoverFwd).toBe(false);
    });
  });
});
