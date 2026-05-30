import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { signal } from '@angular/core';
import { of } from 'rxjs';
import { PhishingCampaignDetailComponent } from './phishing-campaign-detail.component';
import type { PhishingCampaign } from '../services/phishing.service';
import { PHISHING_SCENARIOS } from '../phishing/phishing.component';

function make(): PhishingCampaignDetailComponent {
  const comp = Object.create(
    PhishingCampaignDetailComponent.prototype
  ) as PhishingCampaignDetailComponent;
  (comp as any).campaign = signal<PhishingCampaign | null>(null);
  (comp as any).loading = signal(false);
  (comp as any).downloadingPdf = signal(false);
  (comp as any).scenarios = PHISHING_SCENARIOS;
  return comp;
}

function campaign(overrides: Partial<PhishingCampaign> = {}): PhishingCampaign {
  return {
    id: 1,
    name: 'Test',
    status: 'active',
    plan_tier: 'standard',
    domain: null,
    domain_verified: false,
    lookalike_domain: null,
    scenario_keys: [],
    targets_count: 100,
    emails_sent: 80,
    opened_count: 40,
    clicked_count: 20,
    submitted_count: 5,
    click_rate: 0.25,
    cgu_accepted: true,
    scheduled_at: null,
    started_at: null,
    finished_at: null,
    created_at: '2024-01-01T00:00:00Z',
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
  it("arrondit à l'entier", () => {
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
  it("calcule la progression d'envoi", () => {
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
  it('yellow par défaut', () =>
    expect(make().statusColor('pending_verification')).toContain('yellow'));
});

describe('PhishingCampaignDetailComponent — targetStatusLabel()', () => {
  const cases: [string, string][] = [
    ['pending', 'En attente'],
    ['email_sent', 'Envoyé'],
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
  it('blue pour email_sent', () =>
    expect(make().targetStatusColor('email_sent')).toContain('blue'));
  it('gray par défaut (pending)', () =>
    expect(make().targetStatusColor('pending')).toContain('gray'));
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

// ── Polling automatique ────────────────────────────────────────────────────────

function makeForPolling(status: string) {
  const base = campaign({ status: status as PhishingCampaign['status'] });
  const getCampaign = vi.fn().mockReturnValue(of(base));

  const comp = Object.create(
    PhishingCampaignDetailComponent.prototype
  ) as PhishingCampaignDetailComponent;
  (comp as any).campaign = signal<PhishingCampaign | null>(base);
  (comp as any).loading = signal(false);
  (comp as any).downloadingPdf = signal(false);
  (comp as any).scenarios = PHISHING_SCENARIOS;
  (comp as any).campaignId = 1;
  // Minimal DI stubs — no injection context required
  (comp as any).destroyRef = { onDestroy: vi.fn() };
  (comp as any).route = { snapshot: { paramMap: { get: () => '1' } } };
  (comp as any).router = { navigate: vi.fn() };
  (comp as any).snack = { open: vi.fn() };
  (comp as any).title = { setTitle: vi.fn() };
  (comp as any).phishingService = { getCampaign };

  return { comp, getCampaign };
}

describe('PhishingCampaignDetailComponent — polling automatique', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('appelle getCampaign toutes les 5s quand status=sending', () => {
    const { comp, getCampaign } = makeForPolling('sending');
    comp.ngOnInit();
    getCampaign.mockClear(); // ignore l'appel initial de load()

    vi.advanceTimersByTime(5_000);
    expect(getCampaign).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(5_000);
    expect(getCampaign).toHaveBeenCalledTimes(2);
  });

  it('appelle getCampaign toutes les 5s quand status=active', () => {
    const { comp, getCampaign } = makeForPolling('active');
    comp.ngOnInit();
    getCampaign.mockClear();

    vi.advanceTimersByTime(5_000);
    expect(getCampaign).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(5_000);
    expect(getCampaign).toHaveBeenCalledTimes(2);
  });

  it('ne poll pas quand status=completed', () => {
    const { comp, getCampaign } = makeForPolling('completed');
    comp.ngOnInit();
    getCampaign.mockClear();

    vi.advanceTimersByTime(15_000); // 3 ticks potentiels
    expect(getCampaign).not.toHaveBeenCalled();
  });

  it('ne poll pas quand status=draft', () => {
    const { comp, getCampaign } = makeForPolling('draft');
    comp.ngOnInit();
    getCampaign.mockClear();

    vi.advanceTimersByTime(15_000);
    expect(getCampaign).not.toHaveBeenCalled();
  });

  it('ne poll pas quand status=cancelled', () => {
    const { comp, getCampaign } = makeForPolling('cancelled');
    comp.ngOnInit();
    getCampaign.mockClear();

    vi.advanceTimersByTime(15_000);
    expect(getCampaign).not.toHaveBeenCalled();
  });

  it('met à jour le signal campaign avec la réponse du polling', () => {
    const updated = campaign({ status: 'sending', emails_sent: 42 });
    const { comp, getCampaign } = makeForPolling('sending');
    getCampaign.mockReturnValue(of(updated));
    comp.ngOnInit();

    vi.advanceTimersByTime(5_000);
    expect((comp as any).campaign()).toEqual(updated);
  });

  it('stoppe le polling après transition sending → completed', () => {
    const { comp, getCampaign } = makeForPolling('sending');
    comp.ngOnInit();
    getCampaign.mockClear();

    // Premier tick : campagne encore en cours d'envoi
    vi.advanceTimersByTime(5_000);
    expect(getCampaign).toHaveBeenCalledTimes(1);
    getCampaign.mockClear();

    // Simulation : le polling a ramené un statut completed et mis à jour le signal
    (comp as any).campaign.set(campaign({ status: 'completed' }));

    // Tick suivant : EMPTY retourné, aucun appel API
    vi.advanceTimersByTime(5_000);
    expect(getCampaign).not.toHaveBeenCalled();
  });
});
