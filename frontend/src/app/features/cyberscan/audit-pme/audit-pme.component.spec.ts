import { describe, it, expect } from 'vitest';
import { AUDIT_OFFERS, AUDIT_SUBSCRIPTIONS, AUDIT_FAQS } from './audit-pme.component';

describe('AUDIT_OFFERS', () => {
  it('contient exactement 3 offres ponctuelles', () => {
    expect(AUDIT_OFFERS.length).toBe(3);
  });

  it('la première offre est Flash à 245€', () => {
    expect(AUDIT_OFFERS[0].name).toBe('Audit Flash');
    expect(AUDIT_OFFERS[0].price).toBe('245');
  });

  it('la deuxième offre est App-Check à 725€, marquée popular', () => {
    expect(AUDIT_OFFERS[1].name).toBe('App-Check');
    expect(AUDIT_OFFERS[1].price).toBe('725');
    expect(AUDIT_OFFERS[1].popular).toBe(true);
  });

  it('la troisième offre est Pentest léger à 1900€', () => {
    expect(AUDIT_OFFERS[2].name).toBe('Pentest léger');
    expect(AUDIT_OFFERS[2].price).toBe('1 900');
  });

  it('chaque offre a au moins 4 features', () => {
    for (const offer of AUDIT_OFFERS) {
      expect(offer.features.length).toBeGreaterThanOrEqual(4);
    }
  });

  it("les offres non popular n'ont pas le champ popular à true", () => {
    expect(AUDIT_OFFERS[0].popular).toBeFalsy();
    expect(AUDIT_OFFERS[2].popular).toBeFalsy();
  });
});

describe('AUDIT_SUBSCRIPTIONS', () => {
  it('contient exactement 3 abonnements', () => {
    expect(AUDIT_SUBSCRIPTIONS.length).toBe(3);
  });

  it("l'abonnement Sentinelle est recommandé (popular) à ~199€", () => {
    const sentinelle = AUDIT_SUBSCRIPTIONS.find(s => s.name === 'Sentinelle');
    expect(sentinelle).toBeDefined();
    expect(sentinelle!.popular).toBe(true);
    expect(sentinelle!.price).toBe('~199');
  });

  it('Vigie est à ~99€/mois', () => {
    expect(AUDIT_SUBSCRIPTIONS[0].price).toBe('~99');
  });

  it('Blindage 360 est à ~499€/mois', () => {
    expect(AUDIT_SUBSCRIPTIONS[2].price).toBe('~499');
  });

  it('chaque abonnement a au moins 2 features', () => {
    for (const sub of AUDIT_SUBSCRIPTIONS) {
      expect(sub.features.length).toBeGreaterThanOrEqual(2);
    }
  });
});

describe('AUDIT_FAQS', () => {
  it('contient au moins 5 questions', () => {
    expect(AUDIT_FAQS.length).toBeGreaterThanOrEqual(5);
  });

  it('chaque FAQ a une question et une réponse non vides', () => {
    for (const faq of AUDIT_FAQS) {
      expect(faq.q.length).toBeGreaterThan(5);
      expect(faq.a.length).toBeGreaterThan(10);
    }
  });
});
