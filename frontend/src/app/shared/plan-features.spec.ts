import { describe, it, expect } from 'vitest';
import { formatScanFrequency } from './plan-features';

describe('formatScanFrequency', () => {
  it('0 jour → à la demande (plan gratuit)', () => {
    expect(formatScanFrequency(0)).toBe('Scan à la demande');
  });
  it('valeur négative → à la demande', () => {
    expect(formatScanFrequency(-1)).toBe('Scan à la demande');
  });
  it('1 → quotidienne', () => {
    expect(formatScanFrequency(1)).toBe('Surveillance quotidienne');
  });
  it('7 → hebdomadaire', () => {
    expect(formatScanFrequency(7)).toBe('Surveillance hebdomadaire');
  });
  it('30 → mensuelle', () => {
    expect(formatScanFrequency(30)).toBe('Surveillance mensuelle');
  });
  it('14 → toutes les 2 semaines', () => {
    expect(formatScanFrequency(14)).toBe('Surveillance toutes les 2 semaines');
  });
  it('valeur atypique → repli en jours', () => {
    expect(formatScanFrequency(5)).toBe('Analyse tous les 5 jours');
  });
});
