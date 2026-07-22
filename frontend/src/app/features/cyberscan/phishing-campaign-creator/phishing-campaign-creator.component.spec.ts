import { describe, it, expect, vi } from 'vitest';
import { signal } from '@angular/core';
import { of, throwError } from 'rxjs';
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

// ── ngOnInit ───────────────────────────────────────────────────────────────
describe('PhishingCampaignCreatorComponent — ngOnInit()', () => {
  it('définit le titre de la page', () => {
    const c = make();
    const setTitle = vi.fn();
    (c as any).title = { setTitle };
    c.ngOnInit();
    expect(setTitle).toHaveBeenCalledWith(expect.stringContaining('phishing'));
  });
});

// ── createAndNext() ──────────────────────────────────────────────────────────
describe('PhishingCampaignCreatorComponent — createAndNext()', () => {
  function makeInfo(overrides: Partial<{ name: string; domain: string }> = {}) {
    const c = make();
    (c as any).infoForm = {
      invalid: false,
      getRawValue: () => ({ name: 'Camp', domain: '', ...overrides }),
    };
    (c as any).snack = { open: vi.fn() };
    return c;
  }

  it('ne fait rien si le formulaire est invalide', () => {
    const c = makeInfo();
    (c as any).infoForm.invalid = true;
    const createCampaign = vi.fn();
    (c as any).service = { createCampaign };
    c.createAndNext();
    expect(createCampaign).not.toHaveBeenCalled();
    expect(c.submitting()).toBe(false);
  });

  it('ne fait rien si déjà en soumission', () => {
    const c = makeInfo();
    (c as any).submitting.set(true);
    const createCampaign = vi.fn();
    (c as any).service = { createCampaign };
    c.createAndNext();
    expect(createCampaign).not.toHaveBeenCalled();
  });

  it('sans domaine : crée la campagne et avance', () => {
    const c = makeInfo();
    const camp = { id: 42, name: 'Camp' };
    (c as any).service = { createCampaign: vi.fn().mockReturnValue(of(camp)) };
    c.createAndNext();
    expect(c.campaign()).toEqual(camp);
    expect(c.submitting()).toBe(false);
    expect(c.currentStep()).toBe('info');
  });

  it('avec domaine : patch le domaine puis avance', () => {
    const c = makeInfo({ domain: '  exemple.fr  ' });
    const camp = { id: 42, name: 'Camp' };
    const updated = { id: 42, name: 'Camp', domain: 'exemple.fr' };
    const updateCampaign = vi.fn().mockReturnValue(of(updated));
    (c as any).service = {
      createCampaign: vi.fn().mockReturnValue(of(camp)),
      updateCampaign,
    };
    c.createAndNext();
    expect(updateCampaign).toHaveBeenCalledWith(42, { domain: 'exemple.fr' });
    expect(c.campaign()).toEqual(updated);
    expect(c.currentStep()).toBe('info');
  });

  it('avec domaine : si le patch échoue, garde la campagne créée et avance', () => {
    const c = makeInfo({ domain: 'exemple.fr' });
    const camp = { id: 42, name: 'Camp' };
    (c as any).service = {
      createCampaign: vi.fn().mockReturnValue(of(camp)),
      updateCampaign: vi.fn().mockReturnValue(throwError(() => new Error('boom'))),
    };
    c.createAndNext();
    expect(c.campaign()).toEqual(camp);
    expect(c.submitting()).toBe(false);
    expect(c.currentStep()).toBe('info');
  });

  it('erreur de création : snackbar et reste sur place', () => {
    const c = makeInfo();
    (c as any).service = {
      createCampaign: vi.fn().mockReturnValue(throwError(() => new Error('x'))),
    };
    c.createAndNext();
    expect(c.submitting()).toBe(false);
    expect(c.currentStep()).toBe('plan');
    expect((c as any).snack.open).toHaveBeenCalled();
  });
});

// ── onFileChange() ───────────────────────────────────────────────────────────
describe('PhishingCampaignCreatorComponent — onFileChange()', () => {
  it('stocke le fichier sélectionné', () => {
    const c = make();
    const file = new File(['a'], 'cibles.csv');
    const event = { target: { files: [file] } } as unknown as Event;
    c.onFileChange(event);
    expect(c.uploadedFile()).toBe(file);
  });

  it('ne fait rien si aucun fichier', () => {
    const c = make();
    const event = { target: { files: [] } } as unknown as Event;
    c.onFileChange(event);
    expect(c.uploadedFile()).toBeNull();
  });
});

// ── uploadTargets() ──────────────────────────────────────────────────────────
describe('PhishingCampaignCreatorComponent — uploadTargets()', () => {
  function makeUpload() {
    const c = make();
    (c as any).snack = { open: vi.fn() };
    return c;
  }

  it('ne fait rien sans fichier', () => {
    const c = makeUpload();
    (c as any).campaign.set({ id: 1 });
    const uploadTargets = vi.fn();
    (c as any).service = { uploadTargets };
    c.uploadTargets();
    expect(uploadTargets).not.toHaveBeenCalled();
  });

  it('ne fait rien sans campagne', () => {
    const c = makeUpload();
    (c as any).uploadedFile.set(new File(['a'], 'x.csv'));
    const uploadTargets = vi.fn();
    (c as any).service = { uploadTargets };
    c.uploadTargets();
    expect(uploadTargets).not.toHaveBeenCalled();
  });

  it('succès : maj du compte de cibles, snackbar et avance', () => {
    const c = makeUpload();
    (c as any).uploadedFile.set(new File(['a'], 'x.csv'));
    (c as any).campaign.set({ id: 1, targets_count: 0 });
    (c as any).service = {
      uploadTargets: vi.fn().mockReturnValue(of({ targets_added: 12 })),
    };
    c.uploadTargets();
    expect(c.uploading()).toBe(false);
    expect(c.campaign()?.targets_count).toBe(12);
    expect(c.currentStep()).toBe('info');
    expect((c as any).snack.open).toHaveBeenCalled();
  });

  it('erreur : affiche le détail renvoyé par le backend', () => {
    const c = makeUpload();
    (c as any).uploadedFile.set(new File(['a'], 'x.csv'));
    (c as any).campaign.set({ id: 1 });
    (c as any).service = {
      uploadTargets: vi
        .fn()
        .mockReturnValue(throwError(() => ({ error: { detail: 'CSV invalide' } }))),
    };
    c.uploadTargets();
    expect(c.uploading()).toBe(false);
    expect((c as any).snack.open).toHaveBeenCalledWith('CSV invalide', 'Fermer', expect.anything());
  });
});

// ── saveScenarios() ──────────────────────────────────────────────────────────
describe('PhishingCampaignCreatorComponent — saveScenarios()', () => {
  it('ne fait rien sans campagne', () => {
    const c = make();
    c.toggleScenario('ceo-fraud');
    const updateCampaign = vi.fn();
    (c as any).service = { updateCampaign };
    c.saveScenarios();
    expect(updateCampaign).not.toHaveBeenCalled();
  });

  it('ne fait rien si aucun scénario sélectionné', () => {
    const c = make();
    (c as any).campaign.set({ id: 1 });
    const updateCampaign = vi.fn();
    (c as any).service = { updateCampaign };
    c.saveScenarios();
    expect(updateCampaign).not.toHaveBeenCalled();
  });

  it('succès : enregistre les scénarios et avance', () => {
    const c = make();
    (c as any).campaign.set({ id: 1 });
    c.toggleScenario('ceo-fraud');
    const updated = { id: 1, scenario_keys: ['ceo-fraud'] };
    const updateCampaign = vi.fn().mockReturnValue(of(updated));
    (c as any).service = { updateCampaign };
    c.saveScenarios();
    expect(updateCampaign).toHaveBeenCalledWith(1, { scenario_keys: ['ceo-fraud'] });
    expect(c.campaign()).toEqual(updated);
    expect(c.currentStep()).toBe('info');
  });
});

// ── launch() ─────────────────────────────────────────────────────────────────
describe('PhishingCampaignCreatorComponent — launch()', () => {
  function makeLaunch() {
    const c = make();
    (c as any).reviewForm = { invalid: false };
    (c as any).snack = { open: vi.fn() };
    (c as any).router = { navigate: vi.fn() };
    return c;
  }

  it('ne fait rien si les CGU ne sont pas acceptées', () => {
    const c = makeLaunch();
    (c as any).reviewForm.invalid = true;
    (c as any).campaign.set({ id: 1 });
    const launchWithCgu = vi.fn();
    (c as any).service = { launchWithCgu };
    c.launch();
    expect(launchWithCgu).not.toHaveBeenCalled();
  });

  it('ne fait rien sans campagne', () => {
    const c = makeLaunch();
    const launchWithCgu = vi.fn();
    (c as any).service = { launchWithCgu };
    c.launch();
    expect(launchWithCgu).not.toHaveBeenCalled();
  });

  it('succès : snackbar et redirection vers la liste', () => {
    const c = makeLaunch();
    (c as any).campaign.set({ id: 7 });
    (c as any).service = {
      launchWithCgu: vi.fn().mockReturnValue(of({ status: 'active', campaign_id: 7 })),
    };
    c.launch();
    expect(c.launching()).toBe(false);
    expect((c as any).snack.open).toHaveBeenCalled();
    expect((c as any).router.navigate).toHaveBeenCalledWith(['/phishing/campaigns']);
  });

  it('erreur : affiche le détail et ne redirige pas', () => {
    const c = makeLaunch();
    (c as any).campaign.set({ id: 7 });
    (c as any).service = {
      launchWithCgu: vi
        .fn()
        .mockReturnValue(throwError(() => ({ error: { detail: 'Domaine non vérifié' } }))),
    };
    c.launch();
    expect(c.launching()).toBe(false);
    expect((c as any).snack.open).toHaveBeenCalledWith(
      'Domaine non vérifié',
      'Fermer',
      expect.anything()
    );
    expect((c as any).router.navigate).not.toHaveBeenCalled();
  });
});
