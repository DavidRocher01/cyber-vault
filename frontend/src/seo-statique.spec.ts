import { existsSync, readFileSync } from 'node:fs';
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

/**
 * Blocs de routes de PREMIER NIVEAU, avec leur chemin.
 *
 * Le découpage sur une accolade indentée de deux espaces écarte les routes
 * imbriquées, et ce n'est pas un détail : la console d'administration porte les
 * mêmes segments que le site public (`blog`, `users`). Une première mesure les
 * confondait et attribuait à `/blog` le titre « Admin — Blog ».
 */
function blocsPublics(): { chemin: string; bloc: string }[] {
  const blocs: { chemin: string; bloc: string }[] = [];
  for (const bloc of ROUTES.split(/\n {2}\{/)) {
    const chemin = bloc.match(/path: '([^']*)'/);
    if (!chemin || !bloc.includes('loadComponent')) continue;
    if (chemin[1].includes(':') || bloc.includes('canActivate')) continue;
    blocs.push({ chemin: `/${chemin[1]}`, bloc });
  }
  return blocs;
}

/**
 * Description déclarée sur la route, si elle y est.
 *
 * LES DEUX GUILLEMETS SONT ACCEPTÉS, ET C'EST NÉCESSAIRE. Prettier écrit une
 * chaîne en guillemets simples, sauf si elle contient une apostrophe — auquel
 * cas il passe aux doubles pour éviter l'échappement. Il replie aussi les
 * longues sur la ligne suivante. Une première version ne lisait que les
 * doubles guillemets : cinq descriptions sur neuf devenaient invisibles après
 * un simple formatage. Un extracteur lié à un choix de mise en forme ne
 * mesure pas ce qu'il croit mesurer.
 */
function descriptionDeclaree(bloc: string): string | null {
  return bloc.match(/description:\s*(['"])((?:(?!\1).)*)\1/)?.[2] ?? null;
}

/** Le composant de cette route pose-t-il lui-même une description ?
 *  Quinze pages le font encore ainsi — c'est valable, seulement moins visible. */
function composantPoseUneDescription(bloc: string): boolean {
  const imp = bloc.match(/import\('([^']+)'\)/)?.[1];
  if (!imp) return false;
  const fichier = resolve(RACINE, 'src/app/features/cyberscan', `${imp.replace(/^\.\//, '')}.ts`);
  if (!existsSync(fichier)) return false;
  return readFileSync(fichier, 'utf-8').includes("name: 'description'");
}

describe('Chaque page annoncée aux moteurs porte son titre et sa description', () => {
  /**
   * POURQUOI CES TESTS. Mesuré le 2026-08-09 : NEUF des 23 pages du sitemap
   * n'avaient aucune meta description, dont `/nis2` — celle que le lot 1 venait
   * d'ouvrir à l'indexation. Sans description, Google fabrique lui-même
   * l'extrait affiché sous le lien : on laisse un moteur rédiger
   * l'argumentaire commercial à notre place.
   */
  const PAGES = () => blocsPublics().filter(b => urlsDuSitemap().includes(b.chemin));

  it('lit bien les routes — sinon tout le reste est vide de sens', () => {
    expect(PAGES().length, 'aucune page du sitemap retrouvée dans les routes').toBeGreaterThan(15);
  });

  it('toute page annoncée porte un titre', () => {
    const sans = PAGES()
      .filter(b => !/title: '[^']+'/.test(b.bloc))
      .map(b => b.chemin);
    expect(sans, `pages du sitemap sans titre : ${sans.join(', ')}`).toHaveLength(0);
  });

  it('toute page annoncée porte une description', () => {
    const sans = PAGES()
      .filter(b => !descriptionDeclaree(b.bloc) && !composantPoseUneDescription(b.bloc))
      .map(b => b.chemin);
    expect(sans, `pages du sitemap sans description : ${sans.join(', ')}`).toHaveLength(0);
  });

  it('les titres annoncés sont distincts', () => {
    // Deux pages au même titre se cannibalisent dans les résultats de recherche.
    const titres = PAGES().map(b => b.bloc.match(/title: '([^']+)'/)?.[1] ?? b.chemin);
    expect(new Set(titres).size, `titres en double parmi ${titres.length}`).toBe(titres.length);
  });

  it('les descriptions déclarées sont distinctes et de longueur utile', () => {
    // Au-delà d'environ 160 caractères, Google tronque ; en deçà de 70, il
    // considère souvent la description trop maigre et la remplace.
    const declarees = PAGES()
      .map(b => ({ chemin: b.chemin, texte: descriptionDeclaree(b.bloc) }))
      .filter((d): d is { chemin: string; texte: string } => d.texte !== null);

    expect(declarees.length, 'aucune description déclarée sur une route').toBeGreaterThan(0);

    const mauvaises = declarees.filter(d => d.texte.length < 70 || d.texte.length > 165);
    expect(
      mauvaises.map(d => `${d.chemin} (${d.texte.length})`),
      'descriptions hors des bornes utiles'
    ).toHaveLength(0);

    const textes = declarees.map(d => d.texte);
    expect(new Set(textes).size, 'descriptions en double').toBe(textes.length);
  });
});
