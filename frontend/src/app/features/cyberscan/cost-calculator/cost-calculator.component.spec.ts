import { describe, it, expect } from 'vitest';
import { signal } from '@angular/core';
import { CostCalculatorComponent } from './cost-calculator.component';
import type { CalcQuestion } from '../services/cost-calc.service';

function makeQ(key: string, id = 1): CalcQuestion {
  return { id, key, text: `Question ${key}`, options: [{ id: 'a', text: 'A' }, { id: 'b', text: 'B' }] };
}

function make(): CostCalculatorComponent {
  const comp = Object.create(CostCalculatorComponent.prototype) as CostCalculatorComponent;
  (comp as any).questions = signal<CalcQuestion[]>([]);
  (comp as any).loading = signal(true);
  (comp as any).step = signal<'intro' | 'wizard' | 'email' | 'result'>('intro');
  (comp as any).currentIndex = signal(0);
  (comp as any).answers = signal<Record<string, string>>({});
  (comp as any).submitting = signal(false);
  (comp as any).result = signal(null);
  (comp as any).emailForm = { reset: () => {} };
  return comp;
}

describe('CostCalculatorComponent — currentQuestion', () => {
  it('retourne null si pas de questions', () => {
    expect(make().currentQuestion).toBeNull();
  });
  it('retourne la première question à l\'index 0', () => {
    const comp = make();
    (comp as any).questions.set([makeQ('q1'), makeQ('q2')]);
    expect(comp.currentQuestion?.key).toBe('q1');
  });
  it('retourne la question à l\'index courant', () => {
    const comp = make();
    (comp as any).questions.set([makeQ('q1'), makeQ('q2')]);
    (comp as any).currentIndex.set(1);
    expect(comp.currentQuestion?.key).toBe('q2');
  });
  it('retourne null si index hors limites', () => {
    const comp = make();
    (comp as any).questions.set([makeQ('q1')]);
    (comp as any).currentIndex.set(5);
    expect(comp.currentQuestion).toBeNull();
  });
});

describe('CostCalculatorComponent — progress', () => {
  it('retourne 0 si pas de questions', () => {
    expect(make().progress).toBe(0);
  });
  it('retourne 0 à l\'index 0', () => {
    const comp = make();
    (comp as any).questions.set([makeQ('q1'), makeQ('q2'), makeQ('q3'), makeQ('q4')]);
    expect(comp.progress).toBe(0);
  });
  it('retourne 50 à la moitié', () => {
    const comp = make();
    (comp as any).questions.set([makeQ('q1'), makeQ('q2')]);
    (comp as any).currentIndex.set(1);
    expect(comp.progress).toBe(50);
  });
  it('retourne 75 à 3/4 du parcours', () => {
    const comp = make();
    (comp as any).questions.set([makeQ('q1'), makeQ('q2'), makeQ('q3'), makeQ('q4')]);
    (comp as any).currentIndex.set(3);
    expect(comp.progress).toBe(75);
  });
});

describe('CostCalculatorComponent — allAnswered', () => {
  it('retourne false si aucune réponse', () => {
    const comp = make();
    (comp as any).questions.set([makeQ('q1')]);
    expect(comp.allAnswered).toBe(false);
  });
  it('retourne true si toutes les questions ont une réponse', () => {
    const comp = make();
    (comp as any).questions.set([makeQ('q1'), makeQ('q2')]);
    (comp as any).answers.set({ q1: 'a', q2: 'b' });
    expect(comp.allAnswered).toBe(true);
  });
  it('retourne false si une réponse manque', () => {
    const comp = make();
    (comp as any).questions.set([makeQ('q1'), makeQ('q2')]);
    (comp as any).answers.set({ q1: 'a' });
    expect(comp.allAnswered).toBe(false);
  });
  it('retourne true si aucune question', () => {
    expect(make().allAnswered).toBe(true);
  });
});

describe('CostCalculatorComponent — selectAnswer()', () => {
  it('enregistre la réponse', () => {
    const comp = make();
    comp.selectAnswer('q1', 'a');
    expect((comp as any).answers()['q1']).toBe('a');
  });
  it('écrase une réponse existante', () => {
    const comp = make();
    comp.selectAnswer('q1', 'a');
    comp.selectAnswer('q1', 'b');
    expect((comp as any).answers()['q1']).toBe('b');
  });
  it('enregistre plusieurs réponses indépendantes', () => {
    const comp = make();
    comp.selectAnswer('q1', 'a');
    comp.selectAnswer('q2', 'b');
    expect((comp as any).answers()['q1']).toBe('a');
    expect((comp as any).answers()['q2']).toBe('b');
  });
});

describe('CostCalculatorComponent — next()', () => {
  it('avance l\'index', () => {
    const comp = make();
    (comp as any).questions.set([makeQ('q1'), makeQ('q2')]);
    comp.next();
    expect((comp as any).currentIndex()).toBe(1);
  });
  it('ne dépasse pas le dernier index', () => {
    const comp = make();
    (comp as any).questions.set([makeQ('q1')]);
    comp.next();
    expect((comp as any).currentIndex()).toBe(0);
  });
  it('avance plusieurs fois', () => {
    const comp = make();
    (comp as any).questions.set([makeQ('q1'), makeQ('q2'), makeQ('q3')]);
    comp.next();
    comp.next();
    expect((comp as any).currentIndex()).toBe(2);
  });
});

describe('CostCalculatorComponent — prev()', () => {
  it('recule l\'index', () => {
    const comp = make();
    (comp as any).questions.set([makeQ('q1'), makeQ('q2')]);
    (comp as any).currentIndex.set(1);
    comp.prev();
    expect((comp as any).currentIndex()).toBe(0);
  });
  it('ne passe pas en dessous de 0', () => {
    const comp = make();
    comp.prev();
    expect((comp as any).currentIndex()).toBe(0);
  });
});

describe('CostCalculatorComponent — restart()', () => {
  it('remet les réponses à vide', () => {
    const comp = make();
    (comp as any).answers.set({ q1: 'a' });
    comp.restart();
    expect((comp as any).answers()).toEqual({});
  });
  it('remet l\'index à 0', () => {
    const comp = make();
    (comp as any).currentIndex.set(3);
    comp.restart();
    expect((comp as any).currentIndex()).toBe(0);
  });
  it('remet l\'étape à intro', () => {
    const comp = make();
    (comp as any).step.set('result');
    comp.restart();
    expect((comp as any).step()).toBe('intro');
  });
  it('vide le résultat', () => {
    const comp = make();
    (comp as any).result.set({ estimated_eur: 5000 } as any);
    comp.restart();
    expect((comp as any).result()).toBeNull();
  });
});

describe('CostCalculatorComponent — formatEur()', () => {
  it('contient € et le montant formaté', () => {
    const result = make().formatEur(50000);
    expect(result).toContain('50');
    expect(result).toContain('€');
  });
  it('formate 0', () => {
    expect(make().formatEur(0)).toContain('€');
  });
  it('formate un grand nombre', () => {
    const result = make().formatEur(1000000);
    expect(result).toContain('1');
    expect(result).toContain('€');
  });
});

describe('CostCalculatorComponent — breakdownColor()', () => {
  it('bg-red-500 si ≥ 30', () => expect(make().breakdownColor(30)).toBe('bg-red-500'));
  it('bg-red-500 si > 30', () => expect(make().breakdownColor(50)).toBe('bg-red-500'));
  it('bg-orange-500 si entre 20 et 29', () => expect(make().breakdownColor(20)).toBe('bg-orange-500'));
  it('bg-orange-500 si 25', () => expect(make().breakdownColor(25)).toBe('bg-orange-500'));
  it('bg-yellow-500 si < 20', () => expect(make().breakdownColor(10)).toBe('bg-yellow-500'));
  it('bg-yellow-500 si 0', () => expect(make().breakdownColor(0)).toBe('bg-yellow-500'));
});
