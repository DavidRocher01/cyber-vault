import { describe, it, expect } from 'vitest';
import { signal } from '@angular/core';
import { AwarenessModuleComponent } from './awareness-module.component';
import type { ModuleProgress } from '../cyberscan/services/awareness.service';

function make(): AwarenessModuleComponent {
  const comp = Object.create(AwarenessModuleComponent.prototype) as AwarenessModuleComponent;
  (comp as any).enrollmentId = signal(0);
  (comp as any).dashboard = signal(null);
  (comp as any).currentModuleId = signal(null);
  (comp as any).quizData = signal(null);
  (comp as any).quizResult = signal(null);
  (comp as any).certificate = signal(null);
  (comp as any).view = signal('dashboard');
  (comp as any).loading = signal(false);
  (comp as any).completing = signal(false);
  (comp as any).submittingQuiz = signal(false);
  (comp as any).certLoading = signal(false);
  (comp as any).selectedAnswers = signal({});
  (comp as any).heartbeatInterval = null;
  return comp;
}

describe('AwarenessModuleComponent — moduleIcon()', () => {
  it('check pour completed', () => expect(make().moduleIcon('completed')).toBe('check'));
  it('play_arrow pour in_progress', () =>
    expect(make().moduleIcon('in_progress')).toBe('play_arrow'));
  it('close pour failed', () => expect(make().moduleIcon('failed')).toBe('close'));
  it('lock_outline pour not_started', () =>
    expect(make().moduleIcon('not_started')).toBe('lock_outline'));
  it('circle pour statut inconnu', () => expect(make().moduleIcon('unknown')).toBe('circle'));
});

describe('AwarenessModuleComponent — moduleIconBg()', () => {
  it('contient green pour completed', () =>
    expect(make().moduleIconBg('completed')).toContain('green'));
  it('contient blue pour in_progress', () =>
    expect(make().moduleIconBg('in_progress')).toContain('blue'));
  it('contient red pour failed', () => expect(make().moduleIconBg('failed')).toContain('red'));
  it('contient gray pour not_started', () =>
    expect(make().moduleIconBg('not_started')).toContain('gray'));
});

describe('AwarenessModuleComponent — moduleCardClass()', () => {
  it('contient opacity-60 pour not_started', () =>
    expect(make().moduleCardClass('not_started')).toContain('opacity-60'));
  it('contient blue pour in_progress', () =>
    expect(make().moduleCardClass('in_progress')).toContain('blue'));
  it('contient green pour completed', () =>
    expect(make().moduleCardClass('completed')).toContain('green'));
  it('contient gray par défaut', () => expect(make().moduleCardClass('failed')).toContain('gray'));
});

describe('AwarenessModuleComponent — formatTime()', () => {
  it('affiche les secondes si < 60', () => expect(make().formatTime(45)).toBe('45s'));
  it('affiche 1min pour 60s', () => expect(make().formatTime(60)).toBe('1min'));
  it('affiche 1min pour 90s', () => expect(make().formatTime(90)).toBe('1min'));
  it('affiche 2min pour 120s', () => expect(make().formatTime(120)).toBe('2min'));
  it('affiche 0s pour 0', () => expect(make().formatTime(0)).toBe('0s'));
});

describe('AwarenessModuleComponent — renderMarkdown()', () => {
  it('convertit # en h1', () => expect(make().renderMarkdown('# Titre')).toContain('<h1'));
  it('convertit ## en h2', () => expect(make().renderMarkdown('## Section')).toContain('<h2'));
  it('convertit ### en h3', () =>
    expect(make().renderMarkdown('### Sous-section')).toContain('<h3'));
  it('convertit **bold** en strong', () =>
    expect(make().renderMarkdown('**texte**')).toContain('<strong'));
  it('convertit > en blockquote', () =>
    expect(make().renderMarkdown('> citation')).toContain('blockquote'));
  it('convertit --- en hr', () => expect(make().renderMarkdown('---')).toContain('<hr'));
  it('convertit - item en li', () => expect(make().renderMarkdown('- item')).toContain('<li'));
});

describe('AwarenessModuleComponent — isNextModule()', () => {
  function withDashboard(modules: Partial<ModuleProgress>[]): AwarenessModuleComponent {
    const comp = make();
    (comp as any).dashboard.set({ modules_progress: modules, program: {}, enrollment: {} });
    return comp;
  }

  it('premier module est le prochain si aucun complété', () => {
    const comp = withDashboard([
      {
        module_id: 1,
        position: 1,
        status: 'not_started',
        title: 'A',
        time_spent_seconds: 0,
        best_quiz_score: null,
      },
      {
        module_id: 2,
        position: 2,
        status: 'not_started',
        title: 'B',
        time_spent_seconds: 0,
        best_quiz_score: null,
      },
    ]);
    expect(comp.isNextModule({ module_id: 1, position: 1 } as ModuleProgress)).toBe(true);
    expect(comp.isNextModule({ module_id: 2, position: 2 } as ModuleProgress)).toBe(false);
  });

  it('deuxième module est le prochain si premier complété', () => {
    const comp = withDashboard([
      {
        module_id: 1,
        position: 1,
        status: 'completed',
        title: 'A',
        time_spent_seconds: 0,
        best_quiz_score: null,
      },
      {
        module_id: 2,
        position: 2,
        status: 'not_started',
        title: 'B',
        time_spent_seconds: 0,
        best_quiz_score: null,
      },
    ]);
    expect(comp.isNextModule({ module_id: 2, position: 2 } as ModuleProgress)).toBe(true);
    expect(comp.isNextModule({ module_id: 1, position: 1 } as ModuleProgress)).toBe(false);
  });
});
