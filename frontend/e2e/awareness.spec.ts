import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

/**
 * E2E — Parcours apprenant du module de sensibilisation NIS2.
 *
 * Le portail apprenant (`/awareness`) n'utilise PAS l'auth classique : il
 * s'appuie sur une session stockée dans localStorage sous la clé
 * `awareness_learner_token` (un objet LearnerSession sérialisé), lue une seule
 * fois à la construction du `AwarenessService` (providedIn: 'root'). On injecte
 * donc cette session via `addInitScript` (exécuté AVANT les scripts de la page),
 * ce qui satisfait `awarenessLearnerGuard` sans passer par le magic-link.
 *
 * Robustesse CI (aucun backend requis) : on STUB tous les GET de l'API
 * `/api/v1/awareness/**` avec des réponses déterministes, et on INTERCEPTE les
 * POST de progression (start / quiz submit) pour vérifier que l'app les émet
 * bien. Le test ne touche jamais un vrai backend.
 */

const LEARNER_SESSION = {
  learner_id: 7,
  organization_id: 3,
  email: 'apprenant.e2e@test.com',
  first_name: 'Alex',
  last_name: 'Durand',
  access_token: 'e2e_fake_learner_token',
};

const ENROLLMENT_ID = 55;
const MODULE_ID = 101;

// Un programme avec deux modules ; le 1er a un quiz.
const PROGRAM = {
  id: 9,
  slug: 'nis2-essentiel',
  title: 'NIS2 — Les fondamentaux',
  description: 'Programme de sensibilisation cybersécurité NIS2.',
  language: 'fr',
  estimated_duration_minutes: 45,
  passing_score: 80,
  certificate_validity_months: 12,
  version: '1.0',
  modules: [
    {
      id: MODULE_ID,
      slug: 'phishing-101',
      title: 'Reconnaître le phishing',
      description: 'Les bases du phishing.',
      position: 1,
      content_type: 'markdown',
      estimated_duration_minutes: 15,
      xp_points: 50,
      has_quiz: true,
      quiz_passing_score: 80,
      content_markdown: '# Phishing\n\nApprenez à **repérer** les emails frauduleux.',
    },
    {
      id: 102,
      slug: 'mots-de-passe',
      title: 'Mots de passe robustes',
      description: 'Gestion des mots de passe.',
      position: 2,
      content_type: 'markdown',
      estimated_duration_minutes: 15,
      xp_points: 50,
      has_quiz: false,
      quiz_passing_score: 80,
      content_markdown: '# Mots de passe\n\nUtilisez un gestionnaire.',
    },
  ],
};

const ENROLLMENT = {
  id: ENROLLMENT_ID,
  learner_id: LEARNER_SESSION.learner_id,
  program_id: PROGRAM.id,
  status: 'in_progress',
  completion_pct: 0,
  xp_earned: 0,
  enrolled_at: '2026-06-01T10:00:00Z',
  started_at: '2026-06-01T10:05:00Z',
  completed_at: null,
  last_activity_at: '2026-06-01T10:05:00Z',
};

const DASHBOARD = {
  enrollment: ENROLLMENT,
  program: PROGRAM,
  modules_progress: [
    {
      module_id: MODULE_ID,
      slug: 'phishing-101',
      title: 'Reconnaître le phishing',
      position: 1,
      status: 'in_progress',
      time_spent_seconds: 0,
      video_resume_position: 0,
      best_quiz_score: null,
    },
    {
      module_id: 102,
      slug: 'mots-de-passe',
      title: 'Mots de passe robustes',
      position: 2,
      status: 'not_started',
      time_spent_seconds: 0,
      video_resume_position: 0,
      best_quiz_score: null,
    },
  ],
};

const QUIZ_START = {
  enrollment_id: ENROLLMENT_ID,
  module_id: MODULE_ID,
  attempt_number: 1,
  questions: [
    {
      id: 'q1',
      type: 'single_choice',
      weight: 1,
      text: 'Un email vous demande votre mot de passe. Que faites-vous ?',
      answers: [
        { id: 'a1', text: 'Je le communique' },
        { id: 'a2', text: 'Je ne réponds pas et je signale' },
      ],
    },
  ],
};

const QUIZ_RESULT_PASSED = {
  score: 100,
  result: 'passed',
  passing_score: 80,
  attempt_number: 1,
  details: [
    {
      question_id: 'q1',
      chosen_answers: ['a2'],
      correct_answers: ['a2'],
      is_correct: true,
      points_earned: 1,
      explanation: 'Ne jamais communiquer son mot de passe.',
    },
  ],
  enrollment_completion_pct: 50,
};

function jsonRoute(body: unknown) {
  return {
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(body),
  };
}

/**
 * Seed la session apprenant dans localStorage avant tout chargement de page,
 * puis installe les stubs GET communs. Les POST sont armés au cas par cas.
 */
async function seedLearnerAndStubGets(page: Page) {
  await page.addInitScript(session => {
    localStorage.setItem('awareness_learner_token', JSON.stringify(session));
    localStorage.setItem('cyberscan_cookie_consent', 'accepted');
  }, LEARNER_SESSION);

  // ── GET stubs (déterministes, indépendants de la DB) ──
  await page.route('**/api/v1/awareness/programs', route =>
    route.fulfill(jsonRoute([PROGRAM]))
  );
  await page.route('**/api/v1/awareness/enrollments', route => {
    // Ne concerne QUE le GET liste ; les POST enrollments passent ailleurs.
    if (route.request().method() === 'GET') {
      return route.fulfill(jsonRoute([ENROLLMENT]));
    }
    return route.fallback();
  });
  await page.route('**/api/v1/awareness/me/level', route =>
    route.fulfill(
      jsonRoute({ level: 2, label: 'Vigilant', xp: 120, next_level_xp: 151 })
    )
  );
  await page.route('**/api/v1/awareness/me/badges', route =>
    route.fulfill(
      jsonRoute([
        {
          id: 1,
          slug: 'first-step',
          name: 'Premier pas',
          icon: '🎯',
          category: 'progress',
          xp_bonus: 10,
          description: null,
          earned_at: '2026-06-01T10:10:00Z',
        },
      ])
    )
  );
  await page.route('**/api/v1/awareness/learner/leaderboard**', route =>
    route.fulfill(
      jsonRoute([
        {
          rank: 1,
          display_name: 'Alex D.',
          total_xp: 120,
          level: 2,
          level_label: 'Vigilant',
        },
      ])
    )
  );
  // Dashboard d'un enrollment donné.
  await page.route(`**/api/v1/awareness/enrollments/${ENROLLMENT_ID}/dashboard`, route =>
    route.fulfill(jsonRoute(DASHBOARD))
  );
  // Questions de quiz (GET).
  await page.route(
    `**/api/v1/awareness/enrollments/${ENROLLMENT_ID}/modules/${MODULE_ID}/quiz`,
    route => {
      if (route.request().method() === 'GET') {
        return route.fulfill(jsonRoute(QUIZ_START));
      }
      return route.fallback();
    }
  );
}

test.describe('Sensibilisation NIS2 — parcours apprenant', () => {
  test.describe.configure({ mode: 'serial' });

  test('accès au portail : liste des programmes et enrollments (GET stubés)', async ({
    page,
  }) => {
    await seedLearnerAndStubGets(page);

    await page.goto('/awareness');

    // Le guard laisse passer (session seedée) : on reste sur /awareness.
    await expect(page).toHaveURL(/\/awareness$/);

    // Le programme en cours doit apparaître (via le dashboard des programmes).
    await expect(page.getByRole('heading', { name: /fondamentaux/i })).toBeVisible({
      timeout: 15_000,
    });
    // Bouton "Continuer" du programme in_progress.
    await expect(
      page.getByRole('link', { name: /Continuer/i }).first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test('consultation d\'un module : ouvre le contenu et ÉMET le POST /start', async ({
    page,
  }) => {
    await seedLearnerAndStubGets(page);

    // Intercepte le POST de démarrage de module (enregistrement de progression).
    let startBody: unknown = null;
    await page.route(
      `**/api/v1/awareness/enrollments/${ENROLLMENT_ID}/modules/${MODULE_ID}/start`,
      async route => {
        startBody = route.request().postDataJSON?.() ?? null;
        await route.fulfill(
          jsonRoute({
            id: 1,
            enrollment_id: ENROLLMENT_ID,
            module_id: MODULE_ID,
            status: 'in_progress',
            time_spent_seconds: 0,
            video_resume_position: 0,
            best_quiz_score: null,
            completed_at: null,
          })
        );
      }
    );

    await page.goto(`/awareness/module/${ENROLLMENT_ID}`);

    // Liste des modules du programme.
    await expect(page.getByRole('heading', { name: /Modules du programme/i })).toBeVisible({
      timeout: 15_000,
    });

    // On arme l'écoute du POST /start AVANT de cliquer sur le module.
    const startReq = page.waitForRequest(
      req =>
        req.method() === 'POST' &&
        new RegExp(`/enrollments/${ENROLLMENT_ID}/modules/${MODULE_ID}/start$`).test(req.url())
    );

    // Le premier module (in_progress) est cliquable → ouvre la vue "content".
    await page.getByRole('button', { name: /Reconnaître le phishing/i }).click();

    const req = await startReq;
    // INVARIANT : la progression est enregistrée pour le bon module.
    expect(req.method()).toBe('POST');
    expect(req.url()).toMatch(
      new RegExp(`/enrollments/${ENROLLMENT_ID}/modules/${MODULE_ID}/start$`)
    );
    expect(startBody === null || typeof startBody === 'object').toBeTruthy();

    // La vue contenu doit s'afficher (bouton "Passer au quizz" car has_quiz=true).
    await expect(page.getByRole('button', { name: /Passer au quizz/i })).toBeVisible({
      timeout: 10_000,
    });
  });

  test('quiz : charge les questions (GET) puis ÉMET le POST /quiz/submit', async ({ page }) => {
    await seedLearnerAndStubGets(page);

    // /start réussit silencieusement.
    await page.route(
      `**/api/v1/awareness/enrollments/${ENROLLMENT_ID}/modules/${MODULE_ID}/start`,
      route =>
        route.fulfill(
          jsonRoute({
            id: 1,
            enrollment_id: ENROLLMENT_ID,
            module_id: MODULE_ID,
            status: 'in_progress',
            time_spent_seconds: 0,
            video_resume_position: 0,
            best_quiz_score: null,
            completed_at: null,
          })
        )
    );

    // Intercepte la soumission du quiz (enregistrement de progression clé).
    let submitBody: any = null;
    await page.route(
      `**/api/v1/awareness/enrollments/${ENROLLMENT_ID}/modules/${MODULE_ID}/quiz/submit`,
      async route => {
        submitBody = route.request().postDataJSON?.() ?? null;
        await route.fulfill(jsonRoute(QUIZ_RESULT_PASSED));
      }
    );

    await page.goto(`/awareness/module/${ENROLLMENT_ID}`);
    await expect(page.getByRole('heading', { name: /Modules du programme/i })).toBeVisible({
      timeout: 15_000,
    });

    // Ouvre le module → contenu.
    await page.getByRole('button', { name: /Reconnaître le phishing/i }).click();
    const startQuizBtn = page.getByRole('button', { name: /Passer au quizz/i });
    await expect(startQuizBtn).toBeVisible({ timeout: 10_000 });

    // Passe au quiz (GET questions stubé).
    await startQuizBtn.click();
    await expect(page.getByText(/Tentative 1/i)).toBeVisible({ timeout: 10_000 });
    await expect(
      page.getByText(/demande votre mot de passe/i)
    ).toBeVisible();

    // Sélectionne la bonne réponse.
    await page.getByRole('button', { name: /Je ne réponds pas et je signale/i }).click();

    // Arme l'écoute du POST submit avant de soumettre.
    const submitReq = page.waitForRequest(
      req =>
        req.method() === 'POST' &&
        new RegExp(
          `/enrollments/${ENROLLMENT_ID}/modules/${MODULE_ID}/quiz/submit$`
        ).test(req.url())
    );

    await page.getByRole('button', { name: /Soumettre le quiz/i }).click();

    const req = await submitReq;
    // INVARIANT : la progression (réponses) est bien envoyée au backend.
    expect(req.method()).toBe('POST');
    expect(submitBody).not.toBeNull();
    expect(submitBody.answers).toBeTruthy();
    expect(submitBody.answers.q1).toEqual(['a2']);
    expect(typeof submitBody.duration_seconds).toBe('number');

    // Résultat "réussi" affiché.
    await expect(page.getByText(/Réussi/i)).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('100%')).toBeVisible();
  });
});
