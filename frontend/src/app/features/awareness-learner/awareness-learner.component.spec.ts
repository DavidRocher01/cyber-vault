import { describe, it, expect } from 'vitest';
import { signal } from '@angular/core';
import { AwarenessLearnerComponent } from './awareness-learner.component';
import type {
  AwarenessEnrollment,
  AwarenessProgram,
  LearnerLevel,
} from '../cyberscan/services/awareness.service';

function make(): AwarenessLearnerComponent {
  const comp = Object.create(AwarenessLearnerComponent.prototype) as AwarenessLearnerComponent;
  (comp as any).programs = signal<AwarenessProgram[]>([]);
  (comp as any).enrollments = signal<AwarenessEnrollment[]>([]);
  (comp as any).level = signal<LearnerLevel | null>(null);
  (comp as any).badges = signal([]);
  (comp as any).loading = signal(false);
  (comp as any).enrolling = signal(null);
  return comp;
}

describe('AwarenessLearnerComponent — enrollStatusLabel()', () => {
  it('Non commencé pour pending', () =>
    expect(make().enrollStatusLabel('pending')).toBe('Non commencé'));
  it('En cours pour in_progress', () =>
    expect(make().enrollStatusLabel('in_progress')).toBe('En cours'));
  it('Complété pour completed', () =>
    expect(make().enrollStatusLabel('completed')).toBe('Complété'));
  it('Échoué pour failed', () => expect(make().enrollStatusLabel('failed')).toBe('Échoué'));
  it('retourne la valeur brute pour statut inconnu', () =>
    expect(make().enrollStatusLabel('other')).toBe('other'));
});

describe('AwarenessLearnerComponent — enrollStatusClass()', () => {
  it('contient cyan pour in_progress', () =>
    expect(make().enrollStatusClass('in_progress')).toContain('cyan'));
  it('contient green pour completed', () =>
    expect(make().enrollStatusClass('completed')).toContain('green'));
  it('contient red pour failed', () => expect(make().enrollStatusClass('failed')).toContain('red'));
  it('contient gray pour pending', () =>
    expect(make().enrollStatusClass('pending')).toContain('gray'));
});

describe('AwarenessLearnerComponent — pctColor()', () => {
  it('text-green-400 si pct >= 80', () => expect(make().pctColor(80)).toBe('text-green-400'));
  it('text-green-400 si pct = 100', () => expect(make().pctColor(100)).toBe('text-green-400'));
  it('text-yellow-400 si pct entre 40 et 79', () =>
    expect(make().pctColor(40)).toBe('text-yellow-400'));
  it('text-yellow-400 si pct = 79', () => expect(make().pctColor(79)).toBe('text-yellow-400'));
  it('text-gray-400 si pct < 40', () => expect(make().pctColor(39)).toBe('text-gray-400'));
  it('text-gray-400 si pct = 0', () => expect(make().pctColor(0)).toBe('text-gray-400'));
});

describe('AwarenessLearnerComponent — pctBarColor()', () => {
  it('bg-green-500 si pct >= 80', () => expect(make().pctBarColor(80)).toBe('bg-green-500'));
  it('bg-cyan-500 si pct entre 40 et 79', () => expect(make().pctBarColor(40)).toBe('bg-cyan-500'));
  it('bg-gray-600 si pct < 40', () => expect(make().pctBarColor(10)).toBe('bg-gray-600'));
});

describe('AwarenessLearnerComponent — programTitle()', () => {
  it('retourne le titre du programme correspondant', () => {
    const comp = make();
    (comp as any).programs.set([
      {
        id: 1,
        title: 'NIS2 Fondamentaux',
        modules: [],
        description: '',
        estimated_duration_minutes: 0,
      },
    ]);
    expect(comp.programTitle(1)).toBe('NIS2 Fondamentaux');
  });

  it('retourne Programme #N si id inconnu', () => {
    expect(make().programTitle(99)).toBe('Programme #99');
  });
});

describe('AwarenessLearnerComponent — availablePrograms()', () => {
  it('exclut les programmes déjà inscrits', () => {
    const comp = make();
    (comp as any).programs.set([
      { id: 1, title: 'A', modules: [], description: '', estimated_duration_minutes: 0 },
      { id: 2, title: 'B', modules: [], description: '', estimated_duration_minutes: 0 },
    ]);
    (comp as any).enrollments.set([
      { id: 10, program_id: 1, status: 'in_progress', completion_pct: 0, xp_earned: 0 },
    ]);
    const available = comp.availablePrograms();
    expect(available).toHaveLength(1);
    expect(available[0].id).toBe(2);
  });

  it('retourne tous les programmes si aucune inscription', () => {
    const comp = make();
    (comp as any).programs.set([
      { id: 1, title: 'A', modules: [], description: '', estimated_duration_minutes: 0 },
      { id: 2, title: 'B', modules: [], description: '', estimated_duration_minutes: 0 },
    ]);
    expect(comp.availablePrograms()).toHaveLength(2);
  });
});

describe('AwarenessLearnerComponent — levelPct()', () => {
  it('retourne 100 si pas de next_level_xp', () => {
    const comp = make();
    (comp as any).level.set({ level: 5, xp: 600, label: 'Expert', next_level_xp: null });
    expect(comp.levelPct()).toBe(100);
  });

  it('retourne 100 si level null', () => {
    expect(make().levelPct()).toBe(100);
  });

  it('calcule correctement pour le niveau 1 (seuil 0→51)', () => {
    const comp = make();
    (comp as any).level.set({ level: 1, xp: 26, label: 'Débutant', next_level_xp: 51 });
    // (26 - 0) / (51 - 0) * 100 ≈ 51
    expect(comp.levelPct()).toBeCloseTo(50.98, 0);
  });

  it('est plafonné à 100', () => {
    const comp = make();
    (comp as any).level.set({ level: 1, xp: 100, label: 'Débutant', next_level_xp: 51 });
    expect(comp.levelPct()).toBe(100);
  });
});
