import { describe, it, expect, vi } from 'vitest';
import { signal } from '@angular/core';
import { of } from 'rxjs';
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

describe('PhishingCampaignsComponent — statusLabel()', () => {
  it('retourne Brouillon pour draft', () => expect(make().statusLabel('draft')).toBe('Brouillon'));
  it('retourne En cours pour active', () => expect(make().statusLabel('active')).toBe('En cours'));
  it('retourne Envoi en cours pour sending', () =>
    expect(make().statusLabel('sending')).toBe('Envoi en cours'));
  it('retourne Terminée pour completed', () =>
    expect(make().statusLabel('completed')).toBe('Terminée'));
  it('retourne Prête pour ready', () => expect(make().statusLabel('ready')).toBe('Prête'));
  it('retourne Planifiée pour scheduled', () =>
    expect(make().statusLabel('scheduled')).toBe('Planifiée'));
  it('retourne Annulée pour cancelled', () =>
    expect(make().statusLabel('cancelled')).toBe('Annulée'));
  it('retourne la valeur brute pour un statut inconnu', () =>
    expect(make().statusLabel('unknown')).toBe('unknown'));
});

describe('PhishingCampaignsComponent — statusColor()', () => {
  it('contient cyan pour active', () => expect(make().statusColor('active')).toContain('cyan'));
  it('contient cyan pour sending', () => expect(make().statusColor('sending')).toContain('cyan'));
  it('contient green pour completed', () =>
    expect(make().statusColor('completed')).toContain('green'));
  it('contient gray pour draft', () => expect(make().statusColor('draft')).toContain('gray'));
  it('contient red pour cancelled', () => expect(make().statusColor('cancelled')).toContain('red'));
  it('contient blue pour ready', () => expect(make().statusColor('ready')).toContain('blue'));
  it('contient purple pour scheduled', () =>
    expect(make().statusColor('scheduled')).toContain('purple'));
  it('contient yellow par défaut', () =>
    expect(make().statusColor('pending_verification')).toContain('yellow'));
});

describe('PhishingCampaignsComponent — trendData()', () => {
  it('exclut les campagnes sans emails envoyés', () => {
    const comp = make();
    comp.campaigns.set([
      campaign({ id: 1, emails_sent: 0, status: 'draft' }),
      campaign({
        id: 2,
        emails_sent: 10,
        status: 'completed',
        click_rate: 0.2,
        opened_count: 6,
        submitted_count: 1,
        started_at: '2024-01-01T00:00:00Z',
      }),
    ]);
    expect(comp.trendData.length).toBe(1);
    expect(comp.trendData[0].clickRate).toBe(20);
  });

  it('trie par started_at croissant', () => {
    const comp = make();
    comp.campaigns.set([
      campaign({
        id: 2,
        emails_sent: 5,
        click_rate: 0.2,
        opened_count: 2,
        submitted_count: 0,
        started_at: '2024-03-01T00:00:00Z',
      }),
      campaign({
        id: 1,
        emails_sent: 5,
        click_rate: 0.1,
        opened_count: 1,
        submitted_count: 0,
        started_at: '2024-01-01T00:00:00Z',
      }),
    ]);
    const trend = comp.trendData;
    expect(trend[0].clickRate).toBe(10);
    expect(trend[1].clickRate).toBe(20);
  });

  it('tronque les noms > 12 caractères', () => {
    const comp = make();
    comp.campaigns.set([
      campaign({
        emails_sent: 1,
        opened_count: 0,
        submitted_count: 0,
        click_rate: 0,
        name: 'Campagne très longue Q4',
        started_at: '2024-01-01T00:00:00Z',
      }),
    ]);
    expect(comp.trendData[0].label.endsWith('…')).toBe(true);
    expect(comp.trendData[0].label.length).toBeLessThanOrEqual(13);
  });
});

describe('PhishingCampaignsComponent — trendPolyline()', () => {
  it('retourne une chaîne vide si aucun point', () => {
    expect(make().trendPolyline('clickRate', [])).toBe('');
  });

  it('retourne un point centré pour 1 campagne', () => {
    const pts = [{ label: 'A', date: '01/01/24', openRate: 50, clickRate: 20, submitRate: 5 }];
    const result = make().trendPolyline('clickRate', pts);
    expect(result).toContain('200.0');
  });

  it('retourne 2 points séparés pour 2 campagnes', () => {
    const pts = [
      { label: 'A', date: '01/01/24', openRate: 0, clickRate: 0, submitRate: 0 },
      { label: 'B', date: '01/02/24', openRate: 0, clickRate: 100, submitRate: 0 },
    ];
    const result = make().trendPolyline('clickRate', pts);
    const pairs = result.split(' ');
    expect(pairs.length).toBe(2);
    expect(pairs[0]).toContain('0.0');
    expect(pairs[1]).toContain('400.0');
  });
});

describe('PhishingCampaignsComponent — trendDotX / trendDotY / trendXPct()', () => {
  it('trendDotX centre à 200 pour 1 point', () => expect(make().trendDotX(0, 1)).toBe(200));
  it('trendDotX = 0 pour le premier de 2 points', () => expect(make().trendDotX(0, 2)).toBe(0));
  it('trendDotX = 400 pour le dernier de 2 points', () => expect(make().trendDotX(1, 2)).toBe(400));
  it('trendDotY = 84 pour rate=0 (bas du graphe)', () => expect(make().trendDotY(0)).toBe(84));
  it('trendDotY = 4 pour rate=100 (haut du graphe)', () => expect(make().trendDotY(100)).toBe(4));
  it('trendXPct = 50 pour 1 point', () => expect(make().trendXPct(0, 1)).toBe(50));
  it('trendXPct = 0 pour le premier de 2 points', () => expect(make().trendXPct(0, 2)).toBe(0));
  it('trendXPct = 100 pour le dernier de 2 points', () => expect(make().trendXPct(1, 2)).toBe(100));
});

describe('PhishingCampaignsComponent — clickRateLabel()', () => {
  it('retourne — pour un brouillon', () => {
    expect(make().clickRateLabel(campaign({ status: 'draft', click_rate: 0.2 }))).toBe('—');
  });

  it('retourne — si targets_count est 0', () => {
    expect(make().clickRateLabel(campaign({ status: 'completed', targets_count: 0 }))).toBe('—');
  });

  it('retourne le pourcentage pour une campagne avec cibles', () => {
    const result = make().clickRateLabel(
      campaign({
        status: 'completed',
        targets_count: 100,
        click_rate: 0.25,
      })
    );
    expect(result).toBe('25 %');
  });

  it("arrondit à l'entier le plus proche", () => {
    const result = make().clickRateLabel(
      campaign({
        status: 'active',
        targets_count: 50,
        click_rate: 0.333,
      })
    );
    expect(result).toBe('33 %');
  });
});

describe('PhishingCampaignsComponent — clickRateColor()', () => {
  it('retourne rouge pour taux ≥ 30 %', () => {
    expect(
      make().clickRateColor(campaign({ targets_count: 10, click_rate: 0.35, status: 'completed' }))
    ).toContain('red');
  });
  it('retourne jaune pour taux entre 15 % et 30 %', () => {
    expect(
      make().clickRateColor(campaign({ targets_count: 10, click_rate: 0.2, status: 'completed' }))
    ).toContain('yellow');
  });
  it('retourne vert pour taux < 15 %', () => {
    expect(
      make().clickRateColor(campaign({ targets_count: 10, click_rate: 0.1, status: 'completed' }))
    ).toContain('green');
  });
  it('retourne gris pour un brouillon', () => {
    expect(make().clickRateColor(campaign({ status: 'draft', targets_count: 0 }))).toContain(
      'gray'
    );
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

describe('PhishingCampaignsComponent — deleteCampaign()', () => {
  function evt() {
    return { stopPropagation: vi.fn(), preventDefault: vi.fn() } as unknown as Event;
  }

  it('supprime après confirmation et retire la campagne de la liste', () => {
    const comp = make();
    (comp as any).campaigns.set([campaign({ id: 1 }), campaign({ id: 2 })]);
    (comp as any).phishingService = { deleteCampaign: vi.fn().mockReturnValue(of(undefined)) };
    (comp as any).snack = { open: vi.fn() };
    vi.spyOn(window, 'confirm').mockReturnValue(true);

    comp.deleteCampaign(1, 'Test', evt());

    expect((comp as any).phishingService.deleteCampaign).toHaveBeenCalledWith(1);
    expect(comp.campaigns().map(c => c.id)).toEqual([2]);
  });

  it('ne supprime pas si la confirmation est annulée', () => {
    const comp = make();
    (comp as any).phishingService = { deleteCampaign: vi.fn() };
    (comp as any).snack = { open: vi.fn() };
    vi.spyOn(window, 'confirm').mockReturnValue(false);

    comp.deleteCampaign(1, 'Test', evt());

    expect((comp as any).phishingService.deleteCampaign).not.toHaveBeenCalled();
  });
});
