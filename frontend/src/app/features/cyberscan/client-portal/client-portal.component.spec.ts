import { describe, it, expect } from 'vitest';
import { ClientPortalComponent } from './client-portal.component';
import { PortalAction } from '../services/client-portal.service';

// Helpers purs : testés sans DI (les méthodes vivent sur le prototype).
const c = Object.create(ClientPortalComponent.prototype) as ClientPortalComponent;

describe('ClientPortalComponent — libellés & helpers', () => {
  it('priorityLabel : connu + repli', () => {
    expect(c.priorityLabel('critical')).toBe('Critique');
    expect(c.priorityLabel('low')).toBe('Basse');
    expect(c.priorityLabel('inconnu')).toBe('inconnu');
  });

  it('priorityClass : classe adaptée + repli gris', () => {
    expect(c.priorityClass('high')).toContain('orange');
    expect(c.priorityClass('xxx')).toContain('gray');
  });

  it('actionStatusLabel / actionStatusClass', () => {
    expect(c.actionStatusLabel('done')).toBe('Terminée');
    expect(c.actionStatusLabel('open')).toBe('À faire');
    expect(c.actionStatusClass('done')).toContain('green');
    expect(c.actionStatusClass('xxx')).toBe('text-gray-400');
  });

  it('visitTypeLabel / visitStatus', () => {
    expect(c.visitTypeLabel('quarterly')).toBe('Comité trimestriel');
    expect(c.visitTypeLabel('xxx')).toBe('xxx');
    expect(c.visitStatusLabel('planned')).toBe('Planifiée');
    expect(c.visitStatusClass('done')).toContain('green');
  });

  it('docTypeLabel', () => {
    expect(c.docTypeLabel('rapport')).toBe('Rapport');
    expect(c.docTypeLabel('xxx')).toBe('xxx');
  });

  it('formulaLabel gère null', () => {
    expect(c.formulaLabel('premium')).toBe('Premium');
    expect(c.formulaLabel(null)).toBe('—');
  });

  it('formatDate gère null + date valide', () => {
    expect(c.formatDate(null)).toBe('—');
    expect(c.formatDate('2026-01-15')).toContain('2026');
  });

  it('isDone', () => {
    expect(c.isDone({ status: 'done' } as PortalAction)).toBe(true);
    expect(c.isDone({ status: 'open' } as PortalAction)).toBe(false);
  });
});
