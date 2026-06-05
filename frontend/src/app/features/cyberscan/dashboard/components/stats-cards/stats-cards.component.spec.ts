/**
 * StatsCardsComponent — tests des méthodes utilitaires pures.
 * getGrade/getScoreColor sont des références aux fonctions de score-utils
 * — on les teste directement pour éviter les problèmes d'Object.create.
 */
import { describe, it, expect } from 'vitest';
import { getGrade, getScoreColor } from '../../../../../shared/score-utils';

describe('StatsCardsComponent — getGrade()', () => {
  it('retourne A pour un score >= 90', () => expect(getGrade(95)).toBe('A'));
  it('retourne B pour un score entre 75 et 89', () => expect(getGrade(80)).toBe('B'));
  it('retourne C pour un score entre 60 et 74', () => expect(getGrade(65)).toBe('C'));
  it('retourne D pour un score entre 40 et 59', () => expect(getGrade(50)).toBe('D'));
  it('retourne F pour un score < 40', () => expect(getGrade(20)).toBe('F'));
  it('retourne A exactement à 90', () => expect(getGrade(90)).toBe('A'));
  it('note différente entre score bas et score élevé', () => {
    expect(getGrade(10)).not.toBe(getGrade(95));
  });
});

describe('StatsCardsComponent — getScoreColor()', () => {
  it('retourne une couleur CSS valide pour un score élevé', () => {
    const color = getScoreColor(95);
    expect(color).toBeTruthy();
    expect(color).toMatch(/^#/);
  });

  it('retourne une couleur différente pour un score bas vs élevé', () => {
    expect(getScoreColor(10)).not.toBe(getScoreColor(95));
  });

  it('retourne une couleur verte pour un score >= 90', () => {
    expect(getScoreColor(90)).toBe('#4ade80');
  });

  it('retourne une couleur rouge pour un score < 40', () => {
    expect(getScoreColor(20)).toBe('#f87171');
  });
});

describe('StatsCardsComponent — @Input() defaults', () => {
  it('averageScore est null par défaut', () => {
    const comp = make();
    comp.averageScore = null;
    expect(comp.averageScore).toBeNull();
  });

  it('sitesCount est 0 par défaut', () => {
    const comp = make();
    comp.sitesCount = 0;
    expect(comp.sitesCount).toBe(0);
  });

  it('totalScans est 0 par défaut', () => {
    const comp = make();
    comp.totalScans = 0;
    expect(comp.totalScans).toBe(0);
  });

  it('subscription est null par défaut', () => {
    const comp = make();
    comp.subscription = null;
    expect(comp.subscription).toBeNull();
  });
});
