import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, it, expect } from 'vitest';

/**
 * `robots.txt` et `sitemap.xml` doivent rester d'accord avec l'application.
 *
 * POURQUOI CE FICHIER EXISTE. Les deux sont écrits à la main, et l'expérience du
 * 2026-08-08 a montré ce que ça produit :
 *
 *   - `robots.txt` interdisait `/nis2` et `/iso27001`, deux outils publics sans
 *     authentification — c'est-à-dire les pages les plus susceptibles de se
 *     positionner sur « conformité NIS2 » ;
 *   - le sitemap n'annonçait que 11 URL sur les 30 pages publiques, taisant
 *     l'essentiel des pages commerciales.
 *
 * Personne n'avait rien signalé, parce qu'un fichier statique ne proteste jamais
 * de ce qu'il ne contient pas. Ces tests sont le filet : ils échouent le jour où
 * une page publique naît sans être annoncée, ou disparaît sans être retirée.
 *
 * MÊME LEÇON QUE POUR LA RECETTE, et posée le même jour : une liste écrite à la
 * main se périme en silence. La seule parade est de la confronter à sa source.
 */

const RACINE = resolve(__dirname, '..');
const ROUTES = readFileSync(
  resolve(RACINE, 'src/app/features/cyberscan/cyberscan.routes.ts'),
  'utf-8'
);
const ROBOTS = readFileSync(resolve(RACINE, 'src/robots.txt'), 'utf-8');
const SITEMAP = readFileSync(resolve(RACINE, 'src/sitemap.xml'), 'utf-8');

/** Pages publiques : chargées à la demande, sans garde, sans paramètre. */
function pagesPubliques(): string[] {
  const pages: string[] = [];
  for (const bloc of ROUTES.split(/\n {2}\{/)) {
    const chemin = bloc.match(/path: '([^']*)'/);
    if (!chemin || !bloc.includes('loadComponent')) continue;
    if (chemin[1].includes(':') || bloc.includes('canActivate')) continue;
    pages.push(`/${chemin[1]}`);
  }
  return pages;
}

function urlsDuSitemap(): string[] {
  return [...SITEMAP.matchAll(/<loc>https:\/\/rochercybersecurite\.com([^<]*)<\/loc>/g)].map(
    m => m[1] || '/'
  );
}

function interdites(): string[] {
  return ROBOTS.split('\n')
    .filter(l => l.trim().startsWith('Disallow:'))
    .map(l => l.split(':')[1].trim())
    .filter(Boolean);
}

/**
 * Pages publiques volontairement hors sitemap, chacune avec sa raison.
 *
 * Toute entrée est une décision, pas un oubli. Une exclusion qui ne
 * correspondrait plus à aucune page est signalée : la carte doit rester fidèle
 * au territoire.
 */
const HORS_SITEMAP: Record<string, string> = {
  '/r00t': "console d'administration : son URL ne doit apparaître nulle part",
  '/admin': "console d'administration",
  '/admin/newsletter': "console d'administration",
  '/admin/ba61c5a60113/agenda': "console d'administration, sur une URL volontairement obscure",
  '/newsletter/confirm': "page technique, atteinte par un lien d'e-mail avec jeton",
  '/newsletter/unsubscribe': "page technique, atteinte par un lien d'e-mail avec jeton",
  '/reserver/annuler': 'page technique, atteinte depuis une confirmation de réservation',
};

describe('robots.txt et sitemap.xml suivent l’application', () => {
  it('lit bien les routes — sinon tout le reste est vide de sens', () => {
    // Un parseur muet ferait passer tous les tests suivants sans rien vérifier.
    expect(pagesPubliques().length, 'aucune page publique lue').toBeGreaterThan(15);
    expect(urlsDuSitemap().length, 'sitemap vide ou illisible').toBeGreaterThan(15);
  });

  it('AUCUNE page annoncée au sitemap n’est interdite par robots.txt', () => {
    // LA CONTRADICTION LA PLUS COÛTEUSE : annoncer une page aux moteurs tout en
    // leur interdisant de la lire. C'est ce qui arrivait à `/nis2`.
    const sitemap = urlsDuSitemap();
    const conflits = sitemap.filter(u =>
      interdites().some(d => u === d || (d.endsWith('/') && u.startsWith(d)))
    );
    expect(conflits, `annoncées puis interdites : ${conflits.join(', ')}`).toHaveLength(0);
  });

  it('toute page publique est annoncée, ou exclue avec sa raison', () => {
    const sitemap = urlsDuSitemap();
    const oubliees = pagesPubliques().filter(p => !sitemap.includes(p) && !(p in HORS_SITEMAP));
    expect(oubliees, `pages publiques absentes du sitemap : ${oubliees.join(', ')}`).toHaveLength(
      0
    );
  });

  it('le sitemap n’annonce pas de page qui n’existe plus', () => {
    // Une URL morte au sitemap fait perdre du budget d'exploration et signale un
    // site mal tenu.
    const pages = pagesPubliques();
    const fantomes = urlsDuSitemap().filter(
      u => u !== '/' && !u.startsWith('/blog/') && !pages.includes(u)
    );
    expect(
      fantomes,
      `URL du sitemap sans route correspondante : ${fantomes.join(', ')}`
    ).toHaveLength(0);
  });

  it('les exclusions déclarées correspondent encore à des pages réelles', () => {
    const pages = pagesPubliques();
    const orphelines = Object.keys(HORS_SITEMAP).filter(p => !pages.includes(p));
    expect(
      orphelines,
      `exclusions sans page correspondante : ${orphelines.join(', ')}`
    ).toHaveLength(0);
  });

  it('les espaces authentifiés restent interdits', () => {
    // Le lot du 2026-08-08 a ouvert `/nis2` et `/iso27001` ; il ne doit pas avoir
    // ouvert autre chose au passage.
    for (const prive of ['/dashboard', '/vault', '/profile', '/admin/', '/auth/']) {
      expect(interdites(), `${prive} n'est plus interdit`).toContain(prive);
    }
  });
});
