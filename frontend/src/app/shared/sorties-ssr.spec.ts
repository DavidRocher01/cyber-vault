import { describe, it, expect, beforeEach, afterEach } from 'vitest';

import { CyberLoaderComponent } from './cyber-loader/cyber-loader.component';
import { MatrixRainComponent } from './easter-eggs/matrix-rain.component';
import { GlobeComponent } from './globe/globe.component';

/**
 * CE QUE CES TESTS DEFENDENT : la SORTIE d'un composant anime doit etre gardee
 * comme son ENTREE.
 *
 * LE DEFAUT QU'ILS REPRODUISENT. Ces trois composants gardaient `ngOnInit`
 * derriere `isPlatformBrowser` mais PAS leur destruction, qui appelait
 * `cancelAnimationFrame` — une fonction qui n'existe pas cote serveur. La garde
 * etait posee a l'entree, pas a la sortie. Le premier prerendu reel a fait
 * echouer la construction entiere du site.
 *
 * POURQUOI CE FICHIER EXISTE ALORS QUE LE PRERENDU EST ETEINT. C'est
 * precisement le probleme : rien n'exerce ces sorties aujourd'hui. Le defaut a
 * survecu des mois parce que la documentation affirmait un prerendu qui
 * n'existait pas — la consigne etait suivie pour une capacite eteinte, donc
 * aucune violation ne se signalait. Ces tests rendent la garde verifiable SANS
 * rallumer le prerendu, et resteront justes quand il reviendra.
 *
 * ON SUPPRIME REELLEMENT `cancelAnimationFrame` plutot que de l'espionner :
 * c'est la vraie cause de l'echec en construction, pas une approximation.
 */

const RAF = 'cancelAnimationFrame' as const;

/** Instance minimale, sur le modele de `matrix-rain.component.spec.ts` : on
 *  n'a besoin que des champs que la destruction touche. */
function instance<T>(type: new (...args: never[]) => T, plateforme: string): T {
  const comp = Object.create(type.prototype) as T;
  Object.assign(comp as object, { platformId: plateforme, rafId: 1, logTimer: 1, autoClose: 1 });
  return comp;
}

const COMPOSANTS = [
  ['CyberLoaderComponent', CyberLoaderComponent],
  ['MatrixRainComponent', MatrixRainComponent],
  ['GlobeComponent', GlobeComponent],
] as const;

describe('Sortie des composants animes sous rendu serveur', () => {
  let sauvegarde: typeof globalThis.cancelAnimationFrame;

  beforeEach(() => {
    // Node n'a pas `cancelAnimationFrame` ; l'environnement de test, si. On
    // retablit donc les conditions du prerendu.
    sauvegarde = globalThis.cancelAnimationFrame;
    delete (globalThis as Record<string, unknown>)[RAF];
  });

  afterEach(() => {
    globalThis.cancelAnimationFrame = sauvegarde;
  });

  for (const [nom, type] of COMPOSANTS) {
    it(`${nom} se detruit sans erreur cote serveur`, () => {
      const comp = instance(type, 'server');

      expect(() => comp.ngOnDestroy()).not.toThrow();
    });

    // CE TEST PROUVE QUE LE PRECEDENT DISCRIMINE. Sans garde, la destruction
    // atteint `cancelAnimationFrame` et jette — c'est exactement ce qui faisait
    // echouer la construction. Si l'on retirait la garde, le test ci-dessus
    // tomberait ; celui-ci verifie qu'il tomberait pour LA BONNE RAISON, et non
    // parce que la destruction serait devenue inoffensive.
    it(`${nom} atteindrait bien cancelAnimationFrame sans la garde`, () => {
      const comp = instance(type, 'browser');

      expect(() => comp.ngOnDestroy()).toThrow(/cancelAnimationFrame/);
    });
  }
});
