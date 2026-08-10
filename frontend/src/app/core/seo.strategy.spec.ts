import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Injector, runInInjectionContext } from '@angular/core';
import { Title, Meta } from '@angular/platform-browser';
import { RouterStateSnapshot } from '@angular/router';

import { SeoStrategy } from './seo.strategy';

/**
 * CE QUE CES TESTS DEFENDENT : la strategie pose la description declaree sur la
 * route, et NE TOUCHE A RIEN quand la route n'en declare pas.
 *
 * LE RISQUE EST LA. Quinze composants posent encore leur description dans
 * `ngOnInit`, qui s'execute AVANT cette strategie. Si elle ecrivait
 * inconditionnellement — ne serait-ce qu'une chaine vide ou la description par
 * defaut — elle EFFACERAIT ces quinze descriptions en passant. Le lot gagnerait
 * neuf pages et en perdrait quinze.
 */

/** Faux instantane de route : seuls `data` et `firstChild` sont lus ici. */
function noeud(description?: string, enfant?: unknown): unknown {
  return {
    data: description === undefined ? {} : { description },
    firstChild: enfant ?? null,
    children: [],
  };
}

function etat(racine: unknown): RouterStateSnapshot {
  return { root: racine } as RouterStateSnapshot;
}

describe('SeoStrategy', () => {
  let strategie: SeoStrategy;
  let poserMeta: ReturnType<typeof vi.fn>;
  let poserTitre: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    poserMeta = vi.fn();
    poserTitre = vi.fn();
    const injector = Injector.create({
      providers: [
        { provide: Title, useValue: { setTitle: poserTitre } },
        { provide: Meta, useValue: { updateTag: poserMeta } },
      ],
    });
    strategie = runInInjectionContext(injector, () => new SeoStrategy());
  });

  it('pose la description declaree par la route', () => {
    strategie.updateTitle(etat(noeud(undefined, noeud('Une description de page.'))));

    expect(poserMeta).toHaveBeenCalledWith({
      name: 'description',
      content: 'Une description de page.',
    });
  });

  it("NE TOUCHE PAS a la description quand la route n'en declare aucune", () => {
    // Le test qui protege les quinze pages dont le composant pose la sienne.
    strategie.updateTitle(etat(noeud(undefined, noeud())));

    expect(poserMeta).not.toHaveBeenCalled();
  });

  it('la description la plus profonde l’emporte sur celle du parent', () => {
    // Une route enfant decrit sa page mieux que le parent qui la contient.
    strategie.updateTitle(etat(noeud('Le parent.', noeud("L'enfant."))));

    expect(poserMeta).toHaveBeenCalledWith({ name: 'description', content: "L'enfant." });
    expect(poserMeta).toHaveBeenCalledTimes(1);
  });

  it('ignore une description vide ou faite d’espaces', () => {
    // Declarer `description: ''` est une erreur de saisie, pas une intention
    // d'effacer : on garde ce qui est en place plutot que de vider la balise.
    strategie.updateTitle(etat(noeud(undefined, noeud('   '))));

    expect(poserMeta).not.toHaveBeenCalled();
  });
});
