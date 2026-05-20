import { describe, it, expect } from 'vitest';
import { signal } from '@angular/core';
import {
  PhishingComponent,
  PHISHING_SCENARIOS,
  PRICING_TIERS,
  SUBSCRIPTION_TIERS,
  METHOD_STEPS,
  FAQ_ITEMS,
  USE_CASES,
} from './phishing.component';

function make(): PhishingComponent {
  const comp = Object.create(PhishingComponent.prototype) as PhishingComponent;
  (comp as any).openFaqIndex = signal<number | null>(null);
  return comp;
}

// ── Static data ──────────────────────────────────────────────────────────────

describe('PHISHING_SCENARIOS', () => {
  it('contient 10 scénarios', () => expect(PHISHING_SCENARIOS).toHaveLength(10));

  it('chaque scénario a id, name, description, difficulty, vector, icon', () => {
    for (const s of PHISHING_SCENARIOS) {
      expect(s.id).toBeTruthy();
      expect(s.name).toBeTruthy();
      expect(s.description).toBeTruthy();
      expect(['Facile', 'Moyen', 'Difficile']).toContain(s.difficulty);
      expect(s.vector).toBeTruthy();
      expect(s.icon).toBeTruthy();
    }
  });

  it('inclut le scénario CEO Fraud', () => {
    expect(PHISHING_SCENARIOS.some(s => s.id === 'ceo-fraud')).toBe(true);
  });

  it('inclut des scénarios de chaque niveau de difficulté', () => {
    expect(PHISHING_SCENARIOS.some(s => s.difficulty === 'Facile')).toBe(true);
    expect(PHISHING_SCENARIOS.some(s => s.difficulty === 'Moyen')).toBe(true);
    expect(PHISHING_SCENARIOS.some(s => s.difficulty === 'Difficile')).toBe(true);
  });

  it('les ids sont uniques', () => {
    const ids = PHISHING_SCENARIOS.map(s => s.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});

describe('PRICING_TIERS (one-shot)', () => {
  it('contient 3 offres', () => expect(PRICING_TIERS).toHaveLength(3));

  it('inclut Express, Standard, Premium', () => {
    const names = PRICING_TIERS.map(t => t.name);
    expect(names).toContain('Express');
    expect(names).toContain('Standard');
    expect(names).toContain('Premium');
  });

  it('Express est à 800 €', () => {
    expect(PRICING_TIERS.find(t => t.id === 'express')?.price).toContain('800');
  });

  it('Standard est à 1 500 €', () => {
    expect(PRICING_TIERS.find(t => t.id === 'standard')?.price).toContain('1 500');
  });

  it('Premium est à 2 500 €', () => {
    expect(PRICING_TIERS.find(t => t.id === 'premium')?.price).toContain('2 500');
  });

  it('Standard est le seul highlight', () => {
    const highlighted = PRICING_TIERS.filter(t => t.highlight);
    expect(highlighted).toHaveLength(1);
    expect(highlighted[0].id).toBe('standard');
  });

  it('chaque offre a au moins 4 features', () => {
    for (const tier of PRICING_TIERS) {
      expect(tier.features.length).toBeGreaterThanOrEqual(4);
    }
  });
});

describe('SUBSCRIPTION_TIERS', () => {
  it('contient 2 offres', () => expect(SUBSCRIPTION_TIERS).toHaveLength(2));

  it('inclut Trimestrielle et Mensuelle', () => {
    const names = SUBSCRIPTION_TIERS.map(t => t.name);
    expect(names).toContain('Trimestrielle');
    expect(names).toContain('Mensuelle');
  });

  it('Trimestrielle est à 250 €/mois', () => {
    const tier = SUBSCRIPTION_TIERS.find(t => t.id === 'quarterly');
    expect(tier?.price).toContain('250');
    expect(tier?.priceDetail).toContain('mois');
  });

  it('Mensuelle est à 600 €/mois', () => {
    const tier = SUBSCRIPTION_TIERS.find(t => t.id === 'monthly');
    expect(tier?.price).toContain('600');
    expect(tier?.priceDetail).toContain('mois');
  });

  it('Mensuelle est highlight', () => {
    expect(SUBSCRIPTION_TIERS.find(t => t.id === 'monthly')?.highlight).toBe(true);
  });
});

describe('METHOD_STEPS', () => {
  it('contient 6 étapes', () => expect(METHOD_STEPS).toHaveLength(6));

  it('les étapes sont numérotées de 1 à 6', () => {
    for (let i = 0; i < METHOD_STEPS.length; i++) {
      expect(METHOD_STEPS[i].step).toBe(i + 1);
    }
  });

  it('chaque étape a title, description et icon', () => {
    for (const step of METHOD_STEPS) {
      expect(step.title).toBeTruthy();
      expect(step.description).toBeTruthy();
      expect(step.icon).toBeTruthy();
    }
  });
});

describe('FAQ_ITEMS', () => {
  it('contient 6 questions', () => expect(FAQ_ITEMS).toHaveLength(6));

  it('chaque item a question et answer non vides', () => {
    for (const item of FAQ_ITEMS) {
      expect(item.question).toBeTruthy();
      expect(item.answer).toBeTruthy();
    }
  });

  it('mentionne la légalité', () => {
    expect(FAQ_ITEMS.some(f => f.question.toLowerCase().includes('légal'))).toBe(true);
  });

  it('mentionne le RGPD ou les données', () => {
    const allText = FAQ_ITEMS.map(f => f.answer).join(' ').toLowerCase();
    expect(allText).toMatch(/rgpd|donn[eé]e/);
  });
});

describe('USE_CASES', () => {
  it('contient 3 cas d\'usage', () => expect(USE_CASES).toHaveLength(3));

  it('chaque cas a icon, title, subtitle, description, result, color', () => {
    for (const uc of USE_CASES) {
      expect(uc.icon).toBeTruthy();
      expect(uc.title).toBeTruthy();
      expect(uc.subtitle).toBeTruthy();
      expect(uc.description).toBeTruthy();
      expect(uc.result).toBeTruthy();
      expect(uc.color).toBeTruthy();
    }
  });

  it('inclut un cas NIS2', () => {
    expect(USE_CASES.some(uc => uc.description.includes('NIS2') || uc.title.includes('NIS2'))).toBe(true);
  });
});

// ── Component methods ─────────────────────────────────────────────────────────

describe('PhishingComponent — difficultyColor()', () => {
  it('retourne vert pour Facile', () => expect(make().difficultyColor('Facile')).toContain('green'));
  it('retourne jaune pour Moyen', () => expect(make().difficultyColor('Moyen')).toContain('yellow'));
  it('retourne rouge pour Difficile', () => expect(make().difficultyColor('Difficile')).toContain('red'));
  it('retourne gris pour valeur inconnue', () => expect(make().difficultyColor('unknown')).toContain('gray'));
});

describe('PhishingComponent — useCaseColor()', () => {
  it('retourne rouge pour red', () => expect(make().useCaseColor('red').border).toContain('red'));
  it('retourne bleu pour blue', () => expect(make().useCaseColor('blue').border).toContain('blue'));
  it('retourne violet pour purple', () => expect(make().useCaseColor('purple').border).toContain('purple'));
  it('retourne un objet avec border, icon, badge', () => {
    const result = make().useCaseColor('red');
    expect(result).toHaveProperty('border');
    expect(result).toHaveProperty('icon');
    expect(result).toHaveProperty('badge');
  });
});

describe('PhishingComponent — toggleFaq()', () => {
  it('ouvre la question 0 au premier appel', () => {
    const c = make();
    c.toggleFaq(0);
    expect(c.openFaqIndex()).toBe(0);
  });

  it('ferme la même question au second appel', () => {
    const c = make();
    c.toggleFaq(0);
    c.toggleFaq(0);
    expect(c.openFaqIndex()).toBeNull();
  });

  it('change de question ouverte', () => {
    const c = make();
    c.toggleFaq(0);
    c.toggleFaq(2);
    expect(c.openFaqIndex()).toBe(2);
  });
});
