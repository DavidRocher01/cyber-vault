import { describe, it, expect } from 'vitest';
import { signal } from '@angular/core';
import { AwarenessOrgDetailComponent } from './awareness-org-detail.component';
import type { OrgAdminDashboard } from '../services/awareness.service';

function make(): AwarenessOrgDetailComponent {
  const comp = Object.create(AwarenessOrgDetailComponent.prototype) as AwarenessOrgDetailComponent;
  (comp as any).orgId = signal(0);
  (comp as any).org = signal(null);
  (comp as any).learners = signal([]);
  (comp as any).dashboard = signal(null);
  (comp as any).nis2 = signal(null);
  (comp as any).csvResult = signal(null);
  (comp as any).loading = signal(false);
  (comp as any).loadingDash = signal(false);
  (comp as any).loadingNis2 = signal(false);
  (comp as any).addingLearner = signal(false);
  (comp as any).importingCsv = signal(false);
  (comp as any).activeTab = signal('learners');
  (comp as any).Math = Math;
  return comp;
}

describe('AwarenessOrgDetailComponent — completionColor()', () => {
  it('text-green-400 si taux >= 80', () =>
    expect(make().completionColor(80)).toBe('text-green-400'));
  it('text-yellow-400 si taux entre 50 et 79', () =>
    expect(make().completionColor(50)).toBe('text-yellow-400'));
  it('text-red-400 si taux < 50', () => expect(make().completionColor(0)).toBe('text-red-400'));
});

describe('AwarenessOrgDetailComponent — completionBarColor()', () => {
  it('bg-green-500 si taux >= 80', () =>
    expect(make().completionBarColor(80)).toBe('bg-green-500'));
  it('bg-yellow-500 si taux entre 50 et 79', () =>
    expect(make().completionBarColor(60)).toBe('bg-yellow-500'));
  it('bg-red-500 si taux < 50', () => expect(make().completionBarColor(10)).toBe('bg-red-500'));
});

describe('AwarenessOrgDetailComponent — nis2ScoreColor()', () => {
  it('text-green-400 si score >= 80', () =>
    expect(make().nis2ScoreColor(80)).toBe('text-green-400'));
  it('text-yellow-400 si score entre 50 et 79', () =>
    expect(make().nis2ScoreColor(50)).toBe('text-yellow-400'));
  it('text-red-400 si score < 50', () => expect(make().nis2ScoreColor(49)).toBe('text-red-400'));
});

describe('AwarenessOrgDetailComponent — nis2GaugeColor()', () => {
  it('vert (#4ade80) si score >= 80', () => expect(make().nis2GaugeColor(90)).toBe('#4ade80'));
  it('jaune (#facc15) si score entre 50 et 79', () =>
    expect(make().nis2GaugeColor(60)).toBe('#facc15'));
  it('rouge (#f87171) si score < 50', () => expect(make().nis2GaugeColor(20)).toBe('#f87171'));
});

describe('AwarenessOrgDetailComponent — nis2StatusClass()', () => {
  it('contient green pour green', () => expect(make().nis2StatusClass('green')).toContain('green'));
  it('contient yellow pour yellow', () =>
    expect(make().nis2StatusClass('yellow')).toContain('yellow'));
  it('contient red pour red', () => expect(make().nis2StatusClass('red')).toContain('red'));
});

describe('AwarenessOrgDetailComponent — nis2BarColor()', () => {
  it('bg-green-500 pour green', () => expect(make().nis2BarColor('green')).toBe('bg-green-500'));
  it('bg-yellow-500 pour yellow', () =>
    expect(make().nis2BarColor('yellow')).toBe('bg-yellow-500'));
  it('bg-red-500 pour red', () => expect(make().nis2BarColor('red')).toBe('bg-red-500'));
});

describe('AwarenessOrgDetailComponent — funnelStats()', () => {
  it('retourne 4 statistiques avec les bonnes valeurs', () => {
    const comp = make();
    const engagement = {
      total_learners: 20,
      enrolled_learners: 15,
      active_learners: 10,
      completed_learners: 5,
    };
    (comp as any).dashboard.set({
      engagement,
      programs: [],
      at_risk_learners: [],
    } as unknown as OrgAdminDashboard);
    const stats = comp.funnelStats();
    expect(stats).toHaveLength(4);
    expect(stats[0].value).toBe(20);
    expect(stats[1].value).toBe(15);
    expect(stats[2].value).toBe(10);
    expect(stats[3].value).toBe(5);
  });

  it('associe les bonnes couleurs aux étapes', () => {
    const comp = make();
    (comp as any).dashboard.set({
      engagement: {
        total_learners: 1,
        enrolled_learners: 1,
        active_learners: 1,
        completed_learners: 1,
      },
      programs: [],
      at_risk_learners: [],
    } as unknown as OrgAdminDashboard);
    const stats = comp.funnelStats();
    expect(stats[0].color).toBe('text-white');
    expect(stats[1].color).toContain('blue');
    expect(stats[2].color).toContain('yellow');
    expect(stats[3].color).toContain('green');
  });
});
