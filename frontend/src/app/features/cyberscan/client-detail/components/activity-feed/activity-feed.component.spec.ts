/**
 * ActivityFeedComponent — tests des méthodes utilitaires pures.
 */
import { describe, it, expect } from 'vitest';
import { ActivityFeedComponent } from './activity-feed.component';

function make(): ActivityFeedComponent {
  return Object.create(ActivityFeedComponent.prototype) as ActivityFeedComponent;
}

describe('ActivityFeedComponent — activityLabel()', () => {
  it('retourne le libellé traduit pour view_client', () =>
    expect(make().activityLabel('view_client')).toBe('Consultation fiche client'));
  it('retourne le libellé traduit pour generate_report', () =>
    expect(make().activityLabel('generate_report')).toBe('Génération de rapport'));
  it('retourne le libellé traduit pour create_action', () =>
    expect(make().activityLabel('create_action')).toBe("Création d'une action"));
  it('retourne le libellé traduit pour update_action', () =>
    expect(make().activityLabel('update_action')).toBe("Mise à jour d'une action"));
  it('retourne le libellé traduit pour create_visit', () =>
    expect(make().activityLabel('create_visit')).toBe("Planification d'une visite"));
  it('retourne la valeur brute pour un type inconnu', () =>
    expect(make().activityLabel('unknown_action')).toBe('unknown_action'));
  it('retourne le libellé traduit pour send_deliverable', () =>
    expect(make().activityLabel('send_deliverable')).toBe("Envoi d'un livrable"));
  it('retourne le libellé traduit pour view_sites', () =>
    expect(make().activityLabel('view_sites')).toBe('Consultation des sites'));
});

describe('ActivityFeedComponent — formatDateTime()', () => {
  it("inclut l'année dans le résultat", () =>
    expect(make().formatDateTime('2024-06-15T10:30:00Z')).toContain('2024'));
  it("inclut l'heure dans le résultat", () => {
    const result = make().formatDateTime('2024-06-15T10:30:00Z');
    expect(result).toMatch(/\d+:\d+/);
  });
  it('retourne une chaîne non vide', () => {
    expect(make().formatDateTime('2024-01-01T00:00:00Z')).toBeTruthy();
  });
});
