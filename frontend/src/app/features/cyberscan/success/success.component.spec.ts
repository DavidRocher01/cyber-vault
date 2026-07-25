/**
 * CheckoutSuccessComponent — tests de la logique ngOnInit (lecture de
 * l'abonnement pour afficher le nom du plan). Aucun rendu, aucun réseau.
 */
import { describe, it, expect, vi } from 'vitest';
import { of } from 'rxjs';
import { CheckoutSuccessComponent } from './success.component';

function make(): CheckoutSuccessComponent {
  const comp = Object.create(CheckoutSuccessComponent.prototype) as CheckoutSuccessComponent;
  comp.planName = '';
  (comp as any).title = { setTitle: vi.fn() };
  (comp as any).cyberscan =
    (comp as any).complianceApi =
    (comp as any).publicScanApi =
    (comp as any).notifApi =
    (comp as any).codeScanApi =
    (comp as any).urlScanApi =
    (comp as any).scanApi =
    (comp as any).siteApi =
    (comp as any).billing =
      { getMySubscription: vi.fn(() => of(null)) };
  return comp;
}

describe('CheckoutSuccessComponent — ngOnInit()', () => {
  it('renseigne le nom du plan depuis l’abonnement', () => {
    const comp = make();
    (comp as any).cyberscan.getMySubscription = vi.fn(() => of({ plan: { display_name: 'Pro' } }));
    comp.ngOnInit();
    expect(comp.planName).toBe('Pro');
  });

  it('laisse planName vide si pas d’abonnement', () => {
    const comp = make();
    (comp as any).cyberscan.getMySubscription = vi.fn(() => of(null));
    comp.ngOnInit();
    expect(comp.planName).toBe('');
  });

  it('laisse planName vide si l’abonnement n’a pas de plan', () => {
    const comp = make();
    (comp as any).cyberscan.getMySubscription = vi.fn(() => of({ plan: null }));
    comp.ngOnInit();
    expect(comp.planName).toBe('');
  });

  it('laisse planName vide si display_name est absent', () => {
    const comp = make();
    (comp as any).cyberscan.getMySubscription = vi.fn(() => of({ plan: {} }));
    comp.ngOnInit();
    expect(comp.planName).toBe('');
  });

  it('définit le titre de la page', () => {
    const comp = make();
    comp.ngOnInit();
    expect((comp as any).title.setTitle).toHaveBeenCalled();
  });

  it('appelle getMySubscription une fois', () => {
    const comp = make();
    comp.ngOnInit();
    expect((comp as any).cyberscan.getMySubscription).toHaveBeenCalledTimes(1);
  });
});
