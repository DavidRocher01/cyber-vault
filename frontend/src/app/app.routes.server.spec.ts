import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, it, expect } from 'vitest';
import { RenderMode } from '@angular/ssr';

import { serverRoutes } from './app.routes.server';

/**
 * CE QUE CE TEST DEFEND : aucune route gardee ne doit etre prerendue.
 *
 * CE QUE ÇA A COÛTÉ, LE 2026-08-10. Prerendre une route derriere `canActivate`
 * execute la garde A LA CONSTRUCTION, sans session. Elle refuse, et Angular fige
 * son refus dans un fichier de 324 octets :
 *
 *     <title>Redirecting</title>
 *     <meta http-equiv="refresh" content="0; url=/auth/login?returnUrl=%2Fdashboard">
 *
 * Servi tel quel, ce fichier ejecte vers la connexion TOUT visiteur ouvrant
 * `/dashboard` par URL directe ou par rafraichissement — connecte ou non, et
 * avant meme qu'Angular ne demarre. Douze ecrans etaient dans ce cas en
 * production.
 *
 * LA LISTE EST CONFRONTEE A SA SOURCE, elle n'est pas relue a l'oeil. Une liste
 * recopiee se perime au premier ecran ajoute.
 *
 * ...ET LA SOURCE, C'EST QUATRE FICHIERS, PAS UN. Ce test n'en lisait qu'un —
 * `cyberscan.routes.ts` — en le prenant pour l'application entiere. Il l'est
 * presque : 107 des 123 fichiers de `features/`. Mais `/vault` et `/awareness`
 * sont gardes et montes ailleurs, dans `app.routes.ts` ; ils echappaient donc a
 * la verification. Leur mode de rendu est correct aujourd'hui, mais il l'est A
 * LA MAIN : rien n'exigeait qu'il le reste.
 *
 * C'est le meme angle mort que la couverture de recette, corrige le meme jour
 * (2026-08-18) et pour la meme raison : un dossier nomme comme une
 * fonctionnalite alors qu'il porte l'application trompe qui ecrit le garde-fou.
 */

const RACINE = __dirname;

/**
 * Les fichiers de routes lus, et le prefixe sous lequel `app.routes.ts` les
 * monte. Les chemins de `app.routes.server.ts` s'ecrivent sans barre oblique
 * initiale : `auth/master-password`, pas `/auth/master-password`.
 */
const SOURCES: ReadonlyArray<{ fichier: string; prefixe: string }> = [
  { fichier: 'app.routes.ts', prefixe: '' },
  { fichier: 'features/auth/auth.routes.ts', prefixe: 'auth' },
  { fichier: 'features/cyberscan/cyberscan.routes.ts', prefixe: '' },
  { fichier: 'features/vault/vault.routes.ts', prefixe: 'vault' },
];

/**
 * Chemins de premier niveau portant une garde. Les routes a parametre sont
 * deja rendues cote navigateur pour une autre raison.
 */
function gardees(): string[] {
  const trouvees: string[] = [];

  for (const { fichier, prefixe } of SOURCES) {
    const source = readFileSync(resolve(RACINE, fichier), 'utf-8');

    // Chaque bloc de route commence par `  {` au premier niveau du tableau.
    for (const bloc of source.split(/\n {2}\{/)) {
      const chemin = bloc.match(/path: '([^']*)'/);
      if (!chemin || !bloc.includes('canActivate') || chemin[1].includes(':')) continue;

      const brut = chemin[1];
      trouvees.push(brut === '' ? prefixe : prefixe ? `${prefixe}/${brut}` : brut);
    }
  }
  return trouvees;
}

const cliente = new Set(
  serverRoutes.filter(r => r.renderMode === RenderMode.Client).map(r => r.path)
);

describe('Modes de rendu par route', () => {
  it('lit bien les fichiers de routes — sinon tout le reste est vide de sens', () => {
    // Un parseur muet ferait passer le test suivant sans rien verifier.
    expect(gardees().length, 'aucune route gardee lue').toBeGreaterThan(10);
  });

  it('lit les arbres montes hors de cyberscan — l’angle mort d’origine', () => {
    // Sans cette assertion, quelqu'un pourrait reduire SOURCES au seul fichier
    // cyberscan sans rien casser d'apparent, et le trou se rouvrirait en
    // silence. On exige donc la presence des deux arbres qui manquaient.
    const lues = gardees();

    expect(lues, 'l’arbre /vault n’est plus lu').toContain('vault');
    expect(lues, 'l’arbre /awareness n’est plus lu').toContain('awareness');
  });

  it('AUCUNE route gardee n’est prerendue', () => {
    const oubliees = gardees().filter(p => !cliente.has(p));

    expect(
      oubliees,
      `routes gardees encore prerendues (elles produiraient une page de redirection) : ${oubliees.join(', ')}`
    ).toHaveLength(0);
  });

  it('le reste du site est bien prerendu', () => {
    // La garde inverse : si quelqu'un basculait tout en Client pour « regler »
    // un probleme, on perdrait le prerendu sans que rien ne le signale.
    const parDefaut = serverRoutes.find(r => r.path === '**');

    expect(parDefaut?.renderMode).toBe(RenderMode.Prerender);
  });
});
