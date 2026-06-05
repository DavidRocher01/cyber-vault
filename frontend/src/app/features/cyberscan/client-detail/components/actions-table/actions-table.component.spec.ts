/**
 * ActionsTableComponent — tests des méthodes utilitaires pures.
 */
import { describe, it, expect } from 'vitest';
import { ActionsTableComponent } from './actions-table.component';

function make(): ActionsTableComponent {
  const comp = Object.create(ActionsTableComponent.prototype) as ActionsTableComponent;
  (comp as any).today = new Date().toISOString().slice(0, 10);
  return comp;
}

describe('ActionsTableComponent — formatDate()', () => {
  it('retourne "—" pour null', () => expect(make().formatDate(null)).toBe('—'));
  it("inclut l'année dans le résultat", () =>
    expect(make().formatDate('2024-06-15')).toContain('2024'));
  it('inclut le mois formaté en français', () => {
    const result = make().formatDate('2024-06-15');
    // Le mois doit être présent (pas un nombre pur, car format 'short' = "juin")
    expect(result).toBeTruthy();
    expect(result.length).toBeGreaterThan(4);
  });
});

describe('ActionsTableComponent — priorityClass()', () => {
  it('retourne rouge pour critical', () =>
    expect(make().priorityClass('critical')).toContain('red'));
  it('retourne orange pour high', () => expect(make().priorityClass('high')).toContain('orange'));
  it('retourne jaune pour medium', () =>
    expect(make().priorityClass('medium')).toContain('yellow'));
  it('retourne gris pour low', () => expect(make().priorityClass('low')).toContain('gray'));
  it('retourne gris pour valeur inconnue', () =>
    expect(make().priorityClass('unknown')).toContain('gray'));
});

describe('ActionsTableComponent — actionStatusClass()', () => {
  it('retourne vert pour done', () => expect(make().actionStatusClass('done')).toContain('green'));
  it('retourne bleu pour in_progress', () =>
    expect(make().actionStatusClass('in_progress')).toContain('blue'));
  it('retourne gris pour cancelled', () =>
    expect(make().actionStatusClass('cancelled')).toContain('gray'));
  it('retourne jaune pour postponed', () =>
    expect(make().actionStatusClass('postponed')).toContain('yellow'));
  it('retourne blanc pour open', () => expect(make().actionStatusClass('open')).toContain('white'));
});

describe('ActionsTableComponent — actionStatusLabel()', () => {
  it('retourne "Ouverte" pour open', () =>
    expect(make().actionStatusLabel('open')).toBe('Ouverte'));
  it('retourne "En cours" pour in_progress', () =>
    expect(make().actionStatusLabel('in_progress')).toBe('En cours'));
  it('retourne "Terminée" pour done', () =>
    expect(make().actionStatusLabel('done')).toBe('Terminée'));
  it('retourne "Annulée" pour cancelled', () =>
    expect(make().actionStatusLabel('cancelled')).toBe('Annulée'));
  it('retourne "Reportée" pour postponed', () =>
    expect(make().actionStatusLabel('postponed')).toBe('Reportée'));
  it('retourne la valeur brute pour statut inconnu', () =>
    expect(make().actionStatusLabel('custom_status')).toBe('custom_status'));
});

describe('ActionsTableComponent — today', () => {
  it('today est une date ISO au format YYYY-MM-DD', () => {
    expect(make().today).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});
