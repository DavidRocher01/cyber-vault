/** Paliers d'abonnement, alignés sur `Plan.tier_level` côté backend. */
export const PALIERS = {
  GRATUIT: 1,
  STARTER: 2,
  PRO: 3,
  BUSINESS: 4,
} as const;

export interface ModulePalier {
  /** Identifiant stable, utilisé par les tests et le `track` du template. */
  id: string;
  icone: string;
  titre: string;
  /** Ce que le module apporte concrètement, en termes de résultat pas d'outil. */
  detail: string;
  /** Palier minimum qui l'ouvre (`tier_level`). */
  palierMin: number;
}

/**
 * Catalogue des modules ouverts par chaque palier payant.
 *
 * SOURCE DE VÉRITÉ — ces entrées reflètent les gardes réellement appliquées
 * côté backend, et rien d'autre :
 *   - palier 2 : `require_min_tier(2)` sur code_scans.py et sur les scripts de
 *     remédiation (scans.py), plus `Plan.allow_conformity_export` pour le PDF ;
 *   - palier 3 : `require_min_tier(3)` sur darkweb.py et darkweb_dossier.py,
 *     plus le bloc `if tier >= 3` de services/scan_service.py ;
 *   - palier 4 : le bloc `if tier >= 4` de services/scan_service.py.
 *
 * Écrit le 2026-07-31 : le dashboard listait ces modules en markup dupliqué,
 * et le palier Business n'y figurait NULLE PART — ses cinq contrôles étaient
 * factureés sans être annoncés, et aucun client Pro ne voyait ce qu'il y
 * gagnerait. Le test `plan-features.spec.ts` croise cette liste avec les
 * gardes du backend pour que la dérive ne se reproduise pas.
 *
 * N'ajouter ici que ce qui est réellement gardé côté serveur.
 */
export const MODULES_PAR_PALIER: readonly ModulePalier[] = [
  {
    id: 'code-scan',
    icone: 'code',
    titre: 'Analyse de code',
    detail: 'Bandit · Semgrep · pip-audit',
    palierMin: PALIERS.STARTER,
  },
  {
    id: 'remediation',
    icone: 'terminal',
    titre: 'Scripts de remédiation',
    detail: 'Corrections automatiques UFW · SSH · Nginx',
    palierMin: PALIERS.STARTER,
  },
  {
    id: 'export-conformite',
    icone: 'picture_as_pdf',
    titre: 'Export PDF de conformité',
    detail: 'Rapports NIS2 et ISO 27001 exportables',
    palierMin: PALIERS.STARTER,
  },
  {
    id: 'darkweb',
    icone: 'travel_explore',
    titre: 'Surveillance Dark Web + Dossier',
    detail: 'Fuites de données · Dossier Dark Web B2B',
    palierMin: PALIERS.PRO,
  },
  {
    id: 'threat-intel',
    icone: 'verified_user',
    titre: 'Threat Intel & TLS avancé',
    // Le bloc `tier >= 3` joue cinq scanners, pas deux : l'ancienne carte n'en
    // annoncait que la moitie.
    detail: 'Menaces connues · TLS approfondi · technologies · takeover · méthodes HTTP',
    palierMin: PALIERS.PRO,
  },
  {
    id: 'controles-avances',
    icone: 'policy',
    titre: 'Contrôles applicatifs avancés',
    detail: 'JWT · clickjacking · redirections ouvertes · listing de répertoires · robots.txt',
    palierMin: PALIERS.BUSINESS,
  },
];

/** Libellé et teinte du badge de palier, pour ne pas les recalculer dans le template. */
export function badgePalier(palier: number): { libelle: string; classes: string } {
  if (palier >= PALIERS.BUSINESS) {
    return {
      libelle: 'BUSINESS',
      classes: 'bg-amber-500/20 text-amber-400 border border-amber-700/30',
    };
  }
  if (palier >= PALIERS.PRO) {
    return {
      libelle: 'PRO',
      classes: 'bg-purple-500/20 text-purple-400 border border-purple-700/30',
    };
  }
  return {
    libelle: 'STARTER',
    classes: 'bg-cyan-500/20 text-cyan-400 border border-cyan-700/30',
  };
}

/** Modules qu'un abonné au palier `palier` n'a PAS encore, dans l'ordre du catalogue. */
export function modulesVerrouilles(palier: number): ModulePalier[] {
  return MODULES_PAR_PALIER.filter(m => m.palierMin > palier);
}

/** Modules qu'un abonné au palier `palier` a déjà — complémentaire du précédent. */
export function modulesInclus(palier: number): ModulePalier[] {
  return MODULES_PAR_PALIER.filter(m => m.palierMin <= palier);
}

/**
 * Traduit un intervalle de scan (en jours) en une formule lisible par un non-technicien.
 * Utilisé sur les cartes de tarifs (landing + onboarding) pour éviter le "Scan tous les 0 jours".
 */
export function formatScanFrequency(days: number): string {
  if (!days || days <= 0) return 'Scan à la demande';
  if (days === 1) return 'Surveillance quotidienne';
  if (days === 7) return 'Surveillance hebdomadaire';
  if (days === 30 || days === 31) return 'Surveillance mensuelle';
  if (days % 7 === 0) return `Surveillance toutes les ${days / 7} semaines`;
  return `Analyse tous les ${days} jours`;
}
