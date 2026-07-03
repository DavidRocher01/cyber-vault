import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { of, throwError } from 'rxjs';
import { signal } from '@angular/core';
import { HttpHeaders } from '@angular/common/http';
import { AwarenessService, LearnerSession } from './awareness.service';

const API = '/api/v1/awareness';
const LEARNER_TOKEN_KEY = 'awareness_learner_token';

function makeSession(overrides: Partial<LearnerSession> = {}): LearnerSession {
  return {
    learner_id: 1,
    organization_id: 2,
    email: 'jane@acme.fr',
    first_name: 'Jane',
    last_name: 'Doe',
    access_token: 'tok-123',
    ...overrides,
  };
}

function makeService(
  httpOverrides: Partial<{ get: any; post: any; patch: any; delete: any }> = {},
  session: LearnerSession | null = null
) {
  const http = {
    get: vi.fn().mockReturnValue(of({})),
    post: vi.fn().mockReturnValue(of({})),
    patch: vi.fn().mockReturnValue(of({})),
    delete: vi.fn().mockReturnValue(of(undefined)),
    ...httpOverrides,
  };
  const service = Object.create(AwarenessService.prototype) as AwarenessService;
  (service as any).http = http;
  (service as any).learnerSession = signal<LearnerSession | null>(session);
  return { service, http };
}

// Helper: extract the headers option passed to a mocked http call.
function headerFromCall(call: any[]): HttpHeaders {
  const opts = call[call.length - 1];
  return opts.headers as HttpHeaders;
}

// ── Admin : Organizations ─────────────────────────────────────────────────────

describe('AwarenessService — listOrganizations()', () => {
  it('appelle GET /organizations', () => {
    const { service, http } = makeService();
    service.listOrganizations().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/organizations`);
  });

  it('propage la réponse mappée', () => {
    const orgs = [{ id: 1, name: 'Acme' }];
    const { service } = makeService({ get: vi.fn().mockReturnValue(of(orgs)) });
    let result: any;
    service.listOrganizations().subscribe(r => (result = r));
    expect(result).toBe(orgs);
  });
});

describe('AwarenessService — createOrganization()', () => {
  it('appelle POST /organizations avec le body', () => {
    const { service, http } = makeService();
    const data = { name: 'Acme', max_learners: 50, sector: 'IT' };
    service.createOrganization(data).subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/organizations`, data);
  });
});

describe('AwarenessService — getOrganization()', () => {
  it('appelle GET /organizations/:id', () => {
    const { service, http } = makeService();
    service.getOrganization(42).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/organizations/42`);
  });
});

describe('AwarenessService — updateOrganization()', () => {
  it('appelle PATCH /organizations/:id avec le body', () => {
    const { service, http } = makeService();
    service.updateOrganization(5, { name: 'New' }).subscribe();
    expect(http.patch).toHaveBeenCalledWith(`${API}/organizations/5`, { name: 'New' });
  });
});

// ── Admin : Learners ──────────────────────────────────────────────────────────

describe('AwarenessService — listLearners()', () => {
  it('appelle GET avec active_only=true par défaut', () => {
    const { service, http } = makeService();
    service.listLearners(7).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/organizations/7/learners`, {
      params: { active_only: 'true' },
    });
  });

  it('appelle GET avec active_only=false', () => {
    const { service, http } = makeService();
    service.listLearners(7, false).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/organizations/7/learners`, {
      params: { active_only: 'false' },
    });
  });
});

describe('AwarenessService — createLearner()', () => {
  it('appelle POST /organizations/:id/learners avec le body', () => {
    const { service, http } = makeService();
    const data = { email: 'a@b.fr', first_name: 'A' };
    service.createLearner(7, data).subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/organizations/7/learners`, data);
  });
});

describe('AwarenessService — importCsv()', () => {
  it('appelle POST /import-csv avec un FormData contenant le fichier', () => {
    const { service, http } = makeService();
    const file = new File(['email\nx@y.fr'], 'learners.csv', { type: 'text/csv' });
    service.importCsv(9, file).subscribe();
    expect(http.post).toHaveBeenCalledWith(
      `${API}/organizations/9/learners/import-csv`,
      expect.any(FormData)
    );
    const form = http.post.mock.calls[0][1] as FormData;
    expect(form.get('file')).toBe(file);
  });
});

// ── Admin : Dashboards ────────────────────────────────────────────────────────

describe('AwarenessService — orgAdminDashboard()', () => {
  it('appelle GET /organizations/:id/admin-dashboard', () => {
    const { service, http } = makeService();
    service.orgAdminDashboard(3).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/organizations/3/admin-dashboard`);
  });
});

describe('AwarenessService — nis2Report()', () => {
  it('appelle GET /organizations/:id/nis2-report', () => {
    const { service, http } = makeService();
    service.nis2Report(3).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/organizations/3/nis2-report`);
  });
});

describe('AwarenessService — nis2ReportPdfUrl()', () => {
  it("retourne l'URL du PDF", () => {
    const { service } = makeService();
    expect(service.nis2ReportPdfUrl(3)).toBe(`${API}/organizations/3/nis2-report/pdf`);
  });
});

// ── Magic-link auth ───────────────────────────────────────────────────────────

describe('AwarenessService — requestMagicLink()', () => {
  it('appelle POST /auth/magic-link avec email + organization_id', () => {
    const { service, http } = makeService();
    service.requestMagicLink('u@acme.fr', 12).subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/auth/magic-link`, {
      email: 'u@acme.fr',
      organization_id: 12,
    });
  });
});

describe('AwarenessService — verifyMagicLink()', () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => localStorage.clear());

  it('appelle GET /auth/verify avec le token en param', () => {
    const { service, http } = makeService({ get: vi.fn().mockReturnValue(of(makeSession())) });
    service.verifyMagicLink('magic-tok').subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/auth/verify`, { params: { token: 'magic-tok' } });
  });

  it('persiste la session dans localStorage et le signal', () => {
    const session = makeSession({ access_token: 'saved-tok' });
    const { service } = makeService({ get: vi.fn().mockReturnValue(of(session)) });
    service.verifyMagicLink('magic-tok').subscribe();
    expect(JSON.parse(localStorage.getItem(LEARNER_TOKEN_KEY)!)).toEqual(session);
    expect(service.learnerSession()).toEqual(session);
  });
});

describe('AwarenessService — logout()', () => {
  it('supprime le token et réinitialise le signal', () => {
    localStorage.setItem(LEARNER_TOKEN_KEY, JSON.stringify(makeSession()));
    const { service } = makeService({}, makeSession());
    service.logout();
    expect(localStorage.getItem(LEARNER_TOKEN_KEY)).toBeNull();
    expect(service.learnerSession()).toBeNull();
  });
});

// ── Learner : Programs ────────────────────────────────────────────────────────

describe('AwarenessService — listPrograms()', () => {
  it('appelle GET /programs avec les headers learner', () => {
    const { service, http } = makeService({}, makeSession({ access_token: 'abc' }));
    service.listPrograms().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/programs`, { headers: expect.any(HttpHeaders) });
    const headers = headerFromCall(http.get.mock.calls[0]);
    expect(headers.get('Authorization')).toBe('Bearer abc');
  });

  it('envoie des headers vides sans session', () => {
    const { service, http } = makeService({}, null);
    service.listPrograms().subscribe();
    const headers = headerFromCall(http.get.mock.calls[0]);
    expect(headers.get('Authorization')).toBeNull();
  });
});

// ── Learner : Enrollments ─────────────────────────────────────────────────────

describe('AwarenessService — enroll()', () => {
  it('appelle POST /enrollments avec program_id en param + headers', () => {
    const { service, http } = makeService({}, makeSession());
    service.enroll(15).subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/enrollments`, null, {
      params: { program_id: '15' },
      headers: expect.any(HttpHeaders),
    });
  });
});

describe('AwarenessService — listEnrollments()', () => {
  it('appelle GET /enrollments avec headers', () => {
    const { service, http } = makeService({}, makeSession());
    service.listEnrollments().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/enrollments`, {
      headers: expect.any(HttpHeaders),
    });
  });
});

describe('AwarenessService — getEnrollmentDashboard()', () => {
  it('appelle GET /enrollments/:id/dashboard', () => {
    const { service, http } = makeService({}, makeSession());
    service.getEnrollmentDashboard(20).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/enrollments/20/dashboard`, {
      headers: expect.any(HttpHeaders),
    });
  });
});

// ── Learner : Progression ─────────────────────────────────────────────────────

describe('AwarenessService — startModule()', () => {
  it('appelle POST /enrollments/:id/modules/:mid/start', () => {
    const { service, http } = makeService({}, makeSession());
    service.startModule(20, 4).subscribe();
    expect(http.post).toHaveBeenCalledWith(
      `${API}/enrollments/20/modules/4/start`,
      {},
      { headers: expect.any(HttpHeaders) }
    );
  });
});

describe('AwarenessService — heartbeat()', () => {
  it('envoie elapsed_seconds + video_position', () => {
    const { service, http } = makeService({}, makeSession());
    service.heartbeat(20, 4, 30, 12).subscribe();
    expect(http.post).toHaveBeenCalledWith(
      `${API}/enrollments/20/modules/4/heartbeat`,
      { elapsed_seconds: 30, video_position: 12 },
      { headers: expect.any(HttpHeaders) }
    );
  });

  it('envoie video_position=null si absent', () => {
    const { service, http } = makeService({}, makeSession());
    service.heartbeat(20, 4, 30).subscribe();
    expect(http.post).toHaveBeenCalledWith(
      `${API}/enrollments/20/modules/4/heartbeat`,
      { elapsed_seconds: 30, video_position: null },
      { headers: expect.any(HttpHeaders) }
    );
  });
});

describe('AwarenessService — completeModule()', () => {
  it('envoie quiz_score', () => {
    const { service, http } = makeService({}, makeSession());
    service.completeModule(20, 4, 85).subscribe();
    expect(http.post).toHaveBeenCalledWith(
      `${API}/enrollments/20/modules/4/complete`,
      { quiz_score: 85 },
      { headers: expect.any(HttpHeaders) }
    );
  });

  it('envoie quiz_score=null si absent', () => {
    const { service, http } = makeService({}, makeSession());
    service.completeModule(20, 4).subscribe();
    expect(http.post).toHaveBeenCalledWith(
      `${API}/enrollments/20/modules/4/complete`,
      { quiz_score: null },
      { headers: expect.any(HttpHeaders) }
    );
  });
});

// ── Learner : Quiz ────────────────────────────────────────────────────────────

describe('AwarenessService — getQuizQuestions()', () => {
  it('appelle GET /enrollments/:id/modules/:mid/quiz', () => {
    const { service, http } = makeService({}, makeSession());
    service.getQuizQuestions(20, 4).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/enrollments/20/modules/4/quiz`, {
      headers: expect.any(HttpHeaders),
    });
  });
});

describe('AwarenessService — submitQuiz()', () => {
  it('envoie answers + duration_seconds', () => {
    const { service, http } = makeService({}, makeSession());
    const answers = { q1: ['a'], q2: ['b', 'c'] };
    service.submitQuiz(20, 4, answers, 90).subscribe();
    expect(http.post).toHaveBeenCalledWith(
      `${API}/enrollments/20/modules/4/quiz/submit`,
      { answers, duration_seconds: 90 },
      { headers: expect.any(HttpHeaders) }
    );
  });
});

// ── Learner : Gamification ────────────────────────────────────────────────────

describe('AwarenessService — getMyLevel()', () => {
  it('appelle GET /me/level avec headers', () => {
    const { service, http } = makeService({}, makeSession());
    service.getMyLevel().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/me/level`, {
      headers: expect.any(HttpHeaders),
    });
  });
});

describe('AwarenessService — getMyBadges()', () => {
  it('appelle GET /me/badges avec headers', () => {
    const { service, http } = makeService({}, makeSession());
    service.getMyBadges().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/me/badges`, {
      headers: expect.any(HttpHeaders),
    });
  });
});

describe('AwarenessService — listAdminPrograms()', () => {
  it('appelle GET /admin/programs', () => {
    const { service, http } = makeService();
    service.listAdminPrograms().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/admin/programs`);
  });
});

describe('AwarenessService — enrollAll()', () => {
  it('appelle POST /organizations/:id/enroll-all?program_id=', () => {
    const { service, http } = makeService();
    service.enrollAll(7, 15).subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/organizations/7/enroll-all?program_id=15`, {});
  });
});

describe('AwarenessService — getLeaderboard()', () => {
  it('appelle GET /learner/leaderboard?limit=10 par défaut', () => {
    const { service, http } = makeService({}, makeSession());
    service.getLeaderboard().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/learner/leaderboard?limit=10`, {
      headers: expect.any(HttpHeaders),
    });
  });

  it('appelle GET avec un limit personnalisé', () => {
    const { service, http } = makeService({}, makeSession());
    service.getLeaderboard(25).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/learner/leaderboard?limit=25`, {
      headers: expect.any(HttpHeaders),
    });
  });
});

// ── Learner : Certificate ─────────────────────────────────────────────────────

describe('AwarenessService — getCertificate()', () => {
  it('appelle GET /enrollments/:id/certificate', () => {
    const { service, http } = makeService({}, makeSession());
    service.getCertificate(20).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/enrollments/20/certificate`, {
      headers: expect.any(HttpHeaders),
    });
  });
});

describe('AwarenessService — certificateDownloadUrl()', () => {
  it("retourne l'URL de téléchargement", () => {
    const { service } = makeService();
    expect(service.certificateDownloadUrl(20)).toBe(`${API}/enrollments/20/certificate/download`);
  });
});

// ── Public : Certificate verification ─────────────────────────────────────────

describe('AwarenessService — verifyCertificate()', () => {
  it('appelle GET /verify-certificate/:publicId avec token en param', () => {
    const { service, http } = makeService();
    service.verifyCertificate('pub-abc', 'ver-tok').subscribe();
    expect(http.get).toHaveBeenCalledWith('/api/v1/verify-certificate/pub-abc', {
      params: { token: 'ver-tok' },
    });
  });
});

// ── Gestion d'erreur ──────────────────────────────────────────────────────────

describe('AwarenessService — gestion d’erreur HTTP', () => {
  it('propage une erreur du GET', () => {
    const err = new Error('boom');
    const { service } = makeService({ get: vi.fn().mockReturnValue(throwError(() => err)) });
    let caught: any;
    service.listOrganizations().subscribe({ error: e => (caught = e) });
    expect(caught).toBe(err);
  });

  it('propage une erreur du POST', () => {
    const err = new Error('bad request');
    const { service } = makeService({ post: vi.fn().mockReturnValue(throwError(() => err)) });
    let caught: any;
    service.createOrganization({ name: 'X' }).subscribe({ error: e => (caught = e) });
    expect(caught).toBe(err);
  });
});

// ── _loadSession (au chargement) ──────────────────────────────────────────────

describe('AwarenessService — chargement de session initiale', () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => localStorage.clear());

  it('retourne null si localStorage est vide', () => {
    const service = Object.create(AwarenessService.prototype) as AwarenessService;
    expect((service as any)._loadSession()).toBeNull();
  });

  it('parse une session valide depuis localStorage', () => {
    const session = makeSession();
    localStorage.setItem(LEARNER_TOKEN_KEY, JSON.stringify(session));
    const service = Object.create(AwarenessService.prototype) as AwarenessService;
    expect((service as any)._loadSession()).toEqual(session);
  });

  it('retourne null pour un JSON corrompu', () => {
    localStorage.setItem(LEARNER_TOKEN_KEY, '{not-json');
    const service = Object.create(AwarenessService.prototype) as AwarenessService;
    expect((service as any)._loadSession()).toBeNull();
  });
});
