import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Les écrans de l'application, LUS DANS LE CODE plutôt que recopiés.
 *
 * POURQUOI CE FICHIER EXISTE. La recette navigateur listait ses pages à la main
 * et en couvrait 3 sur 69. Le lot NIS2 du 2026-08-07 a livré deux écrans entiers
 * — dont l'un s'est révélé cassé en production — sans que la recette n'en
 * vérifie aucun. Rien ne signalait l'absence : une liste écrite à la main ne
 * proteste jamais de ce qu'elle ne contient pas.
 *
 * En dérivant la liste du fichier de routes, l'oubli devient impossible : le
 * jour où quelqu'un ajoute un écran, la recette réclame sa couverture ou une
 * raison écrite de s'en passer.
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * ÉLARGI LE 2026-08-17. Ce fichier ne lisait qu'UN fichier de routes sur quatre,
 * `cyberscan.routes.ts`. Il laissait donc hors recette l'inscription, le mot de
 * passe oublié, sa réinitialisation et l'entrée du portail apprenant — des pages
 * PUBLIQUES dont le bundle peut casser exactement comme les écrans NIS2. Le
 * dispositif protégeait bien ce qu'il regardait, mais ne regardait qu'un quart
 * du site. Un filet dérivé du code n'a de valeur que s'il lit tout le code.
 */

const RACINE = resolve(__dirname, '../../src/app');

/**
 * Les fichiers de routes lus, et le préfixe sous lequel leurs chemins sont
 * montés dans `app.routes.ts`. Ajouter un `loadChildren` sans l'inscrire ici le
 * rendrait invisible — c'est le défaut que ce fichier corrige, autant ne pas le
 * reproduire un étage plus bas.
 */
const SOURCES: ReadonlyArray<{ fichier: string; prefixe: string }> = [
  { fichier: 'app.routes.ts', prefixe: '' },
  { fichier: 'features/auth/auth.routes.ts', prefixe: '/auth' },
  { fichier: 'features/cyberscan/cyberscan.routes.ts', prefixe: '' },
];

/**
 * Arbres de routes entiers écartés, avec leur raison — même exigence que pour
 * les écrans isolés dans `EXCLUES`.
 */
export const FICHIERS_ECARTES: Record<string, string> = {
  'features/vault/vault.routes.ts':
    "monté sous `cryptoGuard` : le canari se connecte sans jamais saisir de mot de passe maître, il serait renvoyé vers /auth/master-password avant que le composant ne se charge",
};

/**
 * La route attrape-tout `**` ne correspond à aucune URL réelle. On la visite
 * donc sous une adresse volontairement absente, ce qui vérifie deux choses d'un
 * coup : le bundle de la page « introuvable », et le repli du CDN qui doit
 * renvoyer `/index.html` pour une URL inconnue plutôt qu'un 404 sec.
 */
const CHEMIN_INEXISTANT = '/url-inexistante-pour-la-recette';

function lireUnFichier(fichier: string, prefixe: string): string[] {
  const source = readFileSync(resolve(RACINE, fichier), 'utf-8');
  const routes: string[] = [];

  // Chaque bloc de route commence par `  {` au premier niveau du tableau.
  for (const bloc of source.split(/\n {2}\{/)) {
    const chemin = bloc.match(/path: '([^']*)'/);
    if (!chemin || !bloc.includes('loadComponent')) continue;
    const brut = chemin[1];
    if (brut.includes(':')) continue;

    const garde = bloc.match(/canActivate: \[([a-zA-Z, ]+)\]/);
    const nom = garde ? garde[1].trim() : '';
    if (nom && !nom.includes('authGuard')) continue;

    if (brut === '**') {
      routes.push(CHEMIN_INEXISTANT);
      continue;
    }
    routes.push(brut === '' ? prefixe || '/' : `${prefixe}/${brut}`);
  }
  return routes;
}

/**
 * Écrans chargés à la demande, sans paramètre, qu'un compte canari connecté
 * peut atteindre tels quels.
 *
 * ON PREND LES ROUTES SANS GARDE **ET** CELLES SOUS `authGuard`. Ne retenir que
 * les secondes aurait manqué `/nis2` et `/iso27001`, qui n'ont aucune garde —
 * c'est-à-dire précisément les deux écrans à l'origine de ce fichier. Le critère
 * qui compte n'est pas « est-ce protégé » mais « le bundle de cet écran
 * peut-il casser ».
 *
 * Sont écartées les routes sous une autre garde (`rssiGuard`, `rssiClientGuard`,
 * `awarenessLearnerGuard`) : elles redirigent le canari avant même que leur
 * composant ne se charge, et les couvrir demanderait de lui donner ces rôles en
 * production. Les routes à paramètre le sont aussi — sans donnée réelle
 * derrière, on mesurerait un 404 et non la santé de l'écran.
 */
export function ecransAtteignables(): string[] {
  const vus = new Set<string>();
  for (const { fichier, prefixe } of SOURCES) {
    for (const route of lireUnFichier(fichier, prefixe)) vus.add(route);
  }
  return [...vus];
}

/**
 * Écrans volontairement NON visités, chacun avec sa raison.
 *
 * Toute entrée ici est une décision, pas un oubli — c'est la différence entre
 * une liste écrite à la main et celle-ci. Une exclusion qui ne correspondrait
 * plus à aucune route est signalée : la carte doit rester fidèle au territoire.
 */
export const EXCLUES: Record<string, string> = {
  '/': 'la vitrine a déjà son propre test, plus exigeant que la simple visite',
  '/success':
    'retour de paiement Stripe : sans session de checkout, la page redirige aussitôt et ne dit rien de son bundle',
  '/onboarding':
    'réservée aux comptes sans site ; le canari en possède, il serait renvoyé vers le tableau de bord',
  '/newsletter/confirm':
    'attend un jeton de confirmation en paramètre de requête ; sans lui, la page ne fait qu’afficher une erreur',
  '/newsletter/unsubscribe': 'même chose : sans jeton, rien de significatif à mesurer',
  '/r00t': 'console d’administration : une visite du canari y serait un accès indu',
  '/admin': 'console d’administration : réservée aux comptes `is_admin`',
  '/admin/newsletter': 'console d’administration',
  '/admin/ba61c5a60113/agenda': 'console d’administration, sur une URL volontairement obscure',
  '/reserver/annuler': 'attend une réservation existante en paramètre de requête',
};
