import { describe, it, expect } from 'vitest';
import { signal } from '@angular/core';
import { AdminDashboardComponent } from './admin-dashboard.component';

function make(): AdminDashboardComponent {
  const comp = Object.create(AdminDashboardComponent.prototype) as AdminDashboardComponent;
  (comp as any).stats = signal<any>(null);
  (comp as any).loading = signal(true);
  return comp;
}

describe('AdminDashboardComponent — maxWeekValue()', () => {
  it('retourne 1 si stats null', () => {
    expect(make().maxWeekValue()).toBe(1);
  });
  it('retourne 1 si weekly_activity vide', () => {
    const comp = make();
    (comp as any).stats.set({ weekly_activity: [] });
    expect(comp.maxWeekValue()).toBe(1);
  });
  it('retourne le max des users et scans', () => {
    const comp = make();
    (comp as any).stats.set({
      weekly_activity: [
        { users: 10, scans: 5 },
        { users: 3, scans: 20 },
      ],
    });
    expect(comp.maxWeekValue()).toBe(20);
  });
  it('retourne au moins 1 même si toutes les valeurs sont 0', () => {
    const comp = make();
    (comp as any).stats.set({ weekly_activity: [{ users: 0, scans: 0 }] });
    expect(comp.maxWeekValue()).toBe(1);
  });
});

describe('AdminDashboardComponent — maxRevenue()', () => {
  it('retourne 1 si stats null', () => {
    expect(make().maxRevenue()).toBe(1);
  });
  it('retourne le max des revenus mensuels', () => {
    const comp = make();
    (comp as any).stats.set({
      revenue_per_month: [{ cents: 5000 }, { cents: 15000 }, { cents: 8000 }],
    });
    expect(comp.maxRevenue()).toBe(15000);
  });
});

describe('AdminDashboardComponent — totalRevenue()', () => {
  it('retourne 0 si stats null', () => {
    expect(make().totalRevenue()).toBe(0);
  });
  it('somme tous les revenus mensuels', () => {
    const comp = make();
    (comp as any).stats.set({
      revenue_per_month: [{ cents: 5000 }, { cents: 3000 }, { cents: 2000 }],
    });
    expect(comp.totalRevenue()).toBe(10000);
  });
});

describe('AdminDashboardComponent — barHeight()', () => {
  it('retourne 100 si value = max', () => expect(make().barHeight(50, 50)).toBe(100));
  it('retourne 50 pour moitié du max', () => expect(make().barHeight(25, 50)).toBe(50));
  it('retourne 0 si value = 0', () => expect(make().barHeight(0, 100)).toBe(0));
  it('arrondit à l\'entier', () => expect(make().barHeight(1, 3)).toBe(33));
});

describe('AdminDashboardComponent — formatEur()', () => {
  it('contient € et le montant', () => {
    const result = make().formatEur(100000);
    expect(result).toContain('1');
    expect(result).toContain('€');
  });
  it('formate 0', () => {
    expect(make().formatEur(0)).toContain('€');
  });
});

describe('AdminDashboardComponent — needLabel()', () => {
  it('Audit Flash pour audit-flash', () => expect(make().needLabel('audit-flash')).toBe('Audit Flash'));
  it('App-Check pour audit-app', () => expect(make().needLabel('audit-app')).toBe('App-Check'));
  it('Pentest pour pentest', () => expect(make().needLabel('pentest')).toBe('Pentest'));
  it('Abonnement pour abonnement', () => expect(make().needLabel('abonnement')).toBe('Abonnement'));
  it('Autre pour autre', () => expect(make().needLabel('autre')).toBe('Autre'));
  it('valeur brute pour type inconnu', () => expect(make().needLabel('autre-type')).toBe('autre-type'));
});

describe('AdminDashboardComponent — formatDate()', () => {
  it('contient le jour', () => expect(make().formatDate('2024-04-10T15:30:00Z')).toContain('10'));
});
