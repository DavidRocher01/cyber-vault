import { describe, it, expect } from 'vitest';
import { signal } from '@angular/core';
import { PhishingCampaignDetailComponent } from './phishing-campaign-detail.component';
import type { PhishingCampaign } from '../services/phishing.service';
import { PHISHING_SCENARIOS } from '../phishing/phishing.component';

function make(): PhishingCampaignDetailComponent {
  const comp = Object.create(PhishingCampaignDetailComponent.prototype) as PhishingCampaignDetailComponent;
  (comp as any).campaign = signal<PhishingCampaign | null>(null);
  (comp as any).loading = signal(false);
  (comp as any).downloadingPdf = signal(false);
  (comp as any).scenarios = PHISHING_SCENARIOS;
  return comp;
}

function campaign(overrides: Partial<PhishingCampaign> = {}): PhishingCampaign {
  return {
    id: 1, name: 'Test', status: 'active', plan_tier: 'standard',
    domain: null, domain_verified: false, lookalike_domain: null, scenario_keys: [],
    targets_count: 100, emails_sent: 80, opened_count: 40,
    clicked_count: 20, submitted_count: 5, click_rate: 0.25,
    cgu_accepted: true, scheduled_at: null, started_at: null,
    finished_at: null, created_at: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('PhishingCampaignDetailComponent — openRate()', () => {
  it('calcule le pourcentage arrondi', () => {
    expect(make().openRate(campaign({ opened_count: 40, emails_sent: 80 }))).toBe(50);
  });
  it('retourne 0 si aucun email envoyé', () => {
    expect(make().openRate(campaign({ emails_sent: 0 }))).toBe(0);
  });
  it('arrondit à l\'entier', () => {
    expect(make().openRate(campaign({ opened_count: 1, emails_sent: 3 }))).toBe(33);
  });
});

describe('PhishingCampaignDetailComponent — clickRate()', () => {
  it('calcule le taux de clic', () => {
    expect(make().clickRate(campaign({ clicked_count: 20, emails_sent: 80 }))).toBe(25);
  });
  it('retourne 0 si aucun email envoyé', () => {
    expect(make().clickRate(campaign({ emails_sent: 0 }))).toBe(0);
  });
});

describe('PhishingCampaignDetailComponent — submitRate()', () => {
  it('calcule le taux de soumission', () => {
    expect(make().submitRate(campaign({ submitted_count: 8, emails_sent: 80 }))).toBe(10);
  });
  it('retourne 0 si aucun email envoyé', () => {
    expect(make().submitRate(campaign({ emails_sent: 0 }))).toBe(0);
  });
});

describe('PhishingCampaignDetailComponent — sendProgress()', () => {
  it('calcule la progression d\'envoi', () => {
    expect(make().sendProgress(campaign({ emails_sent: 40, targets_count: 100 }))).toBe(40);
  });
  it('retourne 0 si aucune cible', () => {
    expect(make().sendProgress(campaign({ targets_count: 0 }))).toBe(0);
  });
  it('retourne 100 quand tous les emails sont envoyés', () => {
    expect(make().sendProgress(campaign({ emails_sent: 100, targets_count: 100 }))).toBe(100);
  });
});

describe('PhishingCampaignDetailComponent — riskLevel()', () => {
  it('Risque élevé pour taux ≥ 30 %', () => {
    const result = make().riskLevel(campaign({ clicked_count: 30, emails_sent: 100 }));
    expect(result.label).toBe('Risque élevé');
    expect(result.color).toContain('red');
  });
  it('Risque modéré pour taux entre 15 % et 29 %', () => {
    const result = make().riskLevel(campaign({ clicked_count: 20, emails_sent: 100 }));
    expect(result.label).toBe('Risque modéré');
    expect(result.color).toContain('yellow');
  });
  it('Risque faible pour taux entre 1 % et 14 %', () => {
    const result = make().riskLevel(campaign({ clicked_count: 10, emails_sent: 100 }));
    expect(result.label).toBe('Risque faible');
    expect(result.color).toContain('green');
  });
  it('— pour 0 clic', () => {
    const result = make().riskLevel(campaign({ clicked_count: 0, emails_sent: 100 }));
    expect(result.label).toBe('—');
    expect(result.color).toContain('gray');
  });
});

describe('PhishingCampaignDetailComponent — statusLabel()', () => {
  const cases: [string, string][] = [
    ['draft', 'Brouillon'],
    ['pending_verification', 'Vérification'],
    ['ready', 'Prête'],
    ['sending', 'Envoi en cours'],
    ['active', 'En cours'],
    ['completed', 'Terminée'],
    ['cancelled', 'Annulée'],
  ];
  for (const [status, label] of cases) {
    it(`retourne "${label}" pour "${status}"`, () => {
      expect(make().statusLabel(status)).toBe(label);
    });
  }
  it('retourne la valeur brute pour un statut inconnu', () => {
    expect(make().statusLabel('unknown')).toBe('unknown');
  });
});

describe('PhishingCampaignDetailComponent — statusColor()', () => {
  it('cyan pour active', () => expect(make().statusColor('active')).toContain('cyan'));
  it('cyan pour sending', () => expect(make().statusColor('sending')).toContain('cyan'));
  it('green pour completed', () => expect(make().statusColor('completed')).toContain('green'));
  it('gray pour draft', () => expect(make().statusColor('draft')).toContain('gray'));
  it('blue pour ready', () => expect(make().statusColor('ready')).toContain('blue'));
  it('red pour cancelled', () => expect(make().statusColor('cancelled')).toContain('red'));
  it('yellow par défaut', () => expect(make().statusColor('pending_verification')).toContain('yellow'));
});

describe('PhishingCampaignDetailComponent — targetStatusLabel()', () => {
  const cases: [string, string][] = [
    ['pending', 'En attente'],
    ['sent', 'Envoyé'],
    ['opened', 'Ouvert'],
    ['clicked', 'Cliqué'],
    ['submitted', 'Identifiants saisis'],
  ];
  for (const [status, label] of cases) {
    it(`retourne "${label}" pour "${status}"`, () => {
      expect(make().targetStatusLabel(status)).toBe(label);
    });
  }
  it('retourne la valeur brute pour un statut inconnu', () => {
    expect(make().targetStatusLabel('unknown')).toBe('unknown');
  });
});

describe('PhishingCampaignDetailComponent — targetStatusColor()', () => {
  it('red pour submitted', () => expect(make().targetStatusColor('submitted')).toContain('red'));
  it('orange pour clicked', () => expect(make().targetStatusColor('clicked')).toContain('orange'));
  it('yellow pour opened', () => expect(make().targetStatusColor('opened')).toContain('yellow'));
  it('blue pour sent', () => expect(make().targetStatusColor('sent')).toContain('blue'));
  it('gray par défaut (pending)', () => expect(make().targetStatusColor('pending')).toContain('gray'));
});

describe('PhishingCampaignDetailComponent — scenarioName()', () => {
  it('retourne le nom pour ceo-fraud', () => {
    expect(make().scenarioName('ceo-fraud')).toBe('Fraude au Président');
  });
  it('retourne le nom pour o365-credentials', () => {
    expect(make().scenarioName('o365-credentials')).toBe('Credentials Office 365');
  });
  it('retourne le nom pour hr-document', () => {
    expect(make().scenarioName('hr-document')).toBe('Document RH Confidentiel');
  });
  it('retourne la clé brute pour un scénario inconnu', () => {
    expect(make().scenarioName('unknown-scenario')).toBe('unknown-scenario');
  });
});

describe('PhishingCampaignDetailComponent — formatDate()', () => {
  it('retourne — pour null', () => {
    expect(make().formatDate(null)).toBe('—');
  });
  it('retourne une date formatée fr-FR', () => {
    const result = make().formatDate('2024-03-15T10:00:00Z');
    expect(result).toContain('2024');
    expect(result).toContain('03');
    expect(result).toContain('15');
  });
});
