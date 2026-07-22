import { describe, it, expect, beforeEach, vi } from 'vitest';
import { of } from 'rxjs';
import { BillingService } from './billing.service';

const API = '/api/v1';

/**
 * BillingService uses Angular's inject() field initializer.
 * We bypass DI by creating an instance via Object.create and manually
 * assigning the http dependency — same pattern used for constructor injection.
 */
function makeService(httpOverrides: Partial<{ get: any; post: any; put: any; delete: any }> = {}) {
  const http = {
    get: vi.fn().mockReturnValue(of({})),
    post: vi.fn().mockReturnValue(of({})),
    put: vi.fn().mockReturnValue(of({})),
    delete: vi.fn().mockReturnValue(of(null)),
    ...httpOverrides,
  };
  const service = Object.create(BillingService.prototype) as BillingService;
  (service as any).http = http;
  // Reset in-memory caches so each test starts fresh
  (service as any)._plans$ = null;
  (service as any)._subscription$ = null;
  return { service, http };
}

describe('BillingService', () => {
  let service: BillingService;
  let http: any;

  beforeEach(() => {
    ({ service, http } = makeService());
  });

  // ── Plans ──────────────────────────────────────────────────────────────────

  it('getPlans() envoie GET /api/v1/plans', () => {
    http.get.mockReturnValue(of([]));
    service.getPlans().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/plans`);
  });

  it('getPlans() retourne les données du serveur', () => {
    const plans = [{ id: 1, name: 'starter' }];
    http.get.mockReturnValue(of(plans));
    let result: any;
    service.getPlans().subscribe(r => (result = r));
    expect(result).toEqual(plans);
  });

  it('getPlans() émet exactement un appel HTTP', () => {
    http.get.mockReturnValue(of([]));
    service.getPlans().subscribe();
    expect(http.get).toHaveBeenCalledTimes(1);
  });

  // ── Subscriptions ──────────────────────────────────────────────────────────

  it('getMySubscription() envoie GET /api/v1/subscriptions/me', () => {
    service.getMySubscription().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/subscriptions/me`);
  });

  it('createCheckout() envoie POST /api/v1/subscriptions/checkout/:id', () => {
    http.post.mockReturnValue(of({ checkout_url: 'https://stripe.com' }));
    service.createCheckout(3).subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/subscriptions/checkout/3`, {});
  });

  it("createCheckout() retourne l'url de checkout", () => {
    http.post.mockReturnValue(of({ checkout_url: 'https://stripe.com/x' }));
    let result: any;
    service.createCheckout(5).subscribe(r => (result = r));
    expect(result.checkout_url).toBe('https://stripe.com/x');
  });

  it('getBillingPortal() envoie GET /api/v1/subscriptions/portal', () => {
    http.get.mockReturnValue(of({ checkout_url: '/dashboard' }));
    service.getBillingPortal().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/subscriptions/portal`);
  });

  // ── Cache — Plans ──────────────────────────────────────────────────────────

  it("getPlans() ne fait qu'un seul appel HTTP pour deux souscriptions", () => {
    http.get.mockReturnValue(of([]));
    service.getPlans().subscribe();
    service.getPlans().subscribe();
    expect(http.get).toHaveBeenCalledTimes(1);
  });

  it('getPlans() émet la même valeur aux deux abonnés', () => {
    const plans = [{ id: 1, name: 'starter' }];
    http.get.mockReturnValue(of(plans));
    const results: any[] = [];
    service.getPlans().subscribe(r => results.push(r));
    service.getPlans().subscribe(r => results.push(r));
    expect(results).toHaveLength(2);
    expect(results[0]).toEqual(results[1]);
  });

  // ── Cache — Subscription ──────────────────────────────────────────────────

  it("getMySubscription() ne fait qu'un seul appel HTTP pour deux souscriptions", () => {
    http.get.mockReturnValue(of(null));
    service.getMySubscription().subscribe();
    service.getMySubscription().subscribe();
    expect(http.get).toHaveBeenCalledTimes(1);
  });

  it('getMySubscription(refresh=true) force un nouvel appel HTTP', () => {
    http.get.mockReturnValue(of(null));
    service.getMySubscription().subscribe();
    service.getMySubscription(true).subscribe();
    expect(http.get).toHaveBeenCalledTimes(2);
  });

  it('invalidateSubscriptionCache() force un nouvel appel au prochain getMySubscription()', () => {
    http.get.mockReturnValue(of(null));
    service.getMySubscription().subscribe(); // premier appel → HTTP
    service.invalidateSubscriptionCache();
    service.getMySubscription().subscribe(); // après invalidation → nouvel HTTP
    expect(http.get).toHaveBeenCalledTimes(2);
  });

  it("invalidateSubscriptionCache() n'effectue pas d'appel HTTP en lui-même", () => {
    service.invalidateSubscriptionCache();
    expect(http.get).not.toHaveBeenCalled();
    expect(http.post).not.toHaveBeenCalled();
  });
});
