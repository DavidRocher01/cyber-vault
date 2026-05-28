import { describe, it, expect } from 'vitest';
import { signal } from '@angular/core';
import { QuizComponent } from './quiz.component';
import type { QuizQuestion } from '../services/quiz.service';

function makeQ(id: number, category = 'cat'): QuizQuestion {
  return {
    id,
    text: `Question ${id}`,
    category,
    options: [{ id: 'a', text: 'A' }, { id: 'b', text: 'B' }],
  };
}

function make(): QuizComponent {
  const comp = Object.create(QuizComponent.prototype) as QuizComponent;
  (comp as any).questions = signal<QuizQuestion[]>([]);
  (comp as any).loading = signal(true);
  (comp as any).step = signal<'intro' | 'quiz' | 'email' | 'result'>('intro');
  (comp as any).currentIndex = signal(0);
  (comp as any).answers = signal<Record<number, string>>({});
  (comp as any).submitting = signal(false);
  (comp as any).result = signal(null);
  (comp as any).emailForm = { reset: () => {} };
  return comp;
}

describe('QuizComponent — currentQuestion', () => {
  it('retourne null si pas de questions', () => {
    expect(make().currentQuestion).toBeNull();
  });
  it('retourne la première question à l\'index 0', () => {
    const comp = make();
    (comp as any).questions.set([makeQ(1), makeQ(2)]);
    expect(comp.currentQuestion?.id).toBe(1);
  });
  it('retourne la question à l\'index courant', () => {
    const comp = make();
    (comp as any).questions.set([makeQ(1), makeQ(2)]);
    (comp as any).currentIndex.set(1);
    expect(comp.currentQuestion?.id).toBe(2);
  });
  it('retourne null si index hors limites', () => {
    const comp = make();
    (comp as any).questions.set([makeQ(1)]);
    (comp as any).currentIndex.set(10);
    expect(comp.currentQuestion).toBeNull();
  });
});

describe('QuizComponent — progress', () => {
  it('retourne 0 si pas de questions', () => {
    expect(make().progress).toBe(0);
  });
  it('retourne 0 au début', () => {
    const comp = make();
    (comp as any).questions.set([makeQ(1), makeQ(2), makeQ(3), makeQ(4)]);
    expect(comp.progress).toBe(0);
  });
  it('retourne 50 à la moitié', () => {
    const comp = make();
    (comp as any).questions.set([makeQ(1), makeQ(2)]);
    (comp as any).currentIndex.set(1);
    expect(comp.progress).toBe(50);
  });
  it('retourne 25 au premier quart', () => {
    const comp = make();
    (comp as any).questions.set([makeQ(1), makeQ(2), makeQ(3), makeQ(4)]);
    (comp as any).currentIndex.set(1);
    expect(comp.progress).toBe(25);
  });
});

describe('QuizComponent — allAnswered', () => {
  it('retourne false si aucune réponse', () => {
    const comp = make();
    (comp as any).questions.set([makeQ(1), makeQ(2)]);
    expect(comp.allAnswered).toBe(false);
  });
  it('retourne true si toutes les questions ont une réponse', () => {
    const comp = make();
    (comp as any).questions.set([makeQ(1), makeQ(2)]);
    (comp as any).answers.set({ 1: 'a', 2: 'b' });
    expect(comp.allAnswered).toBe(true);
  });
  it('retourne false si une réponse manque', () => {
    const comp = make();
    (comp as any).questions.set([makeQ(1), makeQ(2)]);
    (comp as any).answers.set({ 1: 'a' });
    expect(comp.allAnswered).toBe(false);
  });
  it('retourne true si pas de questions', () => {
    expect(make().allAnswered).toBe(true);
  });
});

describe('QuizComponent — selectAnswer()', () => {
  it('enregistre la réponse', () => {
    const comp = make();
    comp.selectAnswer(1, 'a');
    expect((comp as any).answers()[1]).toBe('a');
  });
  it('écrase une réponse existante', () => {
    const comp = make();
    comp.selectAnswer(1, 'a');
    comp.selectAnswer(1, 'b');
    expect((comp as any).answers()[1]).toBe('b');
  });
  it('enregistre plusieurs réponses', () => {
    const comp = make();
    comp.selectAnswer(1, 'a');
    comp.selectAnswer(2, 'b');
    expect((comp as any).answers()[1]).toBe('a');
    expect((comp as any).answers()[2]).toBe('b');
  });
});

describe('QuizComponent — next()', () => {
  it('avance l\'index', () => {
    const comp = make();
    (comp as any).questions.set([makeQ(1), makeQ(2)]);
    comp.next();
    expect((comp as any).currentIndex()).toBe(1);
  });
  it('ne dépasse pas le dernier index', () => {
    const comp = make();
    (comp as any).questions.set([makeQ(1)]);
    comp.next();
    expect((comp as any).currentIndex()).toBe(0);
  });
});

describe('QuizComponent — prev()', () => {
  it('recule l\'index', () => {
    const comp = make();
    (comp as any).questions.set([makeQ(1), makeQ(2)]);
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

describe('QuizComponent — goToQuestion()', () => {
  it('navigue directement à l\'index donné', () => {
    const comp = make();
    comp.goToQuestion(5);
    expect((comp as any).currentIndex()).toBe(5);
  });
  it('navigue à 0', () => {
    const comp = make();
    (comp as any).currentIndex.set(3);
    comp.goToQuestion(0);
    expect((comp as any).currentIndex()).toBe(0);
  });
});

describe('QuizComponent — restart()', () => {
  it('remet les réponses à vide', () => {
    const comp = make();
    (comp as any).answers.set({ 1: 'a', 2: 'b' });
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
    (comp as any).result.set({ score: 10 } as any);
    comp.restart();
    expect((comp as any).result()).toBeNull();
  });
});

describe('QuizComponent — categoryColor()', () => {
  it('bg-green-500 si ≥ 80', () => expect(make().categoryColor(80)).toBe('bg-green-500'));
  it('bg-green-500 si 100', () => expect(make().categoryColor(100)).toBe('bg-green-500'));
  it('bg-yellow-500 si entre 60 et 79', () => expect(make().categoryColor(70)).toBe('bg-yellow-500'));
  it('bg-yellow-500 si = 60', () => expect(make().categoryColor(60)).toBe('bg-yellow-500'));
  it('bg-orange-500 si entre 35 et 59', () => expect(make().categoryColor(50)).toBe('bg-orange-500'));
  it('bg-orange-500 si = 35', () => expect(make().categoryColor(35)).toBe('bg-orange-500'));
  it('bg-red-500 si < 35', () => expect(make().categoryColor(20)).toBe('bg-red-500'));
  it('bg-red-500 si 0', () => expect(make().categoryColor(0)).toBe('bg-red-500'));
});

describe('QuizComponent — categoryTextColor()', () => {
  it('text-green-400 si ≥ 80', () => expect(make().categoryTextColor(80)).toBe('text-green-400'));
  it('text-yellow-400 si entre 60 et 79', () => expect(make().categoryTextColor(70)).toBe('text-yellow-400'));
  it('text-orange-400 si entre 35 et 59', () => expect(make().categoryTextColor(50)).toBe('text-orange-400'));
  it('text-red-400 si < 35', () => expect(make().categoryTextColor(20)).toBe('text-red-400'));
  it('text-green-400 si = 80', () => expect(make().categoryTextColor(80)).toBe('text-green-400'));
  it('text-yellow-400 si = 60', () => expect(make().categoryTextColor(60)).toBe('text-yellow-400'));
  it('text-orange-400 si = 35', () => expect(make().categoryTextColor(35)).toBe('text-orange-400'));
});
