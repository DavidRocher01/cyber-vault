/**
 * AwarenessPricingComponent — la page n'avait AUCUN spec alors qu'elle affiche
 * des montants et des volumétries qui arrivent directement chez le prospect.
 *
 * Deux erreurs de ce type ont été corrigées le 2026-07-30 : un tarif annoncé à
 * 49 € pour 79 réels, et « 17 modules » pour 28. Ces tests verrouillent le lien
 * entre ce que la page affiche et les sources uniques (`awareness-plans.ts`,
 * `awareness-catalog.generated.ts`).
 */
import { describe, it, expect } from 'vitest';

import { AwarenessPricingComponent } from './awareness-pricing.component';
import { PLANS, prixPartenaire, REMISE_PARTENAIRE } from '../../../shared/awareness-plans';
import { NB_MODULES, PARCOURS } from '../../../shared/awareness-catalog.generated';

function make(): AwarenessPricingComponent {
  // Le composant n'a aucune dépendance injectée : instanciation directe.
  return new AwarenessPricingComponent();
}

describe('AwarenessPricingComponent — sources uniques', () => {
  it('affiche la grille tarifaire partagée, pas une copie', () => {
    expect(make().plans).toBe(PLANS);
  });

  it('affiche le nombre de modules dérivé du contenu', () => {
    expect(make().nbModules).toBe(NB_MODULES);
  });

  it('expose les parcours dérivés du contenu', () => {
    expect(make().parcours).toBe(PARCOURS);
  });
});

describe('AwarenessPricingComponent — tarif partenaire', () => {
  it('expose la fonction de calcul, pas des montants recopiés', () => {
    expect(make().prixPartenaire).toBe(prixPartenaire);
  });

  it('affiche la remise en pourcentage entier', () => {
    expect(make().remisePartenairePct).toBe(Math.round(REMISE_PARTENAIRE * 100));
    expect(Number.isInteger(make().remisePartenairePct)).toBe(true);
  });

  it('exige plus d’un client pour le tarif partenaire', () => {
    expect(make().minClientsPartenaire).toBeGreaterThan(1);
  });

  it('chaque palier a un prix partenaire strictement inférieur au direct', () => {
    const c = make();
    for (const plan of c.plans) {
      expect(c.prixPartenaire(plan)).toBeLessThan(plan.price);
    }
  });
});

describe('AwarenessPricingComponent — descriptif des fonctionnalités', () => {
  it('les groupes annoncent le vrai nombre de modules', () => {
    const items = make().featureGroups.flatMap(g => g.items);
    const ligneModules = items.find(i => i.includes('modules'));
    expect(ligneModules).toBeDefined();
    expect(ligneModules).toContain(String(NB_MODULES));
  });

  it('aucun groupe n’est vide', () => {
    for (const g of make().featureGroups) {
      expect(g.items.length).toBeGreaterThan(0);
      expect(g.title).toBeTruthy();
    }
  });

  it('ne revendique pas de certification', () => {
    // Le produit délivre une ATTESTATION de suivi. Revendiquer une
    // « certification » supposerait un organisme certificateur accrédité —
    // interdit par SALES-BRIEF.md, et risqué pour un vendeur de conformité.
    const texte = make()
      .featureGroups.flatMap(g => [g.title, ...g.items])
      .join(' ')
      .toLowerCase();
    expect(texte).not.toContain('certifiant');
    expect(texte).not.toContain('certification');
  });
});
