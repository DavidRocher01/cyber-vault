import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, shareReplay } from 'rxjs';

import { Plan, Subscription, CheckoutSession } from './cyberscan.service';

const API = '/api/v1';

/**
 * Domaine facturation / abonnements extrait de CyberscanService (service
 * fourre-tout). Plans, abonnement courant (avec cache), checkout Stripe,
 * portail de facturation, achat de sites supplementaires.
 */
@Injectable({ providedIn: 'root' })
export class BillingService {
  private http = inject(HttpClient);

  private _plans$: Observable<Plan[]> | null = null;
  private _subscription$: Observable<Subscription | null> | null = null;

  getPlans(): Observable<Plan[]> {
    if (!this._plans$) {
      this._plans$ = this.http.get<Plan[]>(`${API}/plans`).pipe(shareReplay(1));
    }
    return this._plans$;
  }

  getMySubscription(refresh = false): Observable<Subscription | null> {
    if (!this._subscription$ || refresh) {
      this._subscription$ = this.http
        .get<Subscription | null>(`${API}/subscriptions/me`)
        .pipe(shareReplay(1));
    }
    return this._subscription$;
  }

  /** Call after checkout / plan change to force subscription reload. */
  invalidateSubscriptionCache(): void {
    this._subscription$ = null;
  }

  createCheckout(planId: number): Observable<CheckoutSession> {
    return this.http.post<CheckoutSession>(`${API}/subscriptions/checkout/${planId}`, {});
  }

  getBillingPortal(): Observable<{ checkout_url: string }> {
    return this.http.get<{ checkout_url: string }>(`${API}/subscriptions/portal`);
  }

  purchaseExtraSites(): Observable<{ checkout_url: string }> {
    return this.http.post<{ checkout_url: string }>(
      `${API}/subscriptions/addons/extra-sites/checkout`,
      {}
    );
  }
}
