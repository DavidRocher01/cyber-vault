import { describe, it, expect } from 'vitest';
import { signal } from '@angular/core';
import { PhishingCampaignsComponent } from './phishing-campaigns.component';
import type { PhishingCampaign } from '../services/phishing.service';

function make(): PhishingCampaignsComponent {
  const comp = Object.create(PhishingCampaignsComponent.prototype) as PhishingCampaignsComponent;
  (comp as any).campaigns = signal<PhishingCampaign[]>([]);
  (comp as any).loading = signal(false);
  return comp;
}

function campaign(overrides: Partial<PhishingCampaign> = {}): PhishingCampaign {
  return {
    id: 1, name: 'Test', status: 'draft', plan_tier: 'standard',
    domain: null, domain_verified: false, lookalike_domain: null, scenario_keys: [],
    targets_count: 0, emails_sent: 0, opened_count: 0,
    clicked_count: 0, submitted_count: 0, click_rate: 0,
    cgu_accepted: false, scheduled_at: null, started_at: null,
    finished_at: null, created_at: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('PhishingCampaignsComponent — statusLabel()', () => {
  it('retourne Brouillon pour draft', () => expect(make().statusLabel('draft')).toBe('Brouillon'));
  it('retourne En cours pour active', () => expect(make().statusLabel('active')).toBe('En cours'));
  it('retourne Envoi en cours pour sending', () => expect(make().statusLabel('sending')).toBe('Envoi en cours'));
  it('retourne Terminée pour completed', () => expect(make().statusLabel('completed')).toBe('Terminée'));
  it('retourne Prête pour ready', () => expect(make().statusLabel('ready')).toBe('Prête'));
  it('retourne Annulée pour cancelled', () => expect(make().statusLabel('cancelled')).toBe('Annulée'));
  it('retourne la valeur brute pour un statut inconnu', () => expect(make().statusLabel('unknown')).toBe('unknown'));
});

describe('PhishingCampaignsComponent — statusColor()', () => {
  it('contient cyan pour active', () => expect(make().statusColor('active')).toContain('cyan'));
  it('contient cyan pour sending', () => expect(make().statusColor('sending')).toContain('cyan'));
  it('contient green pour completed', () => expect(make().statusColor('completed')).toContain('green'));
  it('contient gray pour draft', () => expect(make().statusColor('draft')).toContain('gray'));
  it('contient red pour cancelled', () => expect(make().statusColor('cancelled')).toContain('red'));
  it('contient blue pour ready', () => expect(make().statusColor('ready')).toContain('blue'));
  it('contient yellow par défaut', () => expect(make().statusColor('pending_verification')).toContain('yellow'));
});

describe('PhishingCampaignsComponent — clickRateLabel()', () => {
  it('retourne — pour un brouillon', () => {
    expect(make().clickRateLabel(campaign({ status: 'draft', click_rate: 0.20 }))).toBe('—');
  });

  it('retourne — si targets_count est 0', () => {
    expect(make().clickRateLabel(campaign({ status: 'completed', targets_count: 0 }))).toBe('—');
  });

  it('retourne le pourcentage pour une campagne avec cibles', () => {
    const result = make().clickRateLabel(campaign({
      status: 'completed', targets_count: 100, click_rate: 0.25,
    }));
    expect(result).toBe('25 %');
  });

  it('arrondit à l\'entier le plus proche', () => {
    const result = make().clickRateLabel(campaign({
      status: 'active', targets_count: 50, click_rate: 0.333,
    }));
    expect(result).toBe('33 %');
  });
});

describe('PhishingCampaignsComponent — clickRateColor()', () => {
  it('retourne rouge pour taux ≥ 30 %', () => {
    expect(make().clickRateColor(campaign({ targets_count: 10, click_rate: 0.35, status: 'completed' }))).toContain('red');
  });
  it('retourne jaune pour taux entre 15 % et 30 %', () => {
    expect(make().clickRateColor(campaign({ targets_count: 10, click_rate: 0.20, status: 'completed' }))).toContain('yellow');
  });
  it('retourne vert pour taux < 15 %', () => {
    expect(make().clickRateColor(campaign({ targets_count: 10, click_rate: 0.10, status: 'completed' }))).toContain('green');
  });
  it('retourne gris pour un brouillon', () => {
    expect(make().clickRateColor(campaign({ status: 'draft', targets_count: 0 }))).toContain('gray');
  });
});

describe('PhishingCampaignsComponent — formatDate()', () => {
  it('retourne — pour null', () => expect(make().formatDate(null)).toBe('—'));
  it('retourne une date formatée fr-FR', () => {
    const result = make().formatDate('2024-03-15T10:00:00Z');
    expect(result).toContain('2024');
    expect(result).toContain('03');
    expect(result).toContain('15');
  });
});
