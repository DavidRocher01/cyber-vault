/**
 * Génère la CloudFront Function qui aiguille les URL vers le bon fichier.
 *
 * POURQUOI CE FICHIER EXISTE. Depuis le 2026-08-08, la construction produit un
 * fichier HTML complet par page — 61 routes prérendues. Sans changement côté
 * CDN, ils seraient téléversés puis **jamais servis** : la fonction en place
 * réécrivait vers `/index.html` TOUS les chemins sans extension, y compris ceux
 * qui ont désormais leur propre fichier.
 *
 * LA LISTE EST DÉRIVÉE DE LA CONSTRUCTION, pas écrite à la main. Angular émet
 * `prerendered-routes.json` : c'est la seule source qui ne peut pas mentir sur
 * ce qui a réellement été produit. Une liste recopiée se périmerait au premier
 * écran ajouté — la leçon du jour, déjà apprise deux fois.
 *
 * CE QUE LA FONCTION FAIT, ET DANS QUEL ORDRE :
 *
 *   1. ancien domaine → redirection 301 vers le nouveau (inchangé) ;
 *   2. `/api/*` → laissé intact (par prudence : ce comportement ne passe pas
 *      ici, mais le garder coûte une ligne) ;
 *   3. chemin avec extension → fichier réel, servi tel quel ;
 *   4. **route prérendue → son propre fichier** — c'est ce qui est nouveau ;
 *   5. tout le reste → `/index.html`, exactement comme avant.
 *
 * L'ÉTAPE 5 EST CE QUI REND LE CHANGEMENT SÛR. Une URL inconnue, une faute de
 * frappe, une route rendue côté navigateur : toutes gardent le comportement
 * d'aujourd'hui. On n'ajoute un aiguillage que pour des fichiers dont la
 * construction vient d'attester l'existence.
 */

/** Chemin du fichier servi pour une URI donnée, ou `null` si S3 la sert telle
 *  quelle. Extrait pour être testable sans CloudFront. */
export function cibler(uri: string, prerendues: readonly string[]): string | null {
  if (uri.indexOf('/api/') === 0) return null;

  // Un dernier segment contenant un point = un vrai fichier (js, css, png…).
  const dernier = uri.substring(uri.lastIndexOf('/') + 1);
  if (dernier.indexOf('.') !== -1) return null;

  // On normalise la barre oblique finale : `/nis2/` et `/nis2` désignent la
  // même page, et la construction n'en produit qu'un fichier.
  const chemin = uri.length > 1 && uri.endsWith('/') ? uri.slice(0, -1) : uri;

  if (chemin === '/') return '/index.html';
  if (prerendues.indexOf(chemin) !== -1) return chemin + '/index.html';

  // Route rendue dans le navigateur, ou URL inconnue : comportement d'avant.
  return '/index.html';
}

/** Source de la CloudFront Function, prête à être publiée. */
export function genererFonction(prerendues: readonly string[]): string {
  // `/` est traité à part dans la fonction : l'inclure dans la liste
  // produirait `//index.html`.
  const liste = prerendues.filter(r => r !== '/').sort();

  return `// GÉNÉRÉ — ne pas modifier à la main.
// Source : frontend/src/routage-cloudfront.ts, à partir de prerendered-routes.json.
// ${liste.length} routes prérendues au moment de la construction.
var PRERENDUES = ${JSON.stringify(liste)};

function handler(event) {
  var request = event.request;
  var host = request.headers.host ? request.headers.host.value : '';

  // 1) Ancien domaine -> nouveau domaine (301).
  if (host === 'cyberscanapp.com' || host === 'www.cyberscanapp.com') {
    var qs = request.querystring || {};
    var pairs = [];
    for (var k in qs) {
      if (qs[k].value !== undefined && qs[k].value !== '') {
        pairs.push(k + '=' + qs[k].value);
      } else {
        pairs.push(k);
      }
    }
    var query = pairs.length ? '?' + pairs.join('&') : '';
    return {
      statusCode: 301,
      statusDescription: 'Moved Permanently',
      headers: { location: { value: 'https://rochercybersecurite.com' + request.uri + query } }
    };
  }

  var uri = request.uri;

  // 2) L'API garde ses vrais codes. Ce comportement ne passe pas ici, mais on
  //    ne prend pas le risque.
  if (uri.indexOf('/api/') === 0) return request;

  // 3) Un chemin qui se termine par une extension = un fichier reel.
  var lastSlash = uri.lastIndexOf('/');
  if (uri.substring(lastSlash + 1).indexOf('.') !== -1) return request;

  var chemin = uri.length > 1 && uri.charAt(uri.length - 1) === '/'
    ? uri.substring(0, uri.length - 1)
    : uri;

  if (chemin === '/') {
    request.uri = '/index.html';
    return request;
  }

  // 4) Route prerendue -> son propre fichier, avec son titre et son contenu.
  for (var i = 0; i < PRERENDUES.length; i++) {
    if (PRERENDUES[i] === chemin) {
      request.uri = chemin + '/index.html';
      return request;
    }
  }

  // 5) Tout le reste -> index.html, comme avant ce changement.
  request.uri = '/index.html';
  return request;
}
`;
}
