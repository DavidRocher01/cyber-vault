/**
 * Invariant : la landing est publique, ses liens doivent mener quelque part de
 * public.
 *
 * Trouvé le 2026-07-30 : deux CTA de l'offre de pointe n°2 pointaient vers des
 * routes protégées par authGuard. Un prospect qui cliquait « Découvrir le
 * module » ou « Voir les tarifs » atterrissait sur le formulaire de connexion —
 * y compris les consultants visés par le CTA « Devenir partenaire », qui vit
 * sur la page de tarifs.
 *
 * Ce test lit la source du template et croise chaque `routerLink` avec la
 * définition des routes. Il échouera si quelqu'un ajoute un lien vers une page
 * authentifiée, ou protège une page déjà liée depuis la landing.
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, it, expect } from 'vitest';

const templateLanding = readFileSync(resolve(__dirname, './landing.component.html'), 'utf-8');
const sourceRoutes = readFileSync(resolve(__dirname, '../cyberscan.routes.ts'), 'utf-8');

/** Chemins référencés par un routerLink statique dans la landing. */
function liensDeLaLanding(): string[] {
  const trouves = new Set<string>();
  for (const m of templateLanding.matchAll(/routerLink="\/([a-z0-9\-/]*)"/g)) {
    trouves.add(m[1]);
  }
  return [...trouves].filter(Boolean);
}

/** Chemins déclarés avec un garde d'authentification. */
function cheminsProteges(): Set<string> {
  const proteges = new Set<string>();
  // Chaque bloc de route va d'un `path:` au `path:` suivant.
  const blocs = sourceRoutes.split(/(?=\{\s*\n?\s*(?:\/\/[^\n]*\n\s*)*path:)/);
  for (const bloc of blocs) {
    const chemin = bloc.match(/path: '([^']*)'/)?.[1];
    if (chemin && /canActivate:\s*\[[^\]]*Guard/.test(bloc)) {
      proteges.add(chemin);
    }
  }
  return proteges;
}

/**
 * Violations PRÉEXISTANTES, constatées le 2026-07-30 en écrivant ce test.
 *
 * Le pied de page renvoie vers `/darkweb-dossier` (authGuard) et `/consultant`
 * (rssiGuard) sans condition de connexion : un visiteur qui clique tombe sur le
 * formulaire de login. Même défaut que celui corrigé pour la sensibilisation,
 * mais sur d'autres produits — laissé en l'état faute d'arbitrage produit
 * (faut-il une page vitrine publique, ou retirer le lien du pied de page ?).
 *
 * `/dashboard` et `/profile` sont légitimes : ils vivent dans `@if (isLoggedIn)`.
 * Le test ne sait pas lire cette condition, d'où leur présence ici.
 *
 * Toute NOUVELLE entrée dans cette liste doit être corrigée, pas ajoutée.
 */
const VIOLATIONS_CONNUES = ['dashboard', 'profile', 'darkweb-dossier', 'consultant'];

describe('Landing — aucun lien vers une page authentifiée', () => {
  it('trouve bien des liens à vérifier', () => {
    // Garde-fou du test lui-même : si les regex cassent, il ne doit pas passer
    // en silence sur une liste vide.
    expect(liensDeLaLanding().length).toBeGreaterThan(5);
    expect(cheminsProteges().size).toBeGreaterThan(5);
  });

  it('aucun NOUVEAU lien de la landing ne mène à une route protégée', () => {
    const proteges = cheminsProteges();
    const fautifs = liensDeLaLanding()
      .filter(l => proteges.has(l))
      .filter(l => !VIOLATIONS_CONNUES.includes(l));
    expect(fautifs).toEqual([]);
  });

  it('la liste des violations connues ne contient rien de périmé', () => {
    // Si une violation est corrigée, elle doit sortir de la liste : sinon on
    // garde une exception qui ne protège plus rien.
    const proteges = cheminsProteges();
    const liens = liensDeLaLanding();
    const perimees = VIOLATIONS_CONNUES.filter(v => !(proteges.has(v) && liens.includes(v)));
    expect(perimees).toEqual([]);
  });

  it('les deux destinations de l’offre sensibilisation sont publiques', () => {
    const proteges = cheminsProteges();
    expect(proteges.has('awareness-pricing')).toBe(false);
    expect(proteges.has('contact')).toBe(false);
  });

  it('/sensibilisation reste protégée — c’est l’application, pas une vitrine', () => {
    // Elle appelle /training/modules et /training/progress, tous deux
    // authentifiés. Le garde y est légitime ; c'est le lien qui était fautif.
    expect(cheminsProteges().has('sensibilisation')).toBe(true);
  });
});
