/**
 * Écrit la CloudFront Function à partir de ce que la construction a produit.
 *
 * Usage :  node --experimental-strip-types scripts/generer-routage-cloudfront.ts
 *
 * Lit `dist/cyber-vault-frontend/prerendered-routes.json` — l'inventaire émis
 * par Angular, seule source qui ne peut pas mentir sur ce qui existe vraiment —
 * et écrit `dist/routage-cloudfront.js`.
 *
 * Node 24 exécute le TypeScript sans transpilation : la logique reste dans
 * `src/routage-cloudfront.ts`, testée par sa spec, et n'est dupliquée nulle
 * part. C'était la condition pour que ce script n'ajoute aucune dépendance.
 */

import { readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { genererFonction } from '../src/routage-cloudfront.ts';

const RACINE = resolve(import.meta.dirname, '..');
const INVENTAIRE = resolve(RACINE, 'dist/cyber-vault-frontend/prerendered-routes.json');
const SORTIE = resolve(RACINE, 'dist/routage-cloudfront.js');

const brut = JSON.parse(readFileSync(INVENTAIRE, 'utf-8')) as { routes?: Record<string, unknown> };
const routes = Object.keys(brut.routes ?? {});

// UN INVENTAIRE VIDE EST UNE ANOMALIE, PAS UN CAS LIMITE. Il signifierait que le
// prérendu s'est éteint sans que personne ne s'en aperçoive — exactement l'état
// dans lequel le projet est resté jusqu'au 2026-08-08. Publier alors une
// fonction sans aucune route ferait taire le symptôme.
if (routes.length < 20) {
  throw new Error(
    `Inventaire suspect : ${routes.length} route(s) prérendue(s). ` +
      "Le prérendu est-il toujours actif dans angular.json ?"
  );
}

const source = genererFonction(routes);

// La limite est de 10 Ko par fonction. Échouer ici, à la construction, vaut
// mieux qu'échouer à la publication — c'est-à-dire après la bascule.
const taille = new TextEncoder().encode(source).length;
if (taille > 9000) {
  throw new Error(`Fonction trop volumineuse : ${taille} octets (limite CloudFront 10 000).`);
}

writeFileSync(SORTIE, source, 'utf-8');
console.log(`routage-cloudfront.js écrit — ${routes.length} routes, ${taille} octets`);
