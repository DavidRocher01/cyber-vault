import { describe, it, expect, vi } from 'vitest';
import { signal } from '@angular/core';
import { of, throwError } from 'rxjs';
import { AwarenessOrgDetailComponent } from './awareness-org-detail.component';
import type { OrgAdminDashboard } from '../services/awareness.service';

function make(): AwarenessOrgDetailComponent {
  const comp = Object.create(AwarenessOrgDetailComponent.prototype) as AwarenessOrgDetailComponent;
  (comp as any).orgId = signal(0);
  (comp as any).org = signal(null);
  (comp as any).learners = signal([]);
  (comp as any).dashboard = signal(null);
  (comp as any).nis2 = signal(null);
  (comp as any).csvResult = signal(null);
  (comp as any).loading = signal(false);
  (comp as any).loadingDash = signal(false);
  (comp as any).loadingNis2 = signal(false);
  (comp as any).addingLearner = signal(false);
  (comp as any).importingCsv = signal(false);
  (comp as any).enrollingAll = signal(false);
  (comp as any).emailError = signal(false);
  (comp as any).activeTab = signal('learners');
  (comp as any).Math = Math;
  return comp;
}

describe('AwarenessOrgDetailComponent — completionColor()', () => {
  it('text-green-400 si taux >= 80', () =>
    expect(make().completionColor(80)).toBe('text-green-400'));
  it('text-yellow-400 si taux entre 50 et 79', () =>
    expect(make().completionColor(50)).toBe('text-yellow-400'));
  it('text-red-400 si taux < 50', () => expect(make().completionColor(0)).toBe('text-red-400'));
});

describe('AwarenessOrgDetailComponent — completionBarColor()', () => {
  it('bg-green-500 si taux >= 80', () =>
    expect(make().completionBarColor(80)).toBe('bg-green-500'));
  it('bg-yellow-500 si taux entre 50 et 79', () =>
    expect(make().completionBarColor(60)).toBe('bg-yellow-500'));
  it('bg-red-500 si taux < 50', () => expect(make().completionBarColor(10)).toBe('bg-red-500'));
});

describe('AwarenessOrgDetailComponent — nis2ScoreColor()', () => {
  it('text-green-400 si score >= 80', () =>
    expect(make().nis2ScoreColor(80)).toBe('text-green-400'));
  it('text-yellow-400 si score entre 50 et 79', () =>
    expect(make().nis2ScoreColor(50)).toBe('text-yellow-400'));
  it('text-red-400 si score < 50', () => expect(make().nis2ScoreColor(49)).toBe('text-red-400'));
});

describe('AwarenessOrgDetailComponent — nis2GaugeColor()', () => {
  it('vert (#4ade80) si score >= 80', () => expect(make().nis2GaugeColor(90)).toBe('#4ade80'));
  it('jaune (#facc15) si score entre 50 et 79', () =>
    expect(make().nis2GaugeColor(60)).toBe('#facc15'));
  it('rouge (#f87171) si score < 50', () => expect(make().nis2GaugeColor(20)).toBe('#f87171'));
});

describe('AwarenessOrgDetailComponent — nis2StatusClass()', () => {
  it('contient green pour green', () => expect(make().nis2StatusClass('green')).toContain('green'));
  it('contient yellow pour yellow', () =>
    expect(make().nis2StatusClass('yellow')).toContain('yellow'));
  it('contient red pour red', () => expect(make().nis2StatusClass('red')).toContain('red'));
});

describe('AwarenessOrgDetailComponent — nis2BarColor()', () => {
  it('bg-green-500 pour green', () => expect(make().nis2BarColor('green')).toBe('bg-green-500'));
  it('bg-yellow-500 pour yellow', () =>
    expect(make().nis2BarColor('yellow')).toBe('bg-yellow-500'));
  it('bg-red-500 pour red', () => expect(make().nis2BarColor('red')).toBe('bg-red-500'));
});

describe('AwarenessOrgDetailComponent — funnelStats()', () => {
  it('retourne 4 statistiques avec les bonnes valeurs', () => {
    const comp = make();
    const engagement = {
      total_learners: 20,
      enrolled_learners: 15,
      active_learners: 10,
      completed_learners: 5,
    };
    (comp as any).dashboard.set({
      engagement,
      programs: [],
      at_risk_learners: [],
    } as unknown as OrgAdminDashboard);
    const stats = comp.funnelStats();
    expect(stats).toHaveLength(4);
    expect(stats[0].value).toBe(20);
    expect(stats[1].value).toBe(15);
    expect(stats[2].value).toBe(10);
    expect(stats[3].value).toBe(5);
  });

  it('associe les bonnes couleurs aux étapes', () => {
    const comp = make();
    (comp as any).dashboard.set({
      engagement: {
        total_learners: 1,
        enrolled_learners: 1,
        active_learners: 1,
        completed_learners: 1,
      },
      programs: [],
      at_risk_learners: [],
    } as unknown as OrgAdminDashboard);
    const stats = comp.funnelStats();
    expect(stats[0].color).toBe('text-white');
    expect(stats[1].color).toContain('blue');
    expect(stats[2].color).toContain('yellow');
    expect(stats[3].color).toContain('green');
  });
});

describe('AwarenessOrgDetailComponent — bornes des couleurs', () => {
  it('completionColor : 79 reste jaune (borne haute)', () =>
    expect(make().completionColor(79)).toBe('text-yellow-400'));
  it('completionColor : 49 passe au rouge (borne basse)', () =>
    expect(make().completionColor(49)).toBe('text-red-400'));
  it('completionBarColor : 50 est jaune (borne basse)', () =>
    expect(make().completionBarColor(50)).toBe('bg-yellow-500'));
  it('nis2GaugeColor : 80 est vert (borne)', () =>
    expect(make().nis2GaugeColor(80)).toBe('#4ade80'));
  it('nis2StatusClass : couleur inconnue -> rouge par défaut', () =>
    expect(make().nis2StatusClass('bleu')).toContain('red'));
  it('nis2BarColor : couleur inconnue -> rouge par défaut', () =>
    expect(make().nis2BarColor('bleu')).toBe('bg-red-500'));
});

describe('AwarenessOrgDetailComponent — pdfUrl()', () => {
  it("délègue au service avec l'orgId courant", () => {
    const comp = make();
    (comp as any).orgId = signal(42);
    (comp as any).svc = { nis2ReportPdfUrl: vi.fn().mockReturnValue('http://pdf/42') };
    expect(comp.pdfUrl()).toBe('http://pdf/42');
    expect((comp as any).svc.nis2ReportPdfUrl).toHaveBeenCalledWith(42);
  });
});

describe('AwarenessOrgDetailComponent — loadLearners()', () => {
  it('stocke la liste des learners renvoyée', () => {
    const comp = make();
    (comp as any).orgId = signal(3);
    const list = [{ id: 1, email: 'a@b.c' }];
    (comp as any).svc = { listLearners: vi.fn().mockReturnValue(of(list)) };
    comp.loadLearners();
    expect((comp as any).svc.listLearners).toHaveBeenCalledWith(3);
    expect(comp.learners()).toEqual(list);
  });
});

describe('AwarenessOrgDetailComponent — loadDash()', () => {
  it('stocke le dashboard et lève le flag de chargement', () => {
    const comp = make();
    (comp as any).orgId = signal(3);
    const dash = { engagement: {}, programs: [], at_risk_learners: [] };
    (comp as any).svc = { orgAdminDashboard: vi.fn().mockReturnValue(of(dash)) };
    comp.loadDash();
    expect(comp.dashboard()).toEqual(dash);
    expect(comp.loadingDash()).toBe(false);
  });

  it('remet loadingDash à false en cas d’erreur', () => {
    const comp = make();
    (comp as any).orgId = signal(3);
    (comp as any).svc = {
      orgAdminDashboard: vi.fn().mockReturnValue(throwError(() => new Error('boom'))),
    };
    comp.loadDash();
    expect(comp.loadingDash()).toBe(false);
    expect(comp.dashboard()).toBeNull();
  });
});

describe('AwarenessOrgDetailComponent — loadNis2()', () => {
  it('stocke le rapport et lève le flag de chargement', () => {
    const comp = make();
    (comp as any).orgId = signal(3);
    const report = { global_score: 90, requirements: [] };
    (comp as any).svc = { nis2Report: vi.fn().mockReturnValue(of(report)) };
    comp.loadNis2();
    expect(comp.nis2()).toEqual(report);
    expect(comp.loadingNis2()).toBe(false);
  });

  it('remet loadingNis2 à false en cas d’erreur', () => {
    const comp = make();
    (comp as any).orgId = signal(3);
    (comp as any).svc = {
      nis2Report: vi.fn().mockReturnValue(throwError(() => new Error('boom'))),
    };
    comp.loadNis2();
    expect(comp.loadingNis2()).toBe(false);
    expect(comp.nis2()).toBeNull();
  });
});

describe('AwarenessOrgDetailComponent — addLearner()', () => {
  it('email vide -> emailError et aucun appel service', () => {
    const comp = make();
    (comp as any).orgId = signal(1);
    (comp as any).newEmail = '   ';
    const svc = { createLearner: vi.fn() };
    (comp as any).svc = svc;
    comp.addLearner();
    expect(comp.emailError()).toBe(true);
    expect(svc.createLearner).not.toHaveBeenCalled();
  });

  it('succès -> ajoute le learner, réinitialise les champs et notifie', () => {
    const comp = make();
    (comp as any).orgId = signal(7);
    (comp as any).newEmail = 'alice@x.com';
    (comp as any).newFirstName = 'Alice';
    (comp as any).newDept = 'IT';
    const created = { id: 9, email: 'alice@x.com' };
    (comp as any).svc = { createLearner: vi.fn().mockReturnValue(of(created)) };
    (comp as any).snack = { open: vi.fn() };
    comp.addLearner();
    expect((comp as any).svc.createLearner).toHaveBeenCalledWith(7, {
      email: 'alice@x.com',
      first_name: 'Alice',
      department: 'IT',
    });
    expect(comp.learners()).toContainEqual(created);
    expect((comp as any).newEmail).toBe('');
    expect((comp as any).newFirstName).toBe('');
    expect((comp as any).newDept).toBe('');
    expect(comp.addingLearner()).toBe(false);
    expect((comp as any).snack.open).toHaveBeenCalled();
  });

  it('prénom et département vides -> envoyés comme undefined', () => {
    const comp = make();
    (comp as any).orgId = signal(2);
    (comp as any).newEmail = 'bob@x.com';
    (comp as any).newFirstName = '  ';
    (comp as any).newDept = '';
    (comp as any).svc = {
      createLearner: vi.fn().mockReturnValue(of({ id: 1, email: 'bob@x.com' })),
    };
    (comp as any).snack = { open: vi.fn() };
    comp.addLearner();
    expect((comp as any).svc.createLearner).toHaveBeenCalledWith(2, {
      email: 'bob@x.com',
      first_name: undefined,
      department: undefined,
    });
  });

  it('erreur -> remet le flag et affiche le message', () => {
    const comp = make();
    (comp as any).orgId = signal(1);
    (comp as any).newEmail = 'x@y.z';
    (comp as any).newFirstName = '';
    (comp as any).newDept = '';
    (comp as any).svc = {
      createLearner: vi
        .fn()
        .mockReturnValue(throwError(() => ({ error: { detail: 'déjà pris' } }))),
    };
    (comp as any).snack = { open: vi.fn() };
    comp.addLearner();
    expect(comp.addingLearner()).toBe(false);
    expect((comp as any).snack.open).toHaveBeenCalledWith('déjà pris', 'Fermer', {
      duration: 4000,
    });
  });
});

describe('AwarenessOrgDetailComponent — onCsvSelected()', () => {
  it('affecte le fichier sélectionné et réinitialise le résultat', () => {
    const comp = make();
    (comp as any).csvResult.set({ created: 1, updated: 0, skipped: 0 });
    const file = { name: 'x.csv' } as File;
    const event = { target: { files: [file] } } as unknown as Event;
    comp.onCsvSelected(event);
    expect((comp as any).csvFile).toBe(file);
    expect(comp.csvResult()).toBeNull();
  });

  it('aucun fichier -> csvFile à null', () => {
    const comp = make();
    const event = { target: { files: null } } as unknown as Event;
    comp.onCsvSelected(event);
    expect((comp as any).csvFile).toBeNull();
  });
});

describe('AwarenessOrgDetailComponent — uploadCsv()', () => {
  it('sans fichier -> ne fait rien', () => {
    const comp = make();
    (comp as any).csvFile = null;
    const svc = { importCsv: vi.fn() };
    (comp as any).svc = svc;
    comp.uploadCsv();
    expect(svc.importCsv).not.toHaveBeenCalled();
  });

  it('succès -> stocke le résultat, recharge et notifie', () => {
    const comp = make();
    (comp as any).orgId = signal(5);
    (comp as any).csvFile = { name: 'x.csv' } as File;
    const result = { created: 3, updated: 2, skipped: 1 };
    (comp as any).svc = {
      importCsv: vi.fn().mockReturnValue(of(result)),
      listLearners: vi.fn().mockReturnValue(of([])),
    };
    (comp as any).snack = { open: vi.fn() };
    comp.uploadCsv();
    expect(comp.csvResult()).toEqual(result);
    expect(comp.importingCsv()).toBe(false);
    expect((comp as any).svc.listLearners).toHaveBeenCalledWith(5);
    expect((comp as any).snack.open).toHaveBeenCalled();
  });

  it('erreur -> remet le flag et notifie', () => {
    const comp = make();
    (comp as any).orgId = signal(5);
    (comp as any).csvFile = { name: 'x.csv' } as File;
    (comp as any).svc = {
      importCsv: vi.fn().mockReturnValue(throwError(() => new Error('boom'))),
    };
    (comp as any).snack = { open: vi.fn() };
    comp.uploadCsv();
    expect(comp.importingCsv()).toBe(false);
    expect((comp as any).snack.open).toHaveBeenCalledWith('Erreur import.', 'Fermer', {
      duration: 4000,
    });
  });
});

describe('AwarenessOrgDetailComponent — enrollAll()', () => {
  it('sans programme sélectionné -> ne fait rien', () => {
    const comp = make();
    (comp as any).selectedProgramId = null;
    const svc = { enrollAll: vi.fn() };
    (comp as any).svc = svc;
    comp.enrollAll();
    expect(svc.enrollAll).not.toHaveBeenCalled();
  });

  it('succès -> notifie et réinitialise la sélection', () => {
    const comp = make();
    (comp as any).orgId = signal(8);
    (comp as any).selectedProgramId = 4;
    (comp as any).enrollingAll = signal(false);
    (comp as any).svc = {
      enrollAll: vi.fn().mockReturnValue(of({ enrolled: 3, skipped: 1 })),
    };
    (comp as any).snack = { open: vi.fn() };
    comp.enrollAll();
    expect((comp as any).svc.enrollAll).toHaveBeenCalledWith(8, 4);
    expect(comp.enrollingAll()).toBe(false);
    expect((comp as any).selectedProgramId).toBeNull();
    expect((comp as any).snack.open).toHaveBeenCalled();
  });

  it('erreur -> remet le flag et notifie', () => {
    const comp = make();
    (comp as any).orgId = signal(8);
    (comp as any).selectedProgramId = 4;
    (comp as any).enrollingAll = signal(false);
    (comp as any).svc = {
      enrollAll: vi.fn().mockReturnValue(throwError(() => new Error('boom'))),
    };
    (comp as any).snack = { open: vi.fn() };
    comp.enrollAll();
    expect(comp.enrollingAll()).toBe(false);
    expect((comp as any).snack.open).toHaveBeenCalledWith(
      "Erreur lors de l'inscription.",
      'Fermer',
      {
        duration: 4000,
      }
    );
  });
});

describe('AwarenessOrgDetailComponent — sendMagicLink()', () => {
  it('succès -> notifie avec l’email', () => {
    const comp = make();
    (comp as any).orgId = signal(6);
    (comp as any).svc = { requestMagicLink: vi.fn().mockReturnValue(of({})) };
    (comp as any).snack = { open: vi.fn() };
    comp.sendMagicLink({ email: 'z@z.z' } as any);
    expect((comp as any).svc.requestMagicLink).toHaveBeenCalledWith('z@z.z', 6);
    expect((comp as any).snack.open).toHaveBeenCalledWith('Lien envoyé à z@z.z', 'OK', {
      duration: 3000,
    });
  });

  it('erreur -> notifie l’échec', () => {
    const comp = make();
    (comp as any).orgId = signal(6);
    (comp as any).svc = {
      requestMagicLink: vi.fn().mockReturnValue(throwError(() => new Error('boom'))),
    };
    (comp as any).snack = { open: vi.fn() };
    comp.sendMagicLink({ email: 'z@z.z' } as any);
    expect((comp as any).snack.open).toHaveBeenCalledWith('Erreur envoi lien.', 'Fermer', {
      duration: 3000,
    });
  });
});
