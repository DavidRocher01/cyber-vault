import { describe, it, expect, vi } from 'vitest';
import { signal } from '@angular/core';
import { of, throwError } from 'rxjs';
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

  it('sans dashboard, seule la position 1 est considérée comme prochaine', () => {
    const comp = make();
    expect(comp.isNextModule({ module_id: 1, position: 1 } as ModuleProgress)).toBe(true);
    expect(comp.isNextModule({ module_id: 2, position: 2 } as ModuleProgress)).toBe(false);
  });
});

describe('AwarenessModuleComponent — formatTime() bornes', () => {
  it('affiche les secondes juste sous la minute (59s)', () =>
    expect(make().formatTime(59)).toBe('59s'));
  it('arrondit vers le bas (119s -> 1min)', () => expect(make().formatTime(119)).toBe('1min'));
  it('gère les grandes durées (3600s -> 60min)', () =>
    expect(make().formatTime(3600)).toBe('60min'));
});

describe('AwarenessModuleComponent — moduleCardClass() défaut', () => {
  it('contient gray pour un statut inconnu', () =>
    expect(make().moduleCardClass('inconnu')).toContain('gray'));
});

describe('AwarenessModuleComponent — moduleIcon()/moduleIconBg() défaut', () => {
  it('moduleIconBg contient gray pour un statut inconnu', () =>
    expect(make().moduleIconBg('inconnu')).toContain('gray'));
});

describe('AwarenessModuleComponent — currentModule()', () => {
  it('retourne undefined si aucun module courant', () => {
    const comp = make();
    (comp as any).dashboard.set({ program: { modules: [{ id: 1 }] } });
    expect(comp.currentModule()).toBeUndefined();
  });

  it('retourne undefined si aucun dashboard', () => {
    const comp = make();
    (comp as any).currentModuleId.set(1);
    expect(comp.currentModule()).toBeUndefined();
  });

  it('retrouve le module par id', () => {
    const comp = make();
    (comp as any).currentModuleId.set(2);
    (comp as any).dashboard.set({
      program: {
        modules: [
          { id: 1, title: 'A' },
          { id: 2, title: 'B' },
        ],
      },
    });
    expect(comp.currentModule()).toEqual({ id: 2, title: 'B' });
  });

  it('retourne undefined si id introuvable', () => {
    const comp = make();
    (comp as any).currentModuleId.set(99);
    (comp as any).dashboard.set({ program: { modules: [{ id: 1 }] } });
    expect(comp.currentModule()).toBeUndefined();
  });
});

describe('AwarenessModuleComponent — selectAnswer() / isSelected()', () => {
  it('choix simple remplace la sélection', () => {
    const comp = make();
    comp.selectAnswer('q1', 'a1', false);
    expect(comp.selectedAnswers()['q1']).toEqual(['a1']);
    comp.selectAnswer('q1', 'a2', false);
    expect(comp.selectedAnswers()['q1']).toEqual(['a2']);
  });

  it('choix multiple ajoute puis retire (toggle)', () => {
    const comp = make();
    comp.selectAnswer('q1', 'a1', true);
    comp.selectAnswer('q1', 'a2', true);
    expect(comp.selectedAnswers()['q1']).toEqual(['a1', 'a2']);
    comp.selectAnswer('q1', 'a1', true);
    expect(comp.selectedAnswers()['q1']).toEqual(['a2']);
  });

  it('isSelected reflète la sélection', () => {
    const comp = make();
    expect(comp.isSelected('q1', 'a1')).toBe(false);
    comp.selectAnswer('q1', 'a1', true);
    expect(comp.isSelected('q1', 'a1')).toBe(true);
    expect(comp.isSelected('q1', 'a2')).toBe(false);
  });

  it('isSelected retourne false pour une question inconnue', () => {
    const comp = make();
    expect(comp.isSelected('qX', 'aX')).toBe(false);
  });
});

describe('AwarenessModuleComponent — loadDashboard()', () => {
  it('stocke le dashboard et coupe le loading (succès)', () => {
    const comp = make();
    (comp as any).loading.set(true);
    const dash = { program: { title: 'P' } };
    (comp as any).svc = { getEnrollmentDashboard: vi.fn().mockReturnValue(of(dash)) };
    comp.loadDashboard();
    expect(comp.dashboard()).toEqual(dash);
    expect(comp.loading()).toBe(false);
  });

  it('redirige vers /awareness en cas d’erreur', () => {
    const comp = make();
    (comp as any).loading.set(true);
    (comp as any).svc = {
      getEnrollmentDashboard: vi.fn().mockReturnValue(throwError(() => new Error('x'))),
    };
    const navigate = vi.fn();
    (comp as any).router = { navigate };
    comp.loadDashboard();
    expect(comp.loading()).toBe(false);
    expect(navigate).toHaveBeenCalledWith(['/awareness']);
  });
});

describe('AwarenessModuleComponent — startQuiz()', () => {
  it('charge le quiz et bascule la vue', () => {
    const comp = make();
    (comp as any).currentModuleId.set(3);
    const quiz = { attempt_number: 1, questions: [] };
    (comp as any).svc = { getQuizQuestions: vi.fn().mockReturnValue(of(quiz)) };
    comp.startQuiz();
    expect(comp.quizData()).toEqual(quiz);
    expect(comp.view()).toBe('quiz');
  });

  it('ne fait rien sans module courant', () => {
    const comp = make();
    const getQuizQuestions = vi.fn();
    (comp as any).svc = { getQuizQuestions };
    comp.startQuiz();
    expect(getQuizQuestions).not.toHaveBeenCalled();
  });

  it('ouvre une snackbar avec le détail en cas d’erreur', () => {
    const comp = make();
    (comp as any).currentModuleId.set(3);
    (comp as any).svc = {
      getQuizQuestions: vi
        .fn()
        .mockReturnValue(throwError(() => ({ error: { detail: 'Trop de tentatives' } }))),
    };
    const open = vi.fn();
    (comp as any).snack = { open };
    comp.startQuiz();
    expect(open).toHaveBeenCalledWith('Trop de tentatives', 'Fermer', { duration: 4000 });
  });
});

describe('AwarenessModuleComponent — submitQuiz()', () => {
  it('réussite: stocke le résultat, recharge le dashboard', () => {
    const comp = make();
    (comp as any).currentModuleId.set(3);
    (comp as any).moduleStartTime = Date.now();
    const result = { result: 'passed', score: 100 };
    const submitQuiz = vi.fn().mockReturnValue(of(result));
    const getEnrollmentDashboard = vi.fn().mockReturnValue(of({ program: {} }));
    (comp as any).svc = { submitQuiz, getEnrollmentDashboard };
    comp.submitQuiz();
    expect(comp.quizResult()).toEqual(result);
    expect(comp.submittingQuiz()).toBe(false);
    expect(comp.view()).toBe('quiz-result');
    expect(getEnrollmentDashboard).toHaveBeenCalled();
  });

  it('échec: stocke le résultat sans recharger le dashboard', () => {
    const comp = make();
    (comp as any).currentModuleId.set(3);
    (comp as any).moduleStartTime = Date.now();
    const result = { result: 'failed', score: 20 };
    const getEnrollmentDashboard = vi.fn();
    (comp as any).svc = {
      submitQuiz: vi.fn().mockReturnValue(of(result)),
      getEnrollmentDashboard,
    };
    comp.submitQuiz();
    expect(comp.quizResult()).toEqual(result);
    expect(comp.view()).toBe('quiz-result');
    expect(getEnrollmentDashboard).not.toHaveBeenCalled();
  });

  it('erreur: coupe le spinner et ouvre une snackbar', () => {
    const comp = make();
    (comp as any).currentModuleId.set(3);
    (comp as any).moduleStartTime = Date.now();
    (comp as any).svc = {
      submitQuiz: vi.fn().mockReturnValue(throwError(() => new Error('x'))),
    };
    const open = vi.fn();
    (comp as any).snack = { open };
    comp.submitQuiz();
    expect(comp.submittingQuiz()).toBe(false);
    expect(open).toHaveBeenCalledWith('Erreur lors de la soumission.', 'Fermer', {
      duration: 4000,
    });
  });
});

describe('AwarenessModuleComponent — completeWithoutQuiz()', () => {
  it('succès: recharge le dashboard, retourne au tableau de bord', () => {
    const comp = make();
    (comp as any).currentModuleId.set(3);
    (comp as any).view.set('content');
    const getEnrollmentDashboard = vi.fn().mockReturnValue(of({ program: {} }));
    (comp as any).svc = {
      completeModule: vi.fn().mockReturnValue(of({})),
      getEnrollmentDashboard,
    };
    const open = vi.fn();
    (comp as any).snack = { open };
    comp.completeWithoutQuiz();
    expect(comp.completing()).toBe(false);
    expect(comp.view()).toBe('dashboard');
    expect(getEnrollmentDashboard).toHaveBeenCalled();
    expect(open).toHaveBeenCalled();
  });

  it('erreur: coupe le spinner et notifie', () => {
    const comp = make();
    (comp as any).currentModuleId.set(3);
    (comp as any).svc = {
      completeModule: vi.fn().mockReturnValue(throwError(() => new Error('x'))),
    };
    const open = vi.fn();
    (comp as any).snack = { open };
    comp.completeWithoutQuiz();
    expect(comp.completing()).toBe(false);
    expect(open).toHaveBeenCalledWith('Erreur.', 'Fermer', { duration: 3000 });
  });
});

describe('AwarenessModuleComponent — loadCertificate()', () => {
  it('succès: stocke le certificat', () => {
    const comp = make();
    (comp as any).certLoading.set(true);
    const cert = { public_id: 'ABC', issued_at: '2026-01-01' };
    (comp as any).svc = { getCertificate: vi.fn().mockReturnValue(of(cert)) };
    comp.loadCertificate();
    expect(comp.certificate()).toEqual(cert);
    expect(comp.certLoading()).toBe(false);
  });

  it('erreur: coupe le loading', () => {
    const comp = make();
    (comp as any).certLoading.set(true);
    (comp as any).svc = {
      getCertificate: vi.fn().mockReturnValue(throwError(() => new Error('x'))),
    };
    comp.loadCertificate();
    expect(comp.certLoading()).toBe(false);
  });
});

describe('AwarenessModuleComponent — certDownloadUrl()', () => {
  it('délègue au service avec l’id d’inscription', () => {
    const comp = make();
    (comp as any).enrollmentId.set(42);
    const certificateDownloadUrl = vi.fn().mockReturnValue('http://x/42.pdf');
    (comp as any).svc = { certificateDownloadUrl };
    expect(comp.certDownloadUrl()).toBe('http://x/42.pdf');
    expect(certificateDownloadUrl).toHaveBeenCalledWith(42);
  });
});

describe('AwarenessModuleComponent — openModule()', () => {
  it('positionne le module courant, la vue et réinitialise l’état', () => {
    const comp = make();
    (comp as any).enrollmentId.set(5);
    (comp as any).quizData.set({ x: 1 });
    (comp as any).quizResult.set({ y: 1 });
    (comp as any).selectedAnswers.set({ q1: ['a1'] });
    (comp as any).svc = { startModule: vi.fn().mockReturnValue(of({})) };
    comp.openModule({ module_id: 7 } as ModuleProgress);
    expect(comp.currentModuleId()).toBe(7);
    expect(comp.view()).toBe('content');
    expect(comp.quizData()).toBeNull();
    expect(comp.quizResult()).toBeNull();
    expect(comp.selectedAnswers()).toEqual({});
    (comp as any).stopHeartbeat();
  });
});

describe('AwarenessModuleComponent — retryQuiz()', () => {
  it('réinitialise les réponses et relance le quiz', () => {
    const comp = make();
    (comp as any).currentModuleId.set(3);
    (comp as any).selectedAnswers.set({ q1: ['a1'] });
    const getQuizQuestions = vi.fn().mockReturnValue(of({ attempt_number: 2, questions: [] }));
    (comp as any).svc = { getQuizQuestions };
    comp.retryQuiz();
    expect(comp.selectedAnswers()).toEqual({});
    expect(getQuizQuestions).toHaveBeenCalled();
    expect(comp.view()).toBe('quiz');
  });
});
