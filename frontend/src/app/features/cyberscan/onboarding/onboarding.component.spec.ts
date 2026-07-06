/**
 * OnboardingComponent — tests de la logique (pas de rendu).
 *
 * Instanciation directe via Object.create + injection de mocks, comme les
 * autres specs du repo. Aucune requête réseau : les observables sont simulés
 * avec of()/throwError().
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { signal } from '@angular/core';
import { FormBuilder } from '@angular/forms';
import { of, throwError } from 'rxjs';
import { OnboardingComponent } from './onboarding.component';
import type { Plan } from '../services/cyberscan.service';

function makePlan(over: Partial<Plan> = {}): Plan {
  return {
    id: 1,
    name: 'starter',
    display_name: 'Starter',
    price_eur: 29,
    max_sites: 1,
    scan_interval_days: 30,
    tier_level: 1,
    stripe_price_id: 'price_x',
    ...over,
  };
}

function make(): OnboardingComponent {
  const comp = Object.create(OnboardingComponent.prototype) as OnboardingComponent;

  (comp as any).plans = signal<Plan[]>([]);
  (comp as any).selectedPlan = signal<Plan | null>(null);
  (comp as any).checkoutLoading = signal(false);
  (comp as any).addingSite = signal(false);
  (comp as any).currentStep = signal(1);

  const fb = new FormBuilder();
  (comp as any).fb = fb;
  (comp as any).siteForm = fb.nonNullable.group({
    url: [''],
    name: [''],
  });

  (comp as any).cyberscan = {
    getPlans: vi.fn(() => of([])),
    getMySubscription: vi.fn(() => of(null)),
    createCheckout: vi.fn(() => of({ checkout_url: '/dashboard' })),
    createSite: vi.fn(() => of({ id: 42 })),
    triggerScan: vi.fn(() => of({ scan_id: 7, message: 'ok' })),
  };
  (comp as any).router = { navigate: vi.fn(), navigateByUrl: vi.fn() };
  (comp as any).snack = { open: vi.fn() };
  (comp as any).title = { setTitle: vi.fn() };

  return comp;
}

// ── formatPrice ────────────────────────────────────────────────────────────
describe('OnboardingComponent — formatPrice()', () => {
  it('convertit les centimes en euros', () => {
    const r = make().formatPrice(2900);
    expect(r).toContain('29');
    expect(r).toContain('€');
  });

  it('gère zéro', () => {
    expect(make().formatPrice(0)).toContain('0');
  });

  it('gère les centimes non ronds', () => {
    const r = make().formatPrice(1999);
    expect(r).toContain('19,99');
  });
});

// ── planFeatures ───────────────────────────────────────────────────────────
describe('OnboardingComponent — planFeatures()', () => {
  it('singulier pour 1 site', () => {
    const f = make().planFeatures(makePlan({ max_sites: 1 }));
    expect(f[0]).toBe('1 site surveillé');
  });

  it('pluriel pour plusieurs sites', () => {
    const f = make().planFeatures(makePlan({ max_sites: 3 }));
    expect(f[0]).toBe('3 sites surveillés');
  });

  it('mentionne la fréquence de scan', () => {
    const f = make().planFeatures(makePlan({ scan_interval_days: 30 }));
    expect(f.some(x => x.includes('30 jours'))).toBe(true);
  });

  it('ajoute alertes immédiates si scan <= 7 jours', () => {
    const f = make().planFeatures(makePlan({ scan_interval_days: 7 }));
    expect(f).toContain('Alertes email immédiates');
  });

  it("n'ajoute pas alertes immédiates si scan > 7 jours", () => {
    const f = make().planFeatures(makePlan({ scan_interval_days: 14 }));
    expect(f).not.toContain('Alertes email immédiates');
  });

  it('ajoute rapports PDF si scan <= 14 jours', () => {
    const f = make().planFeatures(makePlan({ scan_interval_days: 14 }));
    expect(f).toContain('Rapports PDF inclus');
  });

  it("n'ajoute pas rapports PDF si scan > 14 jours", () => {
    const f = make().planFeatures(makePlan({ scan_interval_days: 30 }));
    expect(f).not.toContain('Rapports PDF inclus');
  });

  it('ajoute multi-sites si max_sites >= 5', () => {
    const f = make().planFeatures(makePlan({ max_sites: 5 }));
    expect(f).toContain('Multi-sites & équipes');
  });

  it("n'ajoute pas multi-sites si max_sites < 5", () => {
    const f = make().planFeatures(makePlan({ max_sites: 4 }));
    expect(f).not.toContain('Multi-sites & équipes');
  });
});

// ── selectPlan ─────────────────────────────────────────────────────────────
describe('OnboardingComponent — selectPlan()', () => {
  it('mémorise le plan et active le loading', () => {
    const comp = make();
    // Empêche la complétion synchrone du subscribe : observable qui n'émet pas
    (comp as any).cyberscan.createCheckout = vi.fn(() => ({ subscribe: () => {} }));
    const plan = makePlan();
    comp.selectPlan(plan);
    expect(comp.selectedPlan()).toBe(plan);
    expect(comp.checkoutLoading()).toBe(true);
    expect((comp as any).cyberscan.createCheckout).toHaveBeenCalledWith(plan.id);
  });

  it('navigue en interne pour une URL relative', () => {
    const comp = make();
    (comp as any).cyberscan.createCheckout = vi.fn(() => of({ checkout_url: '/dashboard' }));
    comp.selectPlan(makePlan());
    expect((comp as any).router.navigateByUrl).toHaveBeenCalledWith('/dashboard');
  });

  it('navigue en interne pour une URL de même hôte (localhost)', () => {
    const comp = make();
    const url = `${window.location.origin}/checkout/step?x=1`;
    (comp as any).cyberscan.createCheckout = vi.fn(() => of({ checkout_url: url }));
    comp.selectPlan(makePlan());
    expect((comp as any).router.navigateByUrl).toHaveBeenCalledWith('/checkout/step?x=1');
  });

  it('ignore une URL invalide sans naviguer', () => {
    const comp = make();
    (comp as any).cyberscan.createCheckout = vi.fn(() => of({ checkout_url: 'pas une url' }));
    comp.selectPlan(makePlan());
    expect((comp as any).router.navigateByUrl).not.toHaveBeenCalled();
  });

  it('désactive le loading en cas d’erreur', () => {
    const comp = make();
    (comp as any).cyberscan.createCheckout = vi.fn(() => throwError(() => new Error('boom')));
    comp.selectPlan(makePlan());
    expect(comp.checkoutLoading()).toBe(false);
  });
});

// ── addSiteAndScan ─────────────────────────────────────────────────────────
describe('OnboardingComponent — addSiteAndScan()', () => {
  it('ne fait rien si le formulaire est invalide', () => {
    const comp = make();
    // form url/name vides mais sans validators ici → forçons invalide
    comp.siteForm.get('url')!.setErrors({ required: true });
    comp.addSiteAndScan();
    expect((comp as any).cyberscan.createSite).not.toHaveBeenCalled();
  });

  it('préfixe https:// si le protocole est absent', () => {
    const comp = make();
    comp.siteForm.setValue({ url: 'example.com', name: 'Exemple' });
    comp.addSiteAndScan();
    expect((comp as any).cyberscan.createSite).toHaveBeenCalledWith({
      url: 'https://example.com',
      name: 'Exemple',
    });
  });

  it('conserve l’URL si elle commence déjà par http', () => {
    const comp = make();
    comp.siteForm.setValue({ url: 'http://deja.com', name: 'X' });
    comp.addSiteAndScan();
    expect((comp as any).cyberscan.createSite).toHaveBeenCalledWith({
      url: 'http://deja.com',
      name: 'X',
    });
  });

  it('passe à l’étape 3 et déclenche le scan en cas de succès', () => {
    const comp = make();
    comp.siteForm.setValue({ url: 'example.com', name: 'Exemple' });
    comp.addSiteAndScan();
    expect(comp.currentStep()).toBe(3);
    expect(comp.addingSite()).toBe(false);
    expect((comp as any).cyberscan.triggerScan).toHaveBeenCalledWith(42);
  });

  it('affiche une erreur si le scan échoue', () => {
    const comp = make();
    (comp as any).cyberscan.triggerScan = vi.fn(() => throwError(() => new Error('scan ko')));
    comp.siteForm.setValue({ url: 'example.com', name: 'Exemple' });
    comp.addSiteAndScan();
    expect((comp as any).snack.open).toHaveBeenCalled();
    // On reste tout de même à l'étape 3 (site créé)
    expect(comp.currentStep()).toBe(3);
  });

  it('affiche le détail d’erreur si createSite échoue', () => {
    const comp = make();
    (comp as any).cyberscan.createSite = vi.fn(() =>
      throwError(() => ({ error: { detail: 'Quota atteint' } }))
    );
    comp.siteForm.setValue({ url: 'example.com', name: 'Exemple' });
    comp.addSiteAndScan();
    expect(comp.addingSite()).toBe(false);
    expect((comp as any).snack.open).toHaveBeenCalledWith(
      'Quota atteint',
      'Fermer',
      expect.anything()
    );
  });

  it('utilise un message générique si pas de détail', () => {
    const comp = make();
    (comp as any).cyberscan.createSite = vi.fn(() => throwError(() => ({})));
    comp.siteForm.setValue({ url: 'example.com', name: 'Exemple' });
    comp.addSiteAndScan();
    expect((comp as any).snack.open).toHaveBeenCalledWith('Erreur', 'Fermer', expect.anything());
  });
});

// ── goBack / goToDashboard ─────────────────────────────────────────────────
describe('OnboardingComponent — navigation', () => {
  it('goBack depuis l’étape 2 revient à l’étape 1', () => {
    const comp = make();
    comp.currentStep.set(2);
    comp.goBack();
    expect(comp.currentStep()).toBe(1);
    expect((comp as any).router.navigate).not.toHaveBeenCalled();
  });

  it('goBack depuis l’étape 1 va au dashboard', () => {
    const comp = make();
    comp.currentStep.set(1);
    comp.goBack();
    expect((comp as any).router.navigate).toHaveBeenCalledWith(['/dashboard']);
  });

  it('goToDashboard navigue vers le dashboard', () => {
    const comp = make();
    comp.goToDashboard();
    expect((comp as any).router.navigate).toHaveBeenCalledWith(['/dashboard']);
  });
});

// ── ngOnInit ───────────────────────────────────────────────────────────────
describe('OnboardingComponent — ngOnInit()', () => {
  it('charge les plans', () => {
    const comp = make();
    const plans = [makePlan()];
    (comp as any).cyberscan.getPlans = vi.fn(() => of(plans));
    comp.ngOnInit();
    expect(comp.plans()).toEqual(plans);
  });

  it('saute à l’étape 2 si un abonnement existe déjà', () => {
    const comp = make();
    (comp as any).cyberscan.getMySubscription = vi.fn(() => of({ id: 1 }));
    comp.ngOnInit();
    expect(comp.currentStep()).toBe(2);
  });

  it('reste à l’étape 1 sans abonnement', () => {
    const comp = make();
    (comp as any).cyberscan.getMySubscription = vi.fn(() => of(null));
    comp.ngOnInit();
    expect(comp.currentStep()).toBe(1);
  });

  it('définit le titre de la page', () => {
    const comp = make();
    comp.ngOnInit();
    expect((comp as any).title.setTitle).toHaveBeenCalled();
  });
});
