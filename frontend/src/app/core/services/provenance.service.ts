export interface Provenance {
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  page_atterrissage?: string;
}

/**
 * Lit la provenance dans l'URL COURANTE, au moment d'une conversion.
 *
 * Rien n'est stocké : ni cookie, ni `localStorage`, ni `sessionStorage`. Écrire
 * la campagne sur l'appareil relèverait de l'article 82 de la loi Informatique
 * et Libertés, donc du bandeau de consentement — précisément ce que la
 * conception écarte (cf. `docs/ANALYTICS.md`).
 *
 * Conséquence assumée : si quelqu'un arrive avec `?utm_source=linkedin` puis
 * navigue trois pages avant de convertir, la campagne est perdue. Le rattrapage
 * se fait côté serveur, par l'e-mail : les conversions anonymes d'un scan sont
 * reliées au compte créé ensuite avec la même adresse.
 *
 * Fonction libre plutôt que service injectable : `AuthService` s'injecte par
 * constructeur, et lui ajouter une dépendance casserait ses tests sans rien
 * apporter. L'appelant fournit `estNavigateur` — le site est prérendu, tout
 * accès à `window` doit rester gardé.
 */
export function lireProvenance(estNavigateur: boolean): Provenance {
  if (!estNavigateur) return {};

  const params = new URLSearchParams(window.location.search);
  const provenance: Provenance = {};

  for (const cle of ['utm_source', 'utm_medium', 'utm_campaign'] as const) {
    const valeur = params.get(cle);
    // Plafond volontairement large : le serveur normalise et tronque de toute
    // façon. Il ne s'agit ici que de ne pas poster un roman.
    if (valeur) provenance[cle] = valeur.slice(0, 128);
  }

  // Le chemin seul — le serveur retire la query string, mais autant ne pas
  // l'envoyer : elle ne contient rien qu'on ne transmette déjà à part.
  provenance.page_atterrissage = window.location.pathname;

  return provenance;
}
