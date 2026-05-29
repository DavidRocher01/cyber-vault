import { describe, it, expect } from 'vitest';
import { signal } from '@angular/core';
import { SensibilisationComponent } from './sensibilisation.component';

type ModuleUiState = {
  open: boolean;
  selected: string | null;
  quizState: 'idle' | 'answered';
  result: any;
  submitting: boolean;
};

function defaultState(overrides: Partial<ModuleUiState> = {}): ModuleUiState {
  return {
    open: false,
    selected: null,
    quizState: 'idle',
    result: null,
    submitting: false,
    ...overrides,
  };
}

function make(): SensibilisationComponent {
  const comp = Object.create(SensibilisationComponent.prototype) as SensibilisationComponent;
  (comp as any).modules = signal<any[]>([]);
  (comp as any).progress = signal(null);
  (comp as any).loading = signal(true);
  (comp as any).uiState = signal<Record<string, ModuleUiState>>({});
  return comp;
}

function makeWithModule(
  id: string,
  stateOverrides: Partial<ModuleUiState> = {}
): SensibilisationComponent {
  const comp = make();
  (comp as any).uiState.set({ [id]: defaultState(stateOverrides) });
  return comp;
}

describe('SensibilisationComponent — getState()', () => {
  it("retourne l'état par défaut si id inconnu", () => {
    const state = make().getState('unknown');
    expect(state.open).toBe(false);
    expect(state.selected).toBeNull();
    expect(state.quizState).toBe('idle');
    expect(state.result).toBeNull();
    expect(state.submitting).toBe(false);
  });
  it("retourne l'état du module si défini", () => {
    const comp = makeWithModule('mod1', { open: true });
    expect(comp.getState('mod1').open).toBe(true);
  });
});

describe('SensibilisationComponent — toggleModule()', () => {
  it('ouvre un module fermé', () => {
    const comp = makeWithModule('mod1', { open: false });
    comp.toggleModule('mod1');
    expect(comp.getState('mod1').open).toBe(true);
  });
  it('ferme un module ouvert', () => {
    const comp = makeWithModule('mod1', { open: true });
    comp.toggleModule('mod1');
    expect(comp.getState('mod1').open).toBe(false);
  });
  it('ne modifie pas les autres modules', () => {
    const comp = make();
    (comp as any).uiState.set({
      mod1: defaultState({ open: false }),
      mod2: defaultState({ open: true }),
    });
    comp.toggleModule('mod1');
    expect(comp.getState('mod2').open).toBe(true);
  });
});

describe('SensibilisationComponent — selectChoice()', () => {
  it('enregistre le choix sélectionné', () => {
    const comp = makeWithModule('mod1');
    comp.selectChoice('mod1', 'choice_a');
    expect(comp.getState('mod1').selected).toBe('choice_a');
  });
  it('écrase un choix existant', () => {
    const comp = makeWithModule('mod1', { selected: 'choice_a' });
    comp.selectChoice('mod1', 'choice_b');
    expect(comp.getState('mod1').selected).toBe('choice_b');
  });
  it("ne modifie pas l'état si quizState = answered", () => {
    const comp = makeWithModule('mod1', { quizState: 'answered', selected: 'choice_a' });
    comp.selectChoice('mod1', 'choice_b');
    expect(comp.getState('mod1').selected).toBe('choice_a');
  });
});

describe('SensibilisationComponent — resetQuiz()', () => {
  it('remet selected à null', () => {
    const comp = makeWithModule('mod1', { selected: 'choice_a' });
    comp.resetQuiz('mod1');
    expect(comp.getState('mod1').selected).toBeNull();
  });
  it('remet quizState à idle', () => {
    const comp = makeWithModule('mod1', { quizState: 'answered' });
    comp.resetQuiz('mod1');
    expect(comp.getState('mod1').quizState).toBe('idle');
  });
  it('vide le résultat', () => {
    const comp = makeWithModule('mod1', {
      result: { correct: true, explanation: 'OK', correct_answer: 'a' },
    });
    comp.resetQuiz('mod1');
    expect(comp.getState('mod1').result).toBeNull();
  });
  it('ne modifie pas open', () => {
    const comp = makeWithModule('mod1', { open: true, quizState: 'answered' });
    comp.resetQuiz('mod1');
    expect(comp.getState('mod1').open).toBe(true);
  });
});

describe('SensibilisationComponent — colorClass()', () => {
  it('contient red pour red', () => {
    const r = make().colorClass('red');
    expect(r.border).toContain('red');
    expect(r.icon).toContain('red');
    expect(r.badge).toContain('red');
  });
  it('contient blue pour blue', () => {
    const r = make().colorClass('blue');
    expect(r.border).toContain('blue');
  });
  it('contient yellow pour yellow', () => {
    const r = make().colorClass('yellow');
    expect(r.icon).toContain('yellow');
  });
  it('contient orange pour orange', () => {
    const r = make().colorClass('orange');
    expect(r.badge).toContain('orange');
  });
  it('contient green pour green', () => {
    const r = make().colorClass('green');
    expect(r.icon).toContain('green');
  });
  it('fallback sur blue pour couleur inconnue', () => {
    const r = make().colorClass('purple');
    expect(r.border).toContain('blue');
  });
});
