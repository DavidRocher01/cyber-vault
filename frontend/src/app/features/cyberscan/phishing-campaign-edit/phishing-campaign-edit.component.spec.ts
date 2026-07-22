import { describe, it, expect, vi } from 'vitest';
import { signal } from '@angular/core';
import { of, throwError } from 'rxjs';
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

describe('PhishingCampaignEditComponent — planification', () => {
  function withSchedule(value: string | null): PhishingCampaignEditComponent {
    const comp = make();
    (comp as any).form.addControl('scheduled_at', new FormControl(value));
    return comp;
  }

  it('isScheduled = false sans date', () => expect(withSchedule(null).isScheduled).toBe(false));
  it('isScheduled = true pour une date future', () => {
    const future = new Date(Date.now() + 86_400_000).toISOString().slice(0, 16);
    expect(withSchedule(future).isScheduled).toBe(true);
  });
  it('isScheduled = false pour une date passée', () => {
    const past = new Date(Date.now() - 86_400_000).toISOString().slice(0, 16);
    expect(withSchedule(past).isScheduled).toBe(false);
  });

  it('scheduledAtIso = undefined sans date', () =>
    expect(withSchedule(null).scheduledAtIso).toBeUndefined());
  it('scheduledAtIso = undefined pour une date invalide', () =>
    expect(withSchedule('pas-une-date').scheduledAtIso).toBeUndefined());
  it('scheduledAtIso renvoie un ISO pour une date valide', () => {
    const iso = withSchedule('2030-06-15T12:00').scheduledAtIso;
    expect(iso).toBeDefined();
    expect(iso).toMatch(/^\d{4}-\d{2}-\d{2}T/);
  });

  it('minScheduledAt = chaîne datetime-local valide (format input)', () => {
    const v = make().minScheduledAt;
    expect(v).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/);
    expect(Number.isNaN(new Date(v).getTime())).toBe(false);
  });
});

describe('PhishingCampaignEditComponent — difficultyColor()', () => {
  it('red pour Difficile', () => expect(make().difficultyColor('Difficile')).toContain('red'));
  it('yellow pour Moyen', () => expect(make().difficultyColor('Moyen')).toContain('yellow'));
  it('green pour Facile', () => expect(make().difficultyColor('Facile')).toContain('green'));
});

describe('PhishingCampaignEditComponent — gestion des cibles (Lot 2)', () => {
  function withTargets(c: PhishingCampaignEditComponent) {
    (c as any).targets = signal<any[]>([]);
    (c as any).newTargetEmail = signal('');
    (c as any).addingTarget = signal(false);
    (c as any).campaignId = 1;
    return c;
  }

  it('reloadTargets charge la liste et resynchronise targets_count', () => {
    const comp = withTargets(make(campaign()));
    (comp as any).phishingService = {
      getTargets: vi.fn().mockReturnValue(
        of([
          { id: 1, email: 'a@x.com' },
          { id: 2, email: 'b@x.com' },
        ])
      ),
    };
    (comp as any).reloadTargets();
    expect(comp.targets().length).toBe(2);
    expect(comp.campaign()?.targets_count).toBe(2);
  });

  it('addTarget appelle le service et vide le champ, puis recharge', () => {
    const comp = withTargets(make(campaign()));
    comp.newTargetEmail.set('new@x.com');
    const getTargets = vi.fn().mockReturnValue(of([{ id: 1, email: 'new@x.com' }]));
    (comp as any).phishingService = {
      addTarget: vi.fn().mockReturnValue(of({ id: 1, email: 'new@x.com' })),
      getTargets,
    };
    comp.addTarget();
    expect((comp as any).phishingService.addTarget).toHaveBeenCalledWith(1, { email: 'new@x.com' });
    expect(comp.newTargetEmail()).toBe('');
    expect(getTargets).toHaveBeenCalled();
  });

  it('addTarget ne fait rien si le champ est vide', () => {
    const comp = withTargets(make(campaign()));
    (comp as any).phishingService = { addTarget: vi.fn() };
    comp.addTarget();
    expect((comp as any).phishingService.addTarget).not.toHaveBeenCalled();
  });

  it('removeTarget appelle deleteTarget puis recharge', () => {
    const comp = withTargets(make(campaign()));
    const getTargets = vi.fn().mockReturnValue(of([]));
    (comp as any).phishingService = {
      deleteTarget: vi.fn().mockReturnValue(of(undefined)),
      getTargets,
    };
    comp.removeTarget(5);
    expect((comp as any).phishingService.deleteTarget).toHaveBeenCalledWith(1, 5);
    expect(getTargets).toHaveBeenCalled();
  });

  it('addTarget ne fait rien si un ajout est déjà en cours', () => {
    const comp = withTargets(make(campaign()));
    comp.newTargetEmail.set('new@x.com');
    (comp as any).addingTarget.set(true);
    (comp as any).phishingService = { addTarget: vi.fn() };
    comp.addTarget();
    expect((comp as any).phishingService.addTarget).not.toHaveBeenCalled();
  });

  it('addTarget trim les espaces autour de l’email', () => {
    const comp = withTargets(make(campaign()));
    comp.newTargetEmail.set('  spaced@x.com  ');
    (comp as any).phishingService = {
      addTarget: vi.fn().mockReturnValue(of({ id: 1 })),
      getTargets: vi.fn().mockReturnValue(of([])),
    };
    comp.addTarget();
    expect((comp as any).phishingService.addTarget).toHaveBeenCalledWith(1, {
      email: 'spaced@x.com',
    });
  });

  it('addTarget en erreur remet addingTarget à false et ouvre un snack', () => {
    const comp = withTargets(make(campaign()));
    comp.newTargetEmail.set('new@x.com');
    (comp as any).phishingService = {
      addTarget: vi.fn().mockReturnValue(throwError(() => ({ error: { detail: 'déjà pris' } }))),
    };
    comp.addTarget();
    expect(comp.addingTarget()).toBe(false);
    expect((comp as any).snack.open).toHaveBeenCalledWith('déjà pris', 'Fermer', expect.anything());
  });

  it('removeTarget en erreur ouvre un snack', () => {
    const comp = withTargets(make(campaign()));
    (comp as any).phishingService = {
      deleteTarget: vi.fn().mockReturnValue(throwError(() => ({ error: {} }))),
    };
    comp.removeTarget(5);
    expect((comp as any).snack.open).toHaveBeenCalledWith(
      'Suppression impossible',
      'Fermer',
      expect.anything()
    );
  });
});

describe('PhishingCampaignEditComponent — load()', () => {
  function loadComp(routeId = '1'): PhishingCampaignEditComponent {
    const c = make(campaign());
    (c as any).targets = signal<any[]>([]);
    (c as any).campaignId = Number(routeId);
    (c as any).route = { snapshot: { paramMap: { get: () => routeId } } };
    (c as any).router = { navigate: vi.fn() };
    (c as any).title = { setTitle: vi.fn() };
    return c;
  }

  it('charge la campagne, patche le formulaire et remplit les scénarios', () => {
    const c = loadComp();
    const camp = campaign({ name: 'Ma campagne', scenario_keys: ['ceo-fraud', 'fake-invoice'] });
    (c as any).phishingService = {
      getCampaign: vi.fn().mockReturnValue(of(camp)),
      getTargets: vi.fn().mockReturnValue(of([])),
    };
    c.load();
    expect(c.campaign()?.name).toBe('Ma campagne');
    expect(c.selectedScenarios().has('ceo-fraud')).toBe(true);
    expect(c.selectedScenarios().has('fake-invoice')).toBe(true);
    expect(c.loading()).toBe(false);
    expect((c as any).title.setTitle).toHaveBeenCalled();
  });

  it('redirige vers le détail si la campagne est active', () => {
    const c = loadComp();
    (c as any).phishingService = {
      getCampaign: vi.fn().mockReturnValue(of(campaign({ status: 'active' }))),
    };
    c.load();
    expect((c as any).router.navigate).toHaveBeenCalledWith(['/phishing/campaigns', 1]);
    expect(c.campaign()?.status).not.toBe('active');
  });

  it('redirige aussi pour completed, sending et cancelled', () => {
    for (const status of ['completed', 'sending', 'cancelled'] as const) {
      const c = loadComp();
      (c as any).phishingService = {
        getCampaign: vi.fn().mockReturnValue(of(campaign({ status }))),
      };
      c.load();
      expect((c as any).router.navigate).toHaveBeenCalledWith(['/phishing/campaigns', 1]);
    }
  });

  it('en erreur affiche un snack et redirige vers la liste', () => {
    const c = loadComp();
    (c as any).phishingService = {
      getCampaign: vi.fn().mockReturnValue(throwError(() => ({ error: {} }))),
    };
    c.load();
    expect(c.loading()).toBe(false);
    expect((c as any).snack.open).toHaveBeenCalledWith(
      'Campagne introuvable',
      'Fermer',
      expect.anything()
    );
    expect((c as any).router.navigate).toHaveBeenCalledWith(['/phishing/campaigns']);
  });
});

describe('PhishingCampaignEditComponent — save()', () => {
  function saveComp(): PhishingCampaignEditComponent {
    const c = make(campaign());
    (c as any).campaignId = 1;
    return c;
  }

  it('ne fait rien si le nom est invalide', () => {
    const c = saveComp();
    (c as any).form.get('name')!.setValue('');
    (c as any).phishingService = { updateCampaign: vi.fn() };
    c.save();
    expect((c as any).phishingService.updateCampaign).not.toHaveBeenCalled();
    expect(c.saving()).toBe(false);
  });

  it('enregistre la campagne et affiche un snack de succès', () => {
    const c = saveComp();
    const updated = campaign({ name: 'MàJ' });
    (c as any).phishingService = { updateCampaign: vi.fn().mockReturnValue(of(updated)) };
    c.save();
    expect((c as any).phishingService.updateCampaign).toHaveBeenCalled();
    expect(c.campaign()?.name).toBe('MàJ');
    expect(c.saving()).toBe(false);
    expect((c as any).snack.open).toHaveBeenCalledWith(
      'Campagne enregistrée',
      'OK',
      expect.anything()
    );
  });

  it('en erreur affiche le détail renvoyé par le backend', () => {
    const c = saveComp();
    (c as any).phishingService = {
      updateCampaign: vi.fn().mockReturnValue(throwError(() => ({ error: { detail: 'boom' } }))),
    };
    c.save();
    expect(c.saving()).toBe(false);
    expect((c as any).snack.open).toHaveBeenCalledWith('boom', 'Fermer', expect.anything());
  });
});

describe('PhishingCampaignEditComponent — launch()', () => {
  function launchComp(): PhishingCampaignEditComponent {
    const c = make(campaign());
    (c as any).campaignId = 1;
    (c as any).router = { navigate: vi.fn() };
    return c;
  }

  it('lance la campagne (immédiat) puis navigue vers le détail', () => {
    const c = launchComp();
    (c as any).phishingService = { launchWithCgu: vi.fn().mockReturnValue(of({})) };
    c.launch();
    expect((c as any).phishingService.launchWithCgu).toHaveBeenCalled();
    expect(c.launching()).toBe(false);
    expect((c as any).snack.open).toHaveBeenCalledWith(
      'Campagne lancée !',
      'Voir',
      expect.anything()
    );
    expect((c as any).router.navigate).toHaveBeenCalledWith(['/phishing/campaigns', 1]);
  });

  it('affiche "Envoi planifié" quand une date future est renseignée', () => {
    const c = launchComp();
    const future = new Date(Date.now() + 86_400_000).toISOString().slice(0, 16);
    (c as any).form.addControl('scheduled_at', new FormControl(future));
    (c as any).phishingService = { launchWithCgu: vi.fn().mockReturnValue(of({})) };
    c.launch();
    expect((c as any).snack.open).toHaveBeenCalledWith(
      'Envoi planifié !',
      'Voir',
      expect.anything()
    );
  });

  it('en erreur remet launching à false et affiche un snack', () => {
    const c = launchComp();
    (c as any).phishingService = {
      launchWithCgu: vi.fn().mockReturnValue(throwError(() => ({ error: { detail: 'refusé' } }))),
    };
    c.launch();
    expect(c.launching()).toBe(false);
    expect((c as any).snack.open).toHaveBeenCalledWith('refusé', 'Fermer', expect.anything());
    expect((c as any).router.navigate).not.toHaveBeenCalled();
  });
});

describe('PhishingCampaignEditComponent — onFileChange()', () => {
  function fileEvent(file: File | null): Event {
    return {
      target: { files: file ? [file] : [], value: 'x' },
    } as unknown as Event;
  }

  function fileComp(): PhishingCampaignEditComponent {
    const c = make(campaign());
    (c as any).campaignId = 1;
    (c as any).targets = signal<any[]>([]);
    return c;
  }

  it('ne fait rien sans fichier', () => {
    const c = fileComp();
    (c as any).phishingService = { uploadTargets: vi.fn() };
    c.onFileChange(fileEvent(null));
    expect((c as any).phishingService.uploadTargets).not.toHaveBeenCalled();
    expect(c.uploadingTargets()).toBe(false);
  });

  it('importe le fichier et affiche le nombre de cibles ajoutées', () => {
    const c = fileComp();
    const file = new File(['a@x.com'], 'targets.csv');
    (c as any).phishingService = {
      uploadTargets: vi.fn().mockReturnValue(of({ targets_added: 3, targets_skipped: 0 })),
      getTargets: vi.fn().mockReturnValue(of([])),
    };
    c.onFileChange(fileEvent(file));
    expect((c as any).phishingService.uploadTargets).toHaveBeenCalledWith(1, file);
    expect(c.uploadingTargets()).toBe(false);
    expect((c as any).snack.open).toHaveBeenCalledWith(
      '3 cible(s) ajoutée(s)',
      'OK',
      expect.anything()
    );
  });

  it('mentionne les doublons ignorés quand il y en a', () => {
    const c = fileComp();
    const file = new File(['a@x.com'], 'targets.csv');
    (c as any).phishingService = {
      uploadTargets: vi.fn().mockReturnValue(of({ targets_added: 2, targets_skipped: 1 })),
      getTargets: vi.fn().mockReturnValue(of([])),
    };
    c.onFileChange(fileEvent(file));
    expect((c as any).snack.open).toHaveBeenCalledWith(
      '2 cible(s) ajoutée(s) (1 doublon(s) ignoré(s))',
      'OK',
      expect.anything()
    );
  });

  it('en erreur remet uploadingTargets à false et affiche un snack', () => {
    const c = fileComp();
    const file = new File(['a@x.com'], 'targets.csv');
    (c as any).phishingService = {
      uploadTargets: vi
        .fn()
        .mockReturnValue(throwError(() => ({ error: { detail: 'CSV invalide' } }))),
    };
    c.onFileChange(fileEvent(file));
    expect(c.uploadingTargets()).toBe(false);
    expect((c as any).snack.open).toHaveBeenCalledWith('CSV invalide', 'Fermer', expect.anything());
  });
});
