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

import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { genererFonction } from '../src/routage-cloudfront.ts';

const RACINE = resolve(import.meta.dirname, '..');
const INVENTAIRE = resolve(RACINE, 'dist/cyber-vault-frontend/prerendered-routes.json');
const NAVIGATEUR = resolve(RACINE, 'dist/cyber-vault-frontend/browser');
const SORTIE = resolve(RACINE, 'dist/routage-cloudfront.js');

const brut = JSON.parse(readFileSync(INVENTAIRE, 'utf-8')) as { routes?: Record<string, unknown> };
const annoncees = Object.keys(brut.routes ?? {});

/**
 * UNE PAGE QUI REDIRIGE N'EST PAS UNE PAGE.
 *
 * Prérendre une route derrière `canActivate` exécute la garde à la
 * construction, sans session : elle refuse, et Angular fige son refus dans un
 * fichier de 324 octets porteur d'un `<meta http-equiv="refresh">`. Servi tel
 * quel, il éjecte vers la connexion tout visiteur ouvrant `/dashboard` par URL
 * directe — connecté ou non, avant même qu'Angular ne démarre. C'est ce qui est
 * arrivé en production le 2026-08-10, sur douze écrans.
 *
 * `app.routes.server.ts` empêche désormais ces fichiers d'être produits. CE
 * FILTRE EST LA SECONDE COUCHE, et la seule qui ne puisse pas se périmer : il
 * lit ce que la construction a RÉELLEMENT écrit, pas une liste tenue à la main.
 */
function estUneRedirection(route: string): boolean {
  const fichier =
    route === '/' ? resolve(NAVIGATEUR, 'index.html') : resolve(NAVIGATEUR, `.${route}/index.html`);
  if (!existsSync(fichier)) return true;
  return readFileSync(fichier, 'utf-8').includes('http-equiv="refresh"');
}

const routes = annoncees.filter(r => !estUneRedirection(r));
const ecartees = annoncees.filter(r => estUneRedirection(r));

// On le DIT plutôt que de l'écarter en silence : une redirection prérendue
// signale une route gardée oubliée dans `app.routes.server.ts`.
if (ecartees.length) {
  console.warn(
    `${ecartees.length} route(s) écartée(s) — page de redirection, pas de contenu :\n  ` +
      ecartees.join('\n  ') +
      '\n  → à déclarer en RenderMode.Client dans app.routes.server.ts.'
  );
}

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
