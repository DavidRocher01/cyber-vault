/**
 * SitesGridComponent — tests des méthodes utilitaires pures.
 */
import { describe, it, expect } from 'vitest';
import { SitesGridComponent } from './sites-grid.component';

function make(): SitesGridComponent {
  const comp = Object.create(SitesGridComponent.prototype) as SitesGridComponent;
  comp.lastScores = {};
  comp.trends = {};
  comp.sslDays = {};
  comp.triggeringScansMap = {};
  comp.activeScansMap = {};
  comp.lastScanStatuses = {};
  return comp;
}

describe('SitesGridComponent — getLastScore()', () => {
  it('retourne null si le site est absent de la map', () => {
    expect(make().getLastScore(99)).toBeNull();
  });

  it('retourne le score si présent', () => {
    const comp = make();
    comp.lastScores = { 1: 78 };
    expect(comp.getLastScore(1)).toBe(78);
  });

  it('retourne null si la valeur est null dans la map', () => {
    const comp = make();
    comp.lastScores = { 1: null };
    expect(comp.getLastScore(1)).toBeNull();
  });
});

describe('SitesGridComponent — getTrend()', () => {
  it('retourne null si absent', () => expect(make().getTrend(5)).toBeNull());

  it('retourne la valeur de tendance positive', () => {
    const comp = make();
    comp.trends = { 2: 5 };
    expect(comp.getTrend(2)).toBe(5);
  });

  it('retourne la valeur de tendance négative', () => {
    const comp = make();
    comp.trends = { 2: -3 };
    expect(comp.getTrend(2)).toBe(-3);
  });
});

describe('SitesGridComponent — getSslDaysRemaining()', () => {
  it('retourne null si absent', () => expect(make().getSslDaysRemaining(1)).toBeNull());

  it('retourne le nombre de jours restants', () => {
    const comp = make();
    comp.sslDays = { 1: 14 };
    expect(comp.getSslDaysRemaining(1)).toBe(14);
  });
});

describe('SitesGridComponent — isTriggering()', () => {
  it('retourne false si absent de la map', () => expect(make().isTriggering(1)).toBe(false));

  it('retourne true si le scan est en cours de déclenchement', () => {
    const comp = make();
    comp.triggeringScansMap = { 1: true };
    expect(comp.isTriggering(1)).toBe(true);
  });
});

describe('SitesGridComponent — hasActiveScans()', () => {
  it('retourne false si absent', () => expect(make().hasActiveScans(1)).toBe(false));

  it('retourne true si des scans sont actifs', () => {
    const comp = make();
    comp.activeScansMap = { 3: true };
    expect(comp.hasActiveScans(3)).toBe(true);
  });
});

describe('SitesGridComponent — getBadge()', () => {
  it('retourne le badge "En cours" si un scan est actif', () => {
    const comp = make();
    comp.activeScansMap = { 1: true };
    const badge = comp.getBadge(1);
    expect(badge.label).toBe('En cours...');
    expect(badge.icon).toBe('sync');
  });

  it('retourne le badge OK pour statut OK', () => {
    const comp = make();
    comp.lastScanStatuses = { 1: 'OK' };
    const badge = comp.getBadge(1);
    expect(badge.label).toBe('OK');
    expect(badge.icon).toBe('verified_user');
  });

  it('retourne le badge WARNING pour statut WARNING', () => {
    const comp = make();
    comp.lastScanStatuses = { 1: 'WARNING' };
    const badge = comp.getBadge(1);
    expect(badge.label).toBe('WARNING');
    expect(badge.icon).toBe('warning');
  });

  it('retourne le badge CRITICAL pour statut CRITICAL', () => {
    const comp = make();
    comp.lastScanStatuses = { 1: 'CRITICAL' };
    const badge = comp.getBadge(1);
    expect(badge.label).toBe('CRITICAL');
    expect(badge.icon).toBe('gpp_bad');
  });

  it('retourne le badge "Aucun scan" par défaut', () => {
    const comp = make();
    const badge = comp.getBadge(99);
    expect(badge.label).toBe('Aucun scan');
    expect(badge.icon).toBe('help_outline');
  });

  it('badge actif a priorité sur le statut', () => {
    const comp = make();
    comp.activeScansMap = { 1: true };
    comp.lastScanStatuses = { 1: 'OK' };
    expect(comp.getBadge(1).label).toBe('En cours...');
  });
});
