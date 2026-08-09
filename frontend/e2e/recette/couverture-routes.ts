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
 */

const FICHIER_ROUTES = resolve(__dirname, '../../src/app/features/cyberscan/cyberscan.routes.ts');

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
 * Sont écartées les routes sous `rssiGuard` ou `rssiClientGuard` : elles
 * redirigent le canari avant même que leur composant ne se charge, et les
 * couvrir demanderait de lui donner ces rôles en production. Les routes à
 * paramètre le sont aussi — sans donnée réelle derrière, on mesurerait un 404 et
 * non la santé de l'écran.
 */
export function ecransAtteignables(): string[] {
  const source = readFileSync(FICHIER_ROUTES, 'utf-8');
  const routes: string[] = [];

  // Chaque bloc de route commence par `  {` au premier niveau du tableau.
  for (const bloc of source.split(/\n {2}\{/)) {
    const chemin = bloc.match(/path: '([^']*)'/);
    if (!chemin || !bloc.includes('loadComponent')) continue;
    if (chemin[1].includes(':')) continue;

    const garde = bloc.match(/canActivate: \[([a-zA-Z, ]+)\]/);
    const nom = garde ? garde[1].trim() : '';
    if (nom && !nom.includes('authGuard')) continue;

    routes.push(`/${chemin[1]}`);
  }
  return routes;
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
