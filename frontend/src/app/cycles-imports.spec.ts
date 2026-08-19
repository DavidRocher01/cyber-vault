import { readFileSync, existsSync } from 'node:fs';
import { resolve, dirname, relative } from 'node:path';

import { describe, it, expect } from 'vitest';
import fg from 'fast-glob';

/**
 * Garde-fou : aucun cycle d'import entre les modules de l'application.
 *
 * POURQUOI CE FICHIER EXISTE. Le backend a le sien depuis le 2026-08-18, écrit
 * après qu'un cycle entre `pdf_brand` et `pdf_covers` eut survécu des mois : un
 * module ré-exportait par compatibilité les fonctions qu'on lui avait retirées,
 * et ça ne tenait que par l'ordre d'entrée. Importer le module « par l'autre
 * bout » levait une erreur que personne n'avait rencontrée, faute d'avoir
 * essayé cet ordre-là.
 *
 * Le frontend n'avait pas d'équivalent. Il est propre — vérifié le 2026-08-19,
 * 175 modules et aucune boucle — mais il l'était par chance, pas parce que
 * quelque chose l'en empêchait. C'est cette asymétrie que ce fichier ferme.
 *
 * CE QUE COÛTE UN CYCLE EN TYPESCRIPT. Moins qu'en Python : le module qui boucle
 * reçoit `undefined` au lieu de la valeur attendue, au lieu de lever. Le défaut
 * se manifeste donc plus tard et plus loin — un service injecté qui vaut
 * `undefined`, une constante vide, une classe non définie à l'extension. C'est
 * pire à diagnostiquer, pas mieux.
 *
 * ON LIT LE GRAPHE, ON N'EXÉCUTE RIEN. Un cycle qui « fonctionne » grâce à
 * l'ordre de chargement reste un cycle, et c'était précisément le cas côté
 * backend.
 */

const RACINE = resolve(__dirname);

/** Les imports et ré-exports RELATIFS : `from './x'`, `from '../y/z'`. */
const IMPORT_RELATIF = /(?:import|export)[^'"]*from\s+['"](\.[^'"]+)['"]/g;

/**
 * TOUT CHEMIN PASSE PAR ICI, ET CE N'EST PAS DU CONFORT.
 *
 * Sous Windows, `fast-glob` rend des chemins en barres obliques
 * (`C:/Users/…/x.ts`) et `path.resolve` des antislashs (`C:\Users\…\x.ts`).
 * Les deux désignent le même fichier et ne sont pas la même chaîne. Sans cette
 * normalisation, les arêtes du graphe pointaient vers des clés absentes de la
 * map : le parcours entrait dans un nœud inconnu, sans voisins, et ressortait —
 * 355 arêtes, aucune traversable, zéro cycle trouvé quoi qu'il arrive.
 *
 * Ce défaut a survécu au premier jet de ce fichier, et n'a été trouvé qu'en
 * fabriquant un cycle exprès. C'est exactement ce que ce genre de test doit
 * subir avant d'être cru.
 */
const normaliser = (chemin: string): string => resolve(chemin);

function modules(): string[] {
  return fg.sync(['**/*.ts', '!**/*.spec.ts'], { cwd: RACINE, absolute: true }).map(normaliser);
}

/** Résout un chemin d'import vers le fichier réel, ou null s'il sort du champ. */
function resoudre(depuis: string, cible: string): string | null {
  const base = resolve(dirname(depuis), cible);
  for (const candidat of [`${base}.ts`, resolve(base, 'index.ts')]) {
    if (existsSync(candidat)) return normaliser(candidat);
  }
  return null;
}

function graphe(): Map<string, Set<string>> {
  const aretes = new Map<string, Set<string>>();

  for (const fichier of modules()) {
    const source = readFileSync(fichier, 'utf-8');
    const voisins = new Set<string>();

    for (const [, cible] of source.matchAll(IMPORT_RELATIF)) {
      const resolu = resoudre(fichier, cible);
      if (resolu && resolu !== fichier) voisins.add(resolu);
    }
    aretes.set(fichier, voisins);
  }
  return aretes;
}

/** Parcours en profondeur ; un arc vers un nœud de la pile ferme un cycle. */
function cycles(aretes: Map<string, Set<string>>): string[][] {
  const EN_COURS = 1;
  const etat = new Map<string, number>();
  const trouves: string[][] = [];

  function visiter(noeud: string, pile: string[]): void {
    etat.set(noeud, EN_COURS);
    pile.push(noeud);

    for (const voisin of [...(aretes.get(noeud) ?? [])].sort()) {
      if (!etat.has(voisin)) {
        visiter(voisin, pile);
      } else if (etat.get(voisin) === EN_COURS) {
        trouves.push([...pile.slice(pile.indexOf(voisin)), voisin]);
      }
    }
    pile.pop();
    etat.set(noeud, 2);
  }

  for (const noeud of [...aretes.keys()].sort()) {
    if (!etat.has(noeud)) visiter(noeud, []);
  }
  return trouves;
}

describe('Cycles d’import', () => {
  it('le graphe est bien construit — sinon le test suivant est vide de sens', () => {
    // Un extracteur cassé ne verrait aucune arête, et la recherche de cycles
    // passerait triomphalement sur un graphe vide.
    const aretes = graphe();
    const total = [...aretes.values()].reduce((n, v) => n + v.size, 0);

    expect(aretes.size, 'aucun module lu').toBeGreaterThan(100);
    expect(total, 'aucun import relatif détecté').toBeGreaterThan(50);
  });

  it('les arêtes mènent à des modules connus — sans quoi rien n’est parcouru', () => {
    // COMPTER LES ARÊTES NE SUFFIT PAS. Le premier jet de ce fichier en trouvait
    // 355, toutes inexploitables : elles portaient des antislashs quand les clés
    // portaient des barres obliques. Le test ci-dessus passait, la recherche de
    // cycles ne pouvait structurellement rien trouver, et un cycle introduit
    // exprès n'était pas détecté. Une arête qui ne mène nulle part est pire
    // qu'une arête absente : elle donne l'illusion d'un graphe.
    const aretes = graphe();
    const orphelines = [...new Set([...aretes.values()].flatMap(v => [...v]))]
      // Une cible HORS de `app/` est normale : `src/environments/environment.ts`
      // est un fichier de constantes de build, sans import, donc incapable de
      // participer a un cycle. Ce qui doit alerter, c'est une cible DANS `app/`
      // absente de la carte — signe que les chemins ne se correspondent pas.
      .filter(cible => cible.startsWith(RACINE) && !aretes.has(cible))
      .map(cible => relative(RACINE, cible));

    expect(orphelines, 'arêtes vers un module de app/ absent de la carte').toEqual([]);
  });

  it('AUCUN cycle entre les modules de l’application', () => {
    const trouves = cycles(graphe());

    // Deux parcours peuvent décrire la même boucle : on dédoublonne par ensemble.
    const uniques = new Map(
      trouves.map(c => [[...c].sort().join('|'), c.map(f => relative(RACINE, f))])
    );

    expect(
      [...uniques.values()],
      `cycles détectés :\n  ${[...uniques.values()].map(c => c.join(' -> ')).join('\n  ')}`
    ).toEqual([]);
  });
});
