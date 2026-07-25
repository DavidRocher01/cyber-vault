import { describe, it, expect } from 'vitest';
import { priorityClass, actionStatusClass, actionStatusLabel } from './rssi-action-labels';

describe('rssi-action-labels', () => {
  it('priorityClass mappe chaque priorité connue et retombe sur le défaut', () => {
    expect(priorityClass('critical')).toContain('text-red-400');
    expect(priorityClass('high')).toContain('text-orange-400');
    expect(priorityClass('medium')).toContain('text-yellow-400');
    expect(priorityClass('low')).toContain('text-gray-400');
    expect(priorityClass('inconnu')).toContain('text-gray-400');
  });

  it('actionStatusClass mappe chaque statut connu et retombe sur le défaut', () => {
    expect(actionStatusClass('done')).toContain('text-green-400');
    expect(actionStatusClass('in_progress')).toContain('text-blue-400');
    expect(actionStatusClass('cancelled')).toContain('text-gray-500');
    expect(actionStatusClass('postponed')).toContain('text-yellow-400');
    expect(actionStatusClass('open')).toContain('text-white');
  });

  it('actionStatusLabel traduit les statuts et laisse la valeur brute sinon', () => {
    expect(actionStatusLabel('open')).toBe('Ouverte');
    expect(actionStatusLabel('in_progress')).toBe('En cours');
    expect(actionStatusLabel('done')).toBe('Terminée');
    expect(actionStatusLabel('cancelled')).toBe('Annulée');
    expect(actionStatusLabel('postponed')).toBe('Reportée');
    expect(actionStatusLabel('custom')).toBe('custom');
  });
});
