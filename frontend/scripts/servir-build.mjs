/**
 * Sert le build de PRODUCTION comme le fait le CDN, pour que l'E2E puisse
 * tester ce qu'on livre reellement.
 *
 * POURQUOI CE FICHIER EXISTE. La suite E2E tourne contre `ng serve`, donc
 * contre la configuration `development`. Le 2026-08-09, le prerendu n'etait
 * declare que dans `production` : AUCUN test ne pouvait voir la regression de
 * connexion qu'il introduisait. Les 84 e2e etaient verts, les 3201 unitaires
 * aussi, et c'est la recette post-prod qui l'a attrapee — une fois en
 * production. Elle est le dernier filet, pas le premier.
 *
 * LA REGLE D'AIGUILLAGE EST FONDEE SUR LE DISQUE, pas sur une liste. Si le
 * build a produit `<chemin>/index.html`, on le sert ; sinon on retombe sur
 * `/index.html`. C'est exactement l'intention de la CloudFront Function, mais
 * exprimee sans configuration : le harnais reste juste que le prerendu soit
 * allume ou eteint, donc il ne se perimera pas au prochain aller-retour.
 *
 * Aucune dependance : `http` et `fs` suffisent. Un serveur statique de plus
 * dans le lock serait une surface a maintenir pour trois regles.
 */
import { createServer } from 'node:http';
import { existsSync, readFileSync, statSync } from 'node:fs';
import { join, extname, normalize } from 'node:path';

const RACINE = process.argv[2] ?? 'dist/cyber-vault-frontend/browser';
const PORT = Number(process.argv[3] ?? 4300);

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.webp': 'image/webp',
  '.woff2': 'font/woff2',
  '.txt': 'text/plain; charset=utf-8',
  '.xml': 'application/xml; charset=utf-8',
};

/** Fichier a servir pour une URI, ou `null` si l'URI ne doit rien recevoir. */
export function cibler(uri, existe) {
  // L'API n'est pas servie ici : un test qui en a besoin l'intercepte
  // lui-meme. La faire echouer franchement vaut mieux que de la laisser
  // pendre jusqu'au timeout.
  if (uri.startsWith('/api/')) return null;

  const dernier = uri.slice(uri.lastIndexOf('/') + 1);
  if (dernier.includes('.')) return uri;

  const chemin = uri.length > 1 && uri.endsWith('/') ? uri.slice(0, -1) : uri;
  if (chemin === '/') return '/index.html';

  // Le build a produit sa propre page ? On la sert, comme le CDN.
  if (existe(`${chemin}/index.html`)) return `${chemin}/index.html`;

  // Sinon : route rendue dans le navigateur, ou URL inconnue.
  return '/index.html';
}

if (!existsSync(join(RACINE, 'index.html'))) {
  console.error(`Aucun build servable dans ${RACINE} — lancer \`npm run build\` d'abord.`);
  process.exit(1);
}

const existe = rel => {
  // `normalize` neutralise les `..` : on ne sert jamais hors de la racine.
  const abs = join(RACINE, normalize(rel).replace(/^(\.\.[/\\])+/, ''));
  return existsSync(abs) && statSync(abs).isFile();
};

createServer((req, res) => {
  const uri = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
  const cible = cibler(uri, existe);

  if (cible === null) {
    res.writeHead(503, { 'content-type': 'text/plain' });
    res.end("Pas de backend derriere ce serveur : l'intercepter dans le test.");
    return;
  }
  if (!existe(cible)) {
    res.writeHead(404, { 'content-type': 'text/plain' });
    res.end('Introuvable');
    return;
  }

  const corps = readFileSync(join(RACINE, cible));
  res.writeHead(200, {
    'content-type': TYPES[extname(cible)] ?? 'application/octet-stream',
    'cache-control': 'no-store',
  });
  res.end(corps);
}).listen(PORT, () => console.log(`Build servi sur http://localhost:${PORT} depuis ${RACINE}`));
