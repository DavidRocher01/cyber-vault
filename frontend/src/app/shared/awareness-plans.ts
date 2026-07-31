// Grille tarifaire de la sensibilisation NIS2 — SOURCE UNIQUE.
//
// Extraite de awareness-pricing.component.ts le 2026-07-30 : la landing recopiait
// le prix d'entrée à la main, ce qui avait produit un « 49 € » affiché pour 79 €
// réels. Tout affichage de prix passe désormais par ce fichier.

import { NB_MODULES } from './awareness-catalog.generated';

export interface AwarenessPlan {
  id: string;
  name: string;
  price: number;
  period: string;
  maxLearners: number | null;
  badge: string;
  featured: boolean;
  features: string[];
}

export const PLANS: AwarenessPlan[] = [
  {
    id: 'awareness-s',
    name: 'Formation S',
    price: 79,
    period: 'mois',
    maxLearners: 10,
    badge: '',
    featured: false,
    features: [
      "Jusqu'à 10 learners",
      `${NB_MODULES} modules NIS2 inclus`,
      'Quiz avec 3 tentatives',
      'Attestations PDF vérifiables',
      'Dashboard de complétion',
      'Magic-link sans mot de passe',
    ],
  },
  {
    id: 'awareness-m',
    name: 'Formation M',
    price: 199,
    period: 'mois',
    maxLearners: 30,
    badge: 'Populaire',
    featured: true,
    features: [
      "Jusqu'à 30 learners",
      'Tout Formation S +',
      'Import CSV en masse',
      'Gamification (XP, badges, classement)',
      'Rapport NIS2 Article 21 PDF',
      'Dashboard at-risk learners',
    ],
  },
  {
    id: 'awareness-l',
    name: 'Formation L',
    price: 449,
    period: 'mois',
    maxLearners: 75,
    badge: '',
    featured: false,
    features: [
      "Jusqu'à 75 learners",
      'Tout Formation M +',
      'Multi-organisations',
      'Rapport de conformité exportable',
      'Relances automatiques des inactifs',
      'Support prioritaire',
    ],
  },
  {
    id: 'awareness-xl',
    name: 'Formation XL',
    price: 899,
    period: 'mois',
    maxLearners: 200,
    badge: 'Entreprise',
    featured: false,
    features: [
      "Jusqu'à 200 learners",
      'Tout Formation L +',
      'Onboarding personnalisé',
      'Modules sur mesure (option)',
      'SLA 99,9 % garanti',
      'Facturation annuelle disponible',
    ],
  },
];

/** Palier d'entrée — utilisé par la landing pour annoncer « à partir de ». */
export const PLAN_ENTREE = PLANS[0];

/** Remise consentie aux consultants RSSI qui revendent la sensibilisation.
 *
 * Décision du 2026-07-30. Elle rémunère ce que le partenaire fait à notre place
 * — vente, mise en place, support de niveau 1 — et s'applique à partir de
 * 3 organisations clientes, pour qu'un acheteur isolé ne se déclare pas
 * partenaire.
 *
 * DÉRIVÉE du barème direct, jamais recopiée : même logique de taille des deux
 * côtés, ce qui évite qu'un gros compte passe par un consultant uniquement pour
 * changer de barème.
 */
export const REMISE_PARTENAIRE = 0.4;

/** Seuil d'organisations clientes à partir duquel le tarif partenaire s'applique. */
export const MIN_CLIENTS_PARTENAIRE = 3;

/** Prix partenaire d'un palier, arrondi à l'euro. */
export function prixPartenaire(plan: AwarenessPlan): number {
  return Math.round(plan.price * (1 - REMISE_PARTENAIRE));
}
