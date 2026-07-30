import { describe, it, expect } from 'vitest';

import {
  PLANS,
  PLAN_ENTREE,
  REMISE_PARTENAIRE,
  MIN_CLIENTS_PARTENAIRE,
  prixPartenaire,
} from './awareness-plans';

// Ces montants sont des données COMMERCIALES : ils apparaissent sur la landing,
// la page tarifs et dans SALES-BRIEF.md. Une dérive silencieuse ici se voit
// directement chez le prospect — c'est déjà arrivé deux fois (49 € affiché pour
// 79 €, « 17 modules » pour 28). D'où ces tests.

describe('Grille de sensibilisation — barème direct', () => {
  it('expose quatre paliers', () => {
    expect(PLANS).toHaveLength(4);
  });

  it('les prix sont strictement croissants', () => {
    const prix = PLANS.map(p => p.price);
    expect(prix).toEqual([...prix].sort((a, b) => a - b));
    expect(new Set(prix).size).toBe(prix.length);
  });

  it('le coût par apprenant est dégressif', () => {
    const parApprenant = PLANS.filter(p => p.maxLearners).map(p => p.price / p.maxLearners!);
    for (let i = 1; i < parApprenant.length; i++) {
      expect(parApprenant[i]).toBeLessThan(parApprenant[i - 1]);
    }
  });

  it("PLAN_ENTREE est bien le palier le moins cher (c'est lui qu'annonce la landing)", () => {
    expect(PLAN_ENTREE.price).toBe(Math.min(...PLANS.map(p => p.price)));
  });
});

describe('Tarif partenaire (consultants RSSI)', () => {
  it('applique la remise décidée', () => {
    expect(REMISE_PARTENAIRE).toBe(0.4);
  });

  it('correspond aux montants annoncés dans SALES-BRIEF.md', () => {
    // Si ce test casse, le document commercial est devenu faux : le corriger
    // AUSSI, ne pas se contenter d'ajuster la valeur attendue ici.
    expect(PLANS.map(prixPartenaire)).toEqual([47, 119, 269, 539]);
  });

  it('reste strictement en dessous du tarif direct', () => {
    for (const plan of PLANS) {
      expect(prixPartenaire(plan)).toBeLessThan(plan.price);
    }
  });

  it('conserve la logique de taille du barème direct', () => {
    // Point clé : un gros compte ne doit pas avoir intérêt à passer par un
    // consultant pour changer de barème. Les deux grilles restent ordonnées
    // de la même façon.
    const partenaire = PLANS.map(prixPartenaire);
    expect(partenaire).toEqual([...partenaire].sort((a, b) => a - b));
  });

  it('exige un minimum de clients, pour qu’un acheteur isolé ne se déclare pas partenaire', () => {
    expect(MIN_CLIENTS_PARTENAIRE).toBeGreaterThan(1);
  });
});
