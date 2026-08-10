import { RenderMode, ServerRoute } from '@angular/ssr';

/**
 * Comment chaque route est rendue à la construction du site.
 *
 * POURQUOI CE FICHIER EXISTE. Jusqu'au 2026-08-08, le prérendu n'était pas
 * branché : `angular.json` ne déclarait ni `server` ni `outputMode`, et
 * `@angular/platform-server` n'était même pas installé. Résultat mesuré en
 * production — les 43 pages servaient les mêmes 78 780 octets, le même `<title>`
 * et aucun `<h1>`. Un moteur de recherche ne voyait qu'une coquille vide, et les
 * robots sans JavaScript (LinkedIn, Slack) n'y voyaient jamais rien d'autre.
 *
 * Tout l'échafaudage existait pourtant : `main.server.ts`, `app.config.server.ts`
 * et l'entrée dans `tsconfig.app.json`. Seul le branchement manquait, ce qui
 * explique que `CLAUDE.md` ait longtemps affirmé un prérendu inexistant.
 *
 * LA REGLE : tout est prérendu, SAUF les routes à paramètre.
 *
 * Une route à paramètre ne peut pas être prérendue sans savoir quelles valeurs
 * ce paramètre prendra. Angular exige alors un `getPrerenderParams`, c'est-à-dire
 * la liste exhaustive des pages à produire. Or cette liste vit en base, et la
 * construction se fait sans backend : on la fabriquerait au doigt mouillé, et
 * elle se périmerait au premier article publié.
 *
 * Ces routes restent donc rendues dans le navigateur — exactement le
 * comportement d'aujourd'hui. Aucune régression : on ne perd rien de ce qui
 * existait, on gagne les 26 autres pages.
 */

/**
 * Routes rendues côté navigateur, chacune pour une raison qui tient.
 *
 * La plupart sont des espaces authentifiés, sans valeur pour un moteur de
 * recherche et déjà interdits par `robots.txt`. `blog/:slug` est la seule dont
 * l'absence coûte quelque chose — voir la note en fin de fichier.
 */
const A_PARAMETRE = [
  // Espaces authentifiés — aucun intérêt d'indexation, et déjà interdits.
  'scan/:id',
  'site/:id',
  'subdomains/:id',
  'darkweb-dossier/:id',
  'consultant/clients/:id',
  'consultant/clients/:clientId/nis2',
  'awareness/org/:id',
  'awareness/module/:enrollmentId',
  'phishing/campaigns/:id',
  'phishing/campaigns/:id/edit',

  // Pages atteintes par un lien porteur de jeton : elles n'existent que pour
  // leur destinataire, et n'ont aucun sens hors de ce contexte.
  'collab/accept/:token',
  'demo-result/:token',
  'devis/:token/accepter',
  'devis/:token/refuser',
  'r/:token',
  'verify-certificate/:publicId',

  // ARTICLES DE BLOG — LE SEUL CAS QUI COUTE QUELQUE CHOSE.
  //
  // Les prérendre demanderait la liste des slugs à la construction. Elle vit en
  // base, et le build n'a pas de backend. Deux voies possibles plus tard :
  // interroger l'API de production depuis `getPrerenderParams`, ou publier les
  // articles en fichiers. Aucune n'est urgente : les articles restent indexables,
  // Google exécutant le JavaScript, et le sitemap les annonce nommément.
  'blog/:slug',
] as const;

/**
 * ROUTES GARDÉES : elles ne PEUVENT PAS être prérendues.
 *
 * CE QUE ÇA A COÛTÉ, LE 2026-08-10. Prérendre une route derrière `canActivate`
 * exécute la garde À LA CONSTRUCTION, sans session. Elle refuse, et Angular fige
 * son refus dans un fichier de 324 octets :
 *
 *     <title>Redirecting</title>
 *     <meta http-equiv="refresh" content="0; url=/auth/login?returnUrl=%2Fdashboard">
 *
 * Servi tel quel, ce fichier éjecte vers la connexion TOUT visiteur ouvrant
 * `/dashboard` par URL directe ou par rafraîchissement — connecté ou non, et
 * avant même qu'Angular ne démarre. Douze écrans étaient dans ce cas en
 * production. La recette post-prod l'a vu ; c'est la deuxième fois en deux
 * jours qu'elle rattrape ce lot.
 *
 * Ces routes n'ont de toute façon aucune valeur d'indexation : `robots.txt` les
 * interdit déjà.
 *
 * LA LISTE EST CONFRONTÉE À SA SOURCE par `app.routes.server.spec.ts` : toute
 * route portant un `canActivate` doit s'y trouver. Une liste recopiée se périme
 * au premier écran ajouté — la leçon de la semaine, apprise quatre fois.
 */
const AUTHENTIFIEES = [
  'dashboard',
  'url-scanner',
  'code-scan',
  'profile',
  'factures',
  'consultant',
  'consultant/profile',
  'espace-client',
  'sensibilisation',
  'awareness-admin',
  'pca',
  'darkweb',
  'darkweb-dossier',
  'darkweb-dossier/new',
  'onboarding',
  'success',
  'phishing/campaigns',
  'phishing/new',

  // Redirections pures et espaces protégés par une garde posée ailleurs que
  // dans `cyberscan.routes.ts` : même conséquence, même traitement.
  'auth',
  'auth/master-password',
  'awareness',
  'vault',
] as const;

export const serverRoutes: ServerRoute[] = [
  ...A_PARAMETRE.map(path => ({ path, renderMode: RenderMode.Client }) as ServerRoute),
  ...AUTHENTIFIEES.map(path => ({ path, renderMode: RenderMode.Client }) as ServerRoute),
  // Tout le reste est produit en HTML complet à la construction.
  { path: '**', renderMode: RenderMode.Prerender },
];
