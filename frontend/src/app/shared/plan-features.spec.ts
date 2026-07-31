/**
 * Le dashboard annonce au client ce que chaque palier lui ouvrirait. Cette
 * promesse n'a de valeur que si elle correspond aux gardes réellement
 * appliquées par le serveur.
 *
 * Trouvé le 2026-07-31 : le palier Business (tier 4) n'apparaissait NULLE PART
 * dans l'interface. Ses cinq contrôles étaient facturés sans être annoncés, et
 * un client Pro n'avait aucun moyen de savoir ce qu'il gagnerait à monter. La
 * cause : la grille était du markup dupliqué, sans lien avec le backend.
 *
 * Les tests de paliers ci-dessous lisent la source Python et la croisent avec
 * le catalogue. Ils échoueront si un palier est gardé côté serveur sans être
 * annoncé côté client — ou l'inverse.
 */
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';

import { describe, it, expect } from 'vitest';

import {
  badgePalier,
  formatScanFrequency,
  MODULES_PAR_PALIER,
  modulesInclus,
  modulesVerrouilles,
  PALIERS,
} from './plan-features';

const RACINE = resolve(__dirname, '../../../..');

function fichiersPython(dossier: string): string[] {
  const trouves: string[] = [];
  for (const entree of readdirSync(dossier)) {
    if (entree === '__pycache__') continue;
    const chemin = join(dossier, entree);
    if (statSync(chemin).isDirectory()) trouves.push(...fichiersPython(chemin));
    else if (entree.endsWith('.py')) trouves.push(chemin);
  }
  return trouves;
}

/** Paliers effectivement gardés côté serveur, toutes formes de garde confondues. */
function paliersGardesBackend(): Set<number> {
  const paliers = new Set<number>();
  const sources = [
    ...fichiersPython(join(RACINE, 'backend/app/api/v1/endpoints')),
    join(RACINE, 'backend/app/services/scan_service.py'),
  ];
  for (const fichier of sources) {
    const code = readFileSync(fichier, 'utf-8');
    // Garde d'endpoint : Depends(require_min_tier(3))
    for (const m of code.matchAll(/require_min_tier\((\d+)\)/g)) paliers.add(Number(m[1]));
    // Garde de profondeur de scan : if tier >= 4:
    for (const m of code.matchAll(/if tier >= (\d+):/g)) paliers.add(Number(m[1]));
  }
  return paliers;
}

describe('Catalogue des modules par palier', () => {
  it('lit bien les gardes du backend', () => {
    // Garde-fou du test : si les regex ou les chemins cassent, il ne doit pas
    // passer en silence sur un ensemble vide.
    expect(paliersGardesBackend().size).toBeGreaterThan(1);
  });

  it('annonce tous les paliers que le backend garde réellement', () => {
    const annonces = new Set(MODULES_PAR_PALIER.map(m => m.palierMin));
    const oublies = [...paliersGardesBackend()].filter(p => !annonces.has(p));
    // C'est exactement ce qui manquait pour le palier 4.
    expect(oublies).toEqual([]);
  });

  it("n'annonce aucun palier que le backend ne garde pas", () => {
    // L'inverse est tout aussi grave : promettre un contenu inexistant.
    const gardes = paliersGardesBackend();
    const inventes = [...new Set(MODULES_PAR_PALIER.map(m => m.palierMin))].filter(
      p => !gardes.has(p)
    );
    expect(inventes).toEqual([]);
  });

  it('a des identifiants uniques', () => {
    const ids = MODULES_PAR_PALIER.map(m => m.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('ne référence que des paliers payants', () => {
    // Un module ouvert au Gratuit n'a rien à faire dans une grille d'upsell.
    for (const module of MODULES_PAR_PALIER) {
      expect(module.palierMin).toBeGreaterThan(PALIERS.GRATUIT);
      expect(module.palierMin).toBeLessThanOrEqual(PALIERS.BUSINESS);
    }
  });

  it('décrit chaque module sans champ vide', () => {
    for (const module of MODULES_PAR_PALIER) {
      expect(module.titre.length).toBeGreaterThan(0);
      expect(module.detail.length).toBeGreaterThan(0);
      expect(module.icone.length).toBeGreaterThan(0);
    }
  });
});

describe('modulesVerrouilles — ce que voit chaque profil', () => {
  it('le Gratuit voit tout le catalogue', () => {
    expect(modulesVerrouilles(PALIERS.GRATUIT)).toEqual([...MODULES_PAR_PALIER]);
  });

  it('le Starter ne voit plus les modules Starter', () => {
    const vus = modulesVerrouilles(PALIERS.STARTER);
    expect(vus.every(m => m.palierMin > PALIERS.STARTER)).toBe(true);
    expect(vus.length).toBeLessThan(MODULES_PAR_PALIER.length);
  });

  it('le Pro ne voit plus que du Business', () => {
    const vus = modulesVerrouilles(PALIERS.PRO);
    expect(vus.every(m => m.palierMin === PALIERS.BUSINESS)).toBe(true);
    // Le point de départ de ce chantier : un Pro ne voyait rien du tout.
    expect(vus.length).toBeGreaterThan(0);
  });

  it("le Business ne voit rien — il n'y a plus rien à débloquer", () => {
    expect(modulesVerrouilles(PALIERS.BUSINESS)).toEqual([]);
  });

  it('chaque palier voit strictement moins que le précédent', () => {
    const tailles = [PALIERS.GRATUIT, PALIERS.STARTER, PALIERS.PRO, PALIERS.BUSINESS].map(
      p => modulesVerrouilles(p).length
    );
    for (let i = 1; i < tailles.length; i++) {
      expect(tailles[i]).toBeLessThan(tailles[i - 1]);
    }
  });
});

describe('modulesInclus — ce que la modale annonce par plan', () => {
  it('est le complémentaire exact de modulesVerrouilles', () => {
    // Les deux vues doivent partitionner le catalogue : un module oublié des
    // deux côtés serait facturé sans jamais être annoncé, ce qui est
    // précisément le défaut d'origine.
    for (const palier of [PALIERS.GRATUIT, PALIERS.STARTER, PALIERS.PRO, PALIERS.BUSINESS]) {
      const inclus = modulesInclus(palier);
      const verrouilles = modulesVerrouilles(palier);
      expect(inclus.length + verrouilles.length).toBe(MODULES_PAR_PALIER.length);
      const ids = new Set([...inclus, ...verrouilles].map(m => m.id));
      expect(ids.size).toBe(MODULES_PAR_PALIER.length);
    }
  });

  it("le Gratuit n'a aucun module payant", () => {
    expect(modulesInclus(PALIERS.GRATUIT)).toEqual([]);
  });

  it('le Business a tout le catalogue', () => {
    expect(modulesInclus(PALIERS.BUSINESS)).toEqual([...MODULES_PAR_PALIER]);
  });

  it('chaque palier inclut tout ce que le précédent incluait', () => {
    const paliers = [PALIERS.STARTER, PALIERS.PRO, PALIERS.BUSINESS];
    for (let i = 1; i < paliers.length; i++) {
      const precedent = modulesInclus(paliers[i - 1]).map(m => m.id);
      const courant = modulesInclus(paliers[i]).map(m => m.id);
      for (const id of precedent) expect(courant).toContain(id);
      expect(courant.length).toBeGreaterThan(precedent.length);
    }
  });
});

describe('badgePalier', () => {
  it('nomme chaque palier payant', () => {
    expect(badgePalier(PALIERS.STARTER).libelle).toBe('STARTER');
    expect(badgePalier(PALIERS.PRO).libelle).toBe('PRO');
    expect(badgePalier(PALIERS.BUSINESS).libelle).toBe('BUSINESS');
  });

  it('donne une teinte distincte par palier', () => {
    const teintes = [PALIERS.STARTER, PALIERS.PRO, PALIERS.BUSINESS].map(
      p => badgePalier(p).classes
    );
    expect(new Set(teintes).size).toBe(3);
  });

  it('reste lisible pour un palier inattendu', () => {
    // Si un tier 5 apparaissait, mieux vaut un badge par défaut qu'un vide.
    expect(badgePalier(9).libelle).toBe('BUSINESS');
    expect(badgePalier(0).libelle).toBe('STARTER');
  });
});

describe('formatScanFrequency', () => {
  it('0 jour → à la demande (plan gratuit)', () => {
    expect(formatScanFrequency(0)).toBe('Scan à la demande');
  });
  it('valeur négative → à la demande', () => {
    expect(formatScanFrequency(-1)).toBe('Scan à la demande');
  });
  it('1 → quotidienne', () => {
    expect(formatScanFrequency(1)).toBe('Surveillance quotidienne');
  });
  it('7 → hebdomadaire', () => {
    expect(formatScanFrequency(7)).toBe('Surveillance hebdomadaire');
  });
  it('30 → mensuelle', () => {
    expect(formatScanFrequency(30)).toBe('Surveillance mensuelle');
  });
  it('14 → toutes les 2 semaines', () => {
    expect(formatScanFrequency(14)).toBe('Surveillance toutes les 2 semaines');
  });
  it('valeur atypique → repli en jours', () => {
    expect(formatScanFrequency(5)).toBe('Analyse tous les 5 jours');
  });
});
