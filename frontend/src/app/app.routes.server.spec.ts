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
 * recopiee se perime au premier ecran ajoute : c'est la meme lecon que pour le
 * sitemap, pour la couverture de recette et pour les routes prerendues du CDN —
 * quatre fois la meme semaine, ce qui suffit a en faire une regle.
 */

const ROUTES = readFileSync(resolve(__dirname, 'features/cyberscan/cyberscan.routes.ts'), 'utf-8');

/** Chemins de premier niveau portant une garde. Les routes a parametre sont
 *  deja rendues cote navigateur pour une autre raison. */
function gardees(): string[] {
  const trouvees: string[] = [];
  for (const bloc of ROUTES.split(/\n {2}\{/)) {
    const chemin = bloc.match(/path: '([^']*)'/);
    if (!chemin || !bloc.includes('canActivate') || chemin[1].includes(':')) continue;
    trouvees.push(chemin[1]);
  }
  return trouvees;
}

const cliente = new Set(
  serverRoutes.filter(r => r.renderMode === RenderMode.Client).map(r => r.path)
);

describe('Modes de rendu par route', () => {
  it('lit bien le fichier de routes — sinon tout le reste est vide de sens', () => {
    // Un parseur muet ferait passer le test suivant sans rien verifier.
    expect(gardees().length, 'aucune route gardee lue').toBeGreaterThan(10);
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
