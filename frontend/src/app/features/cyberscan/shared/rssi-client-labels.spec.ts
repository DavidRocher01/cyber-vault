import { describe, it, expect } from 'vitest';
import * as L from './rssi-client-labels';

describe('rssi-client-labels', () => {
  it('docType / formula / clientStatus mappent + fallback', () => {
    expect(L.docTypeLabel('rapport')).toBe('Rapport');
    expect(L.docTypeLabel('???')).toBe('???');
    expect(L.docTypeClass('contrat')).toContain('text-amber-300');
    expect(L.docTypeClass('???')).toContain('text-gray-400');
    expect(L.formulaLabel('premium')).toBe('Premium');
    expect(L.formulaLabel(null)).toBe('—');
    expect(L.formulaClass('excellence')).toContain('text-amber-300');
    expect(L.formulaClass(null)).toContain('text-gray-400');
    expect(L.clientStatusClass('active')).toBe('text-green-300');
    expect(L.clientStatusClass('???')).toBe('text-gray-400');
  });

  it('visit helpers mappent + fallback', () => {
    expect(L.visitStatusClass('cancelled')).toBe('text-red-400');
    expect(L.visitStatusClass('???')).toBe('text-blue-300');
    expect(L.visitStatusLabel('completed')).toBe('Complétée');
    expect(L.visitStatusLabel('???')).toBe('???');
    expect(L.visitTypeLabel('monthly')).toBe('Mensuelle');
    expect(L.visitLocationLabel('onsite')).toBe('Sur site');
    expect(L.visitLocationLabel('remote')).toBe('À distance');
  });

  it('activity + scan status', () => {
    expect(L.activityLabel('view_client')).toBe('Consultation fiche client');
    expect(L.activityLabel('???')).toBe('???');
    expect(L.scanStatusClass('CRITICAL')).toContain('text-red-400');
    expect(L.scanStatusClass(null)).toContain('text-gray-500');
    expect(L.scanStatusLabel('OK')).toBe('OK');
    expect(L.scanStatusLabel(null)).toBe('Aucun scan');
  });
});
