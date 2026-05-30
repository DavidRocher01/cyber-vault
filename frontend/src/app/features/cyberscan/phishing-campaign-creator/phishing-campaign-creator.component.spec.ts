import { describe, it, expect } from 'vitest';
import { signal } from '@angular/core';
import {
  PhishingCampaignCreatorComponent,
  PLAN_OPTIONS,
  STEPS,
  STEP_LABELS,
} from './phishing-campaign-creator.component';
import { LOOKALIKE_TECHNIQUE_LABELS } from '../services/phishing.service';

function make(): PhishingCampaignCreatorComponent {
  const comp = Object.create(
    PhishingCampaignCreatorComponent.prototype
  ) as PhishingCampaignCreatorComponent;
  (comp as any).currentStep = signal('plan');
  (comp as any).selectedPlan = signal('standard');
  (comp as any).selectedScenarios = signal(new Set<string>());
  (comp as any).campaign = signal(null);
  (comp as any).uploadedFile = signal(null);
  (comp as any).uploading = signal(false);
  (comp as any).submitting = signal(false);
  (comp as any).launching = signal(false);
  return comp;
}

// Re-export PLAN_OPTIONS from TS so we can test here
export { PLAN_OPTIONS, STEPS, STEP_LABELS };

describe('STEPS & STEP_LABELS', () => {
  it('contient 5 étapes', () => expect(STEPS).toHaveLength(5));
  it('commence par plan', () => expect(STEPS[0]).toBe('plan'));
  it('termine par review', () => expect(STEPS[STEPS.length - 1]).toBe('review'));
  it('chaque step a un label', () => {
    for (const s of STEPS) {
      expect(STEP_LABELS[s]).toBeTruthy();
    }
  });
});

describe('PLAN_OPTIONS', () => {
  it('contient 3 plans', () => expect(PLAN_OPTIONS).toHaveLength(3));
  it('standard est highlight', () =>
    expect(PLAN_OPTIONS.find(p => p.id === 'standard')?.highlight).toBe(true));
  it('express a maxTargets 50', () =>
    expect(PLAN_OPTIONS.find(p => p.id === 'express')?.maxTargets).toBe(50));
  it('premium a maxTargets 500', () =>
    expect(PLAN_OPTIONS.find(p => p.id === 'premium')?.maxTargets).toBe(500));
});

describe('PhishingCampaignCreatorComponent — stepIndex', () => {
  it('vaut 0 pour plan', () => expect(make().stepIndex).toBe(0));
  it('vaut 4 pour review', () => {
    const c = make();
    (c as any).currentStep.set('review');
    expect(c.stepIndex).toBe(4);
  });
});

describe('PhishingCampaignCreatorComponent — maxScenarios / maxTargets', () => {
  it('maxScenarios est 5 pour standard', () => expect(make().maxScenarios).toBe(5));
  it('maxTargets est 200 pour standard', () => expect(make().maxTargets).toBe(200));
  it('maxScenarios est 2 pour express', () => {
    const c = make();
    (c as any).selectedPlan.set('express');
    expect(c.maxScenarios).toBe(2);
  });
  it('maxTargets est 500 pour premium', () => {
    const c = make();
    (c as any).selectedPlan.set('premium');
    expect(c.maxTargets).toBe(500);
  });
});

describe('PhishingCampaignCreatorComponent — goTo()', () => {
  it('peut naviguer vers une étape précédente', () => {
    const c = make();
    (c as any).currentStep.set('targets');
    c.goTo('info');
    expect(c.currentStep()).toBe('info');
  });

  it('ne peut pas naviguer vers une étape future', () => {
    const c = make();
    c.goTo('review');
    expect(c.currentStep()).toBe('plan');
  });

  it("peut naviguer vers l'étape courante (no-op)", () => {
    const c = make();
    c.goTo('plan');
    expect(c.currentStep()).toBe('plan');
  });
});

describe('PhishingCampaignCreatorComponent — next() / prev()', () => {
  it("next() avance d'une étape", () => {
    const c = make();
    c.next();
    expect(c.currentStep()).toBe('info');
  });

  it('next() ne dépasse pas la dernière étape', () => {
    const c = make();
    (c as any).currentStep.set('review');
    c.next();
    expect(c.currentStep()).toBe('review');
  });

  it("prev() recule d'une étape", () => {
    const c = make();
    (c as any).currentStep.set('info');
    c.prev();
    expect(c.currentStep()).toBe('plan');
  });

  it('prev() ne remonte pas avant la première étape', () => {
    const c = make();
    c.prev();
    expect(c.currentStep()).toBe('plan');
  });
});

describe('LOOKALIKE_TECHNIQUE_LABELS', () => {
  it('contient un label pour sim_subdomain', () => {
    expect(LOOKALIKE_TECHNIQUE_LABELS['sim_subdomain']).toBeTruthy();
  });
  it('contient un label pour chaque technique', () => {
    const techniques = [
      'sim_subdomain',
      'combosquatting_prepend',
      'combosquatting_append',
      'tld_swap',
      'typo_missing_char',
      'typo_double_char',
      'typo_char_swap',
      'typo_homoglyph',
      'subdomain_trick',
    ] as const;
    for (const t of techniques) {
      expect(LOOKALIKE_TECHNIQUE_LABELS[t]).toBeTruthy();
    }
  });
});

describe('PhishingCampaignCreatorComponent — toggleScenario()', () => {
  it('ajoute un scénario', () => {
    const c = make();
    c.toggleScenario('ceo-fraud');
    expect(c.selectedScenarios().has('ceo-fraud')).toBe(true);
  });

  it('retire un scénario déjà sélectionné', () => {
    const c = make();
    c.toggleScenario('ceo-fraud');
    c.toggleScenario('ceo-fraud');
    expect(c.selectedScenarios().has('ceo-fraud')).toBe(false);
  });

  it('ne dépasse pas la limite du plan express (2)', () => {
    const c = make();
    (c as any).selectedPlan.set('express');
    c.toggleScenario('ceo-fraud');
    c.toggleScenario('o365-credentials');
    c.toggleScenario('fake-invoice'); // should be ignored
    expect(c.selectedScenarios().size).toBe(2);
    expect(c.selectedScenarios().has('fake-invoice')).toBe(false);
  });
});
