import { describe, it, expect, vi } from 'vitest';
import { signal } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { PhishingCampaignEditComponent } from './phishing-campaign-edit.component';
import type { PhishingCampaign } from '../services/phishing.service';

function campaign(overrides: Partial<PhishingCampaign> = {}): PhishingCampaign {
  return {
    id: 1,
    name: 'Test',
    status: 'draft',
    plan_tier: 'standard',
    domain: null,
    domain_verified: false,
    lookalike_domain: null,
    scenario_keys: [],
    targets_count: 0,
    emails_sent: 0,
    opened_count: 0,
    clicked_count: 0,
    submitted_count: 0,
    click_rate: 0,
    cgu_accepted: false,
    scheduled_at: null,
    started_at: null,
    finished_at: null,
    created_at: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

function make(c: PhishingCampaign | null = null): PhishingCampaignEditComponent {
  const comp = Object.create(
    PhishingCampaignEditComponent.prototype
  ) as PhishingCampaignEditComponent;
  (comp as any).campaign = signal<PhishingCampaign | null>(c);
  (comp as any).loading = signal(false);
  (comp as any).saving = signal(false);
  (comp as any).launching = signal(false);
  (comp as any).uploadingTargets = signal(false);
  (comp as any).selectedScenarios = signal<Set<string>>(new Set());
  (comp as any).snack = { open: vi.fn() };
  (comp as any).form = new FormGroup({
    name: new FormControl('Campagne test', [
      Validators.required,
      Validators.minLength(2),
      Validators.maxLength(100),
    ]),
    cgu_accepted: new FormControl(false, Validators.requiredTrue),
  });
  return comp;
}

describe('PhishingCampaignEditComponent — maxScenarios', () => {
  it('vaut 2 pour express', () =>
    expect(make(campaign({ plan_tier: 'express' })).maxScenarios).toBe(2));
  it('vaut 5 pour standard', () =>
    expect(make(campaign({ plan_tier: 'standard' })).maxScenarios).toBe(5));
  it('vaut 10 pour premium', () =>
    expect(make(campaign({ plan_tier: 'premium' })).maxScenarios).toBe(10));
  it('vaut 3 pour quarterly', () =>
    expect(make(campaign({ plan_tier: 'quarterly' })).maxScenarios).toBe(3));
  it('vaut 7 pour monthly', () =>
    expect(make(campaign({ plan_tier: 'monthly' })).maxScenarios).toBe(7));
  it('vaut 2 par défaut quand campaign est null', () => expect(make(null).maxScenarios).toBe(2));
  it('vaut 2 pour un plan inconnu', () =>
    expect(make(campaign({ plan_tier: 'unknown' })).maxScenarios).toBe(2));
});

describe('PhishingCampaignEditComponent — toggleScenario()', () => {
  it('ajoute un scénario', () => {
    const c = make(campaign({ plan_tier: 'standard' }));
    c.toggleScenario('ceo-fraud');
    expect(c.isScenarioSelected('ceo-fraud')).toBe(true);
  });

  it('retire un scénario déjà sélectionné', () => {
    const c = make(campaign({ plan_tier: 'standard' }));
    c.toggleScenario('ceo-fraud');
    c.toggleScenario('ceo-fraud');
    expect(c.isScenarioSelected('ceo-fraud')).toBe(false);
  });

  it('ne dépasse pas la limite express (2)', () => {
    const c = make(campaign({ plan_tier: 'express' }));
    c.toggleScenario('ceo-fraud');
    c.toggleScenario('fake-invoice');
    c.toggleScenario('o365-credentials'); // ignoré
    expect(c.selectedScenarios().size).toBe(2);
    expect(c.isScenarioSelected('o365-credentials')).toBe(false);
  });

  it('ne dépasse pas la limite standard (5)', () => {
    const c = make(campaign({ plan_tier: 'standard' }));
    ['ceo-fraud', 'fake-invoice', 'o365-credentials', 'bank-phishing', 'parcel-tracking'].forEach(
      id => c.toggleScenario(id)
    );
    c.toggleScenario('it-password'); // ignoré
    expect(c.selectedScenarios().size).toBe(5);
    expect(c.isScenarioSelected('it-password')).toBe(false);
  });

  it('peut retirer un scénario même à la limite du plan', () => {
    const c = make(campaign({ plan_tier: 'express' }));
    c.toggleScenario('ceo-fraud');
    c.toggleScenario('fake-invoice');
    c.toggleScenario('ceo-fraud'); // retire
    expect(c.selectedScenarios().size).toBe(1);
    expect(c.isScenarioSelected('ceo-fraud')).toBe(false);
    expect(c.isScenarioSelected('fake-invoice')).toBe(true);
  });
});

describe('PhishingCampaignEditComponent — isScenarioSelected()', () => {
  it('retourne false pour un scénario non sélectionné', () => {
    expect(make().isScenarioSelected('ceo-fraud')).toBe(false);
  });
  it('retourne true après sélection', () => {
    const c = make(campaign());
    c.toggleScenario('ceo-fraud');
    expect(c.isScenarioSelected('ceo-fraud')).toBe(true);
  });
});

describe('PhishingCampaignEditComponent — canLaunch', () => {
  function readyComp(): PhishingCampaignEditComponent {
    const c = make(campaign({ status: 'ready', targets_count: 10 }));
    c.toggleScenario('ceo-fraud');
    (c as any).form.get('name')!.setValue('Campagne test');
    (c as any).form.get('cgu_accepted')!.setValue(true);
    return c;
  }

  it('est vrai quand toutes les conditions sont remplies (status ready)', () => {
    expect(readyComp().canLaunch).toBe(true);
  });

  it('est vrai pour status draft', () => {
    const c = readyComp();
    (c as any).campaign.set(campaign({ status: 'draft', targets_count: 10 }));
    expect(c.canLaunch).toBe(true);
  });

  it('est faux sans campagne', () => {
    expect(make(null).canLaunch).toBe(false);
  });

  it('est faux si statut est active', () => {
    const c = readyComp();
    (c as any).campaign.set(campaign({ status: 'active', targets_count: 10 }));
    expect(c.canLaunch).toBe(false);
  });

  it('est faux si statut est completed', () => {
    const c = readyComp();
    (c as any).campaign.set(campaign({ status: 'completed', targets_count: 10 }));
    expect(c.canLaunch).toBe(false);
  });

  it('est faux sans scénario sélectionné', () => {
    const c = readyComp();
    (c as any).selectedScenarios.set(new Set());
    expect(c.canLaunch).toBe(false);
  });

  it('est faux sans cibles (targets_count = 0)', () => {
    const c = readyComp();
    (c as any).campaign.set(campaign({ status: 'ready', targets_count: 0 }));
    expect(c.canLaunch).toBe(false);
  });

  it('est faux sans CGU acceptées', () => {
    const c = readyComp();
    (c as any).form.get('cgu_accepted')!.setValue(false);
    expect(c.canLaunch).toBe(false);
  });

  it('est faux avec un nom trop court (< 2 caractères)', () => {
    const c = readyComp();
    (c as any).form.get('name')!.setValue('A');
    expect(c.canLaunch).toBe(false);
  });

  it('est faux avec un nom vide', () => {
    const c = readyComp();
    (c as any).form.get('name')!.setValue('');
    expect(c.canLaunch).toBe(false);
  });
});

describe('PhishingCampaignEditComponent — statusLabel()', () => {
  it('retourne Brouillon pour draft', () => expect(make().statusLabel('draft')).toBe('Brouillon'));
  it('retourne Prête pour ready', () => expect(make().statusLabel('ready')).toBe('Prête'));
  it('retourne Vérification pour pending_verification', () => {
    expect(make().statusLabel('pending_verification')).toBe('Vérification');
  });
  it('retourne la valeur brute pour un statut inconnu', () => {
    expect(make().statusLabel('unknown')).toBe('unknown');
  });
});

describe('PhishingCampaignEditComponent — statusColor()', () => {
  it('blue pour ready', () => expect(make().statusColor('ready')).toContain('blue'));
  it('gray par défaut pour draft', () => expect(make().statusColor('draft')).toContain('gray'));
});

describe('PhishingCampaignEditComponent — difficultyColor()', () => {
  it('red pour Difficile', () => expect(make().difficultyColor('Difficile')).toContain('red'));
  it('yellow pour Moyen', () => expect(make().difficultyColor('Moyen')).toContain('yellow'));
  it('green pour Facile', () => expect(make().difficultyColor('Facile')).toContain('green'));
});
