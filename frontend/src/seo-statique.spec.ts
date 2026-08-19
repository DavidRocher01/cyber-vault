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
const ROBOTS = readFileSync(resolve(RACINE, 'src/robots.txt'), 'utf-8');

/**
 * Le sitemap n'est PLUS un fichier statique : il est construit par le backend,
 * qui seul connaît les articles de blog — ils vivent en base, et publier depuis
 * l'administration ne pouvait donc pas mettre à jour un fichier du dépôt.
 *
 * Ce test lit désormais la liste des pages publiques là où elle est écrite, en
 * Python. Lire un fichier de l'autre côté est le motif déjà employé en sens
 * inverse par `backend/tests/test_coherence_front_back.py`.
 */
const SITEMAP = readFileSync(
  resolve(RACINE, '..', 'backend/app/services/sitemap_service.py'),
  'utf-8'
);

/**
 * LES ROUTES VIVENT DANS PLUSIEURS FICHIERS, PAS UN SEUL. Cette liste ne lisait
 * que `cyberscan.routes.ts`, en le prenant pour l'application : il l'est
 * presque — 107 des 123 fichiers de `features/` — mais les pages
 * d'authentification et l'entrée du portail apprenant sont montées ailleurs.
 * Elles échappaient donc à la vérification, et rien n'obligeait à décider de
 * leur sort. Même angle mort que la couverture de recette et que les modes de
 * rendu, corrigé le même jour (2026-08-18).
 *
 * `vault.routes.ts` n'est délibérément PAS lu : sa route est gardée au point de
 * montage, dans `app.routes.ts`, et non dans son propre fichier — la lire ici la
 * ferait passer pour publique.
 */
const SOURCES: ReadonlyArray<{ fichier: string; prefixe: string }> = [
  { fichier: 'src/app/app.routes.ts', prefixe: '' },
  { fichier: 'src/app/features/auth/auth.routes.ts', prefixe: '/auth' },
  { fichier: 'src/app/features/cyberscan/cyberscan.routes.ts', prefixe: '' },
];

/** Pages publiques : chargées à la demande, sans garde, sans paramètre. */
function pagesPubliques(): string[] {
  const pages: string[] = [];
  for (const { fichier, prefixe } of SOURCES) {
    const source = readFileSync(resolve(RACINE, fichier), 'utf-8');
    for (const bloc of source.split(/\n {2}\{/)) {
      const chemin = bloc.match(/path: '([^']*)'/);
      if (!chemin || !bloc.includes('loadComponent')) continue;
      const brut = chemin[1];
      if (brut.includes(':') || bloc.includes('canActivate')) continue;
      // `**` n'est pas une page : c'est le repli « introuvable ».
      if (brut === '**') continue;
      pages.push(brut === '' ? prefixe || '/' : `${prefixe}/${brut}`);
    }
  }
  return pages;
}

function urlsDuSitemap(): string[] {
  // Les tuples `("/chemin", "monthly", "0.8")` de PAGES_PUBLIQUES. Les articles
  // de blog n'y sont pas : ils viennent de la base, et aucun test du dépôt ne
  // peut donc les voir.
  return [...SITEMAP.matchAll(/^\s{4}\("(\/[^"]*)",/gm)].map(m => m[1]);
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

  // Pages publiques montées hors de `cyberscan.routes.ts`. Elles étaient
  // simplement invisibles à ce test jusqu'au 2026-08-18 : leur absence du
  // sitemap n'était pas une décision, c'était un angle mort.
  '/auth/login':
    'formulaire de connexion : aucune valeur de référencement, et déjà interdit par `Disallow: /auth/` dans robots.txt',
  '/auth/register':
    "formulaire d'inscription : même raison ; l'entrée commerciale est la vitrine, pas ce formulaire",
  '/auth/forgot-password': 'page technique de récupération de compte',
  '/auth/reset-password': "page technique, atteinte par un lien d'e-mail avec jeton",
  '/awareness/login':
    "entrée du portail apprenant, atteinte par un lien magique envoyé par e-mail : rien à y indexer, et l'annoncer exposerait le point d'entrée",
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
function blocsPublics(): { chemin: string; bloc: string; dossier: string }[] {
  const blocs: { chemin: string; bloc: string; dossier: string }[] = [];
  for (const { fichier, prefixe } of SOURCES) {
    const source = readFileSync(resolve(RACINE, fichier), 'utf-8');
    // Les imports paresseux d'un fichier de routes sont relatifs A CE FICHIER :
    // on garde donc son dossier pour les resoudre plus bas.
    const dossier = resolve(RACINE, fichier, '..');

    for (const bloc of source.split(/\n {2}\{/)) {
      const chemin = bloc.match(/path: '([^']*)'/);
      if (!chemin || !bloc.includes('loadComponent')) continue;
      const brut = chemin[1];
      if (brut.includes(':') || bloc.includes('canActivate') || brut === '**') continue;
      blocs.push({ chemin: brut === '' ? prefixe || '/' : `${prefixe}/${brut}`, bloc, dossier });
    }
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
function composantPoseUneDescription(bloc: string, dossier: string): boolean {
  const imp = bloc.match(/import\('([^']+)'\)/)?.[1];
  if (!imp) return false;
  // Le dossier vient du fichier de routes qui porte ce bloc : un chemin en dur
  // vers `features/cyberscan` ne resoudrait rien pour les autres arbres.
  const fichier = resolve(dossier, `${imp.replace(/^\.\//, '')}.ts`);
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
      .filter(b => !descriptionDeclaree(b.bloc) && !composantPoseUneDescription(b.bloc, b.dossier))
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
