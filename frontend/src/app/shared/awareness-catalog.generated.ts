// ⚠️ FICHIER GÉNÉRÉ — NE PAS ÉDITER À LA MAIN.
//
// Source de vérité : content/fr/ (modules et parcours).
// Régénérer : python backend/scripts/generate_awareness_catalog.py
// La CI vérifie que ce fichier est à jour (--check) : un module ajouté sans
// régénération fait échouer le build, ce qui est le but.
//
// Ce fichier existe parce que ces chiffres étaient recopiés à la main dans huit
// emplacements et avaient dérivé : 17 modules annoncés au lieu de 28, 72 minutes
// au lieu de 143.

export interface ParcoursAwareness {
  readonly slug: string;
  readonly titre: string;
  readonly public: string;
  readonly nbModules: number;
  readonly dureeMinutes: number;
  readonly scoreRequis: number;
}

/** Nombre de modules actifs dans le catalogue. */
export const NB_MODULES = 28;

/** Durée cumulée de tous les modules actifs, en minutes. */
export const DUREE_TOTALE_MINUTES = 144;

/** Parcours proposés, du plus complet au plus court. */
export const PARCOURS: readonly ParcoursAwareness[] = [
  {
    slug: 'nis2-essentiel',
    titre: 'NIS2 Essentiel — Sensibilisation Cyber Complète',
    public: 'Tout le personnel',
    nbModules: 28,
    dureeMinutes: 144,
    scoreRequis: 60,
  },
  {
    slug: 'nis2-technique',
    titre: 'NIS2 Équipes Techniques — Sécurité avancée',
    public: 'Équipes IT, développeurs, DevOps',
    nbModules: 8,
    dureeMinutes: 40,
    scoreRequis: 70,
  },
  {
    slug: 'nis2-direction',
    titre: 'NIS2 Direction & RSSI — Gouvernance et responsabilités',
    public: 'Dirigeants, managers, RSSI',
    nbModules: 6,
    dureeMinutes: 31,
    scoreRequis: 70,
  },
  {
    slug: 'nis2-onboarding',
    titre: 'NIS2 Onboarding — Les fondamentaux en 20 minutes',
    public: 'Nouveaux arrivants',
    nbModules: 4,
    dureeMinutes: 20,
    scoreRequis: 60,
  },
] as const;

/** Nombre de parcours proposés. */
export const NB_PARCOURS = PARCOURS.length;
