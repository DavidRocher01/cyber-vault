import { Injectable, inject, signal } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, tap } from 'rxjs';

const API = '/api/v1/awareness';
const LEARNER_TOKEN_KEY = 'awareness_learner_token';

// ── Interfaces ──────────────────────────────────────────────────────────────

export interface AwarenessOrganization {
  id: number;
  owner_user_id: number;
  name: string;
  siret: string | null;
  sector: string | null;
  max_learners: number;
  is_active: boolean;
  created_at: string;
  learner_count?: number;
  active_enrollments?: number;
  completion_rate?: number;
}

export interface AwarenessLearner {
  id: number;
  organization_id: number;
  email: string;
  first_name: string | null;
  last_name: string | null;
  department: string | null;
  job_title: string | null;
  preferred_language: string;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface CsvImportResult {
  created: number;
  updated: number;
  skipped: number;
  errors: string[];
}

export interface AwarenessProgram {
  id: number;
  slug: string;
  title: string;
  description: string | null;
  language: string;
  estimated_duration_minutes: number;
  passing_score: number;
  certificate_validity_months: number;
  version: string;
  modules: AwarenessModule[];
}

export interface AwarenessModule {
  id: number;
  slug: string;
  title: string;
  description: string | null;
  position: number;
  content_type: string;
  estimated_duration_minutes: number;
  xp_points: number;
  has_quiz: boolean;
  quiz_passing_score: number;
  content_markdown: string | null;
}

export interface AwarenessEnrollment {
  id: number;
  learner_id: number;
  program_id: number;
  status: string;
  completion_pct: number;
  xp_earned: number;
  enrolled_at: string;
  started_at: string | null;
  completed_at: string | null;
  last_activity_at: string | null;
}

export interface AwarenessProgress {
  id: number;
  enrollment_id: number;
  module_id: number;
  status: string;
  time_spent_seconds: number;
  video_resume_position: number;
  best_quiz_score: number | null;
  completed_at: string | null;
}

export interface ModuleProgress {
  module_id: number;
  slug: string;
  title: string;
  position: number;
  status: string;
  time_spent_seconds: number;
  video_resume_position: number;
  best_quiz_score: number | null;
}

export interface LearnerDashboard {
  enrollment: AwarenessEnrollment;
  program: AwarenessProgram;
  modules_progress: ModuleProgress[];
}

export interface QuizQuestion {
  id: string;
  type: string;
  weight: number;
  text: string;
  answers: { id: string; text: string }[];
}

export interface QuizStart {
  questions: QuizQuestion[];
  attempt_number: number;
  module_id: number;
  enrollment_id: number;
}

export interface QuizResult {
  score: number;
  result: string;
  passing_score: number;
  attempt_number: number;
  details: {
    question_id: string;
    chosen_answers: string[];
    correct_answers: string[];
    is_correct: boolean;
    points_earned: number;
    explanation: string | null;
  }[];
  enrollment_completion_pct: number | null;
}

export interface LearnerSession {
  learner_id: number;
  organization_id: number;
  email: string;
  first_name: string | null;
  last_name: string | null;
  access_token: string;
}

export interface LearnerLevel {
  level: number;
  label: string;
  xp: number;
  next_level_xp: number | null;
}

export interface Badge {
  id: number;
  slug: string;
  name: string;
  icon: string;
  category: string;
  xp_bonus: number;
  description: string | null;
  earned_at: string | null;
}

export interface AwarenessCertificate {
  id: number;
  public_id: string;
  verification_token: string;
  issued_at: string;
  expires_at: string | null;
  is_revoked: boolean;
  verification_count: number;
}

export interface CertificateVerification {
  valid: boolean;
  public_id: string;
  learner_name: string | null;
  program_title: string | null;
  issued_at: string;
  expires_at: string | null;
  verification_count: number;
}

export interface OrgAdminDashboard {
  organization: { id: number; name: string; sector: string | null; max_learners: number };
  engagement: {
    total_learners: number;
    enrolled_learners: number;
    active_learners: number;
    completed_learners: number;
    enrollment_rate: number;
  };
  programs: {
    program_id: number;
    program_title: string;
    total_modules: number;
    enrolled_learners: number;
    completed_learners: number;
    completion_rate: number;
    avg_completion_pct: number;
  }[];
  at_risk_learners: {
    learner_id: number;
    display_name: string;
    department: string | null;
    completion_pct: number;
    last_activity_at: string | null;
    days_inactive: number | null;
  }[];
  certificates_issued: number;
}

export interface Nis2Requirement {
  article: string;
  title: string;
  description: string;
  value: number;
  threshold: number;
  status: string;
  status_label: string;
  color: string;
  gap: number;
}

export interface Nis2Report {
  org_name: string;
  global_score: number;
  requirements: Nis2Requirement[];
  metrics: Record<string, number>;
  certificate_count: number;
}

// ── Service ─────────────────────────────────────────────────────────────────

@Injectable({ providedIn: 'root' })
export class AwarenessService {
  private http = inject(HttpClient);

  readonly learnerSession = signal<LearnerSession | null>(this._loadSession());

  // ── Admin : Organizations ────────────────────────────────────────────────

  listOrganizations(): Observable<AwarenessOrganization[]> {
    return this.http.get<AwarenessOrganization[]>(`${API}/organizations`);
  }

  createOrganization(data: { name: string; max_learners?: number; sector?: string }): Observable<AwarenessOrganization> {
    return this.http.post<AwarenessOrganization>(`${API}/organizations`, data);
  }

  getOrganization(id: number): Observable<AwarenessOrganization> {
    return this.http.get<AwarenessOrganization>(`${API}/organizations/${id}`);
  }

  updateOrganization(id: number, data: Partial<AwarenessOrganization>): Observable<AwarenessOrganization> {
    return this.http.patch<AwarenessOrganization>(`${API}/organizations/${id}`, data);
  }

  // ── Admin : Learners ─────────────────────────────────────────────────────

  listLearners(orgId: number, activeOnly = true): Observable<AwarenessLearner[]> {
    return this.http.get<AwarenessLearner[]>(`${API}/organizations/${orgId}/learners`, {
      params: { active_only: String(activeOnly) },
    });
  }

  createLearner(orgId: number, data: { email: string; first_name?: string; last_name?: string; department?: string }): Observable<AwarenessLearner> {
    return this.http.post<AwarenessLearner>(`${API}/organizations/${orgId}/learners`, data);
  }

  importCsv(orgId: number, file: File): Observable<CsvImportResult> {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<CsvImportResult>(`${API}/organizations/${orgId}/learners/import-csv`, form);
  }

  // ── Admin : Dashboards ───────────────────────────────────────────────────

  orgAdminDashboard(orgId: number): Observable<OrgAdminDashboard> {
    return this.http.get<OrgAdminDashboard>(`${API}/organizations/${orgId}/admin-dashboard`);
  }

  nis2Report(orgId: number): Observable<Nis2Report> {
    return this.http.get<Nis2Report>(`${API}/organizations/${orgId}/nis2-report`);
  }

  nis2ReportPdfUrl(orgId: number): string {
    return `${API}/organizations/${orgId}/nis2-report/pdf`;
  }

  // ── Magic-link auth ───────────────────────────────────────────────────────

  requestMagicLink(email: string, organizationId: number): Observable<{ message: string; token?: string }> {
    return this.http.post<{ message: string; token?: string }>(`${API}/auth/magic-link`, {
      email,
      organization_id: organizationId,
    });
  }

  verifyMagicLink(token: string): Observable<LearnerSession> {
    return this.http.get<LearnerSession>(`${API}/auth/verify`, { params: { token } }).pipe(
      tap(session => this._saveSession(session))
    );
  }

  logout(): void {
    localStorage.removeItem(LEARNER_TOKEN_KEY);
    this.learnerSession.set(null);
  }

  // ── Learner : Programs ────────────────────────────────────────────────────

  listPrograms(): Observable<AwarenessProgram[]> {
    return this.http.get<AwarenessProgram[]>(`${API}/programs`, {
      headers: this._learnerHeaders(),
    });
  }

  // ── Learner : Enrollments ─────────────────────────────────────────────────

  enroll(programId: number): Observable<AwarenessEnrollment> {
    return this.http.post<AwarenessEnrollment>(`${API}/enrollments`, null, {
      params: { program_id: String(programId) },
      headers: this._learnerHeaders(),
    });
  }

  listEnrollments(): Observable<AwarenessEnrollment[]> {
    return this.http.get<AwarenessEnrollment[]>(`${API}/enrollments`, {
      headers: this._learnerHeaders(),
    });
  }

  getEnrollmentDashboard(enrollmentId: number): Observable<LearnerDashboard> {
    return this.http.get<LearnerDashboard>(`${API}/enrollments/${enrollmentId}/dashboard`, {
      headers: this._learnerHeaders(),
    });
  }

  // ── Learner : Progression ─────────────────────────────────────────────────

  startModule(enrollmentId: number, moduleId: number): Observable<AwarenessProgress> {
    return this.http.post<AwarenessProgress>(
      `${API}/enrollments/${enrollmentId}/modules/${moduleId}/start`,
      {},
      { headers: this._learnerHeaders() }
    );
  }

  heartbeat(enrollmentId: number, moduleId: number, elapsedSeconds: number, videoPosition?: number): Observable<AwarenessProgress> {
    return this.http.post<AwarenessProgress>(
      `${API}/enrollments/${enrollmentId}/modules/${moduleId}/heartbeat`,
      { elapsed_seconds: elapsedSeconds, video_position: videoPosition ?? null },
      { headers: this._learnerHeaders() }
    );
  }

  completeModule(enrollmentId: number, moduleId: number, quizScore?: number): Observable<AwarenessEnrollment> {
    return this.http.post<AwarenessEnrollment>(
      `${API}/enrollments/${enrollmentId}/modules/${moduleId}/complete`,
      { quiz_score: quizScore ?? null },
      { headers: this._learnerHeaders() }
    );
  }

  // ── Learner : Quiz ────────────────────────────────────────────────────────

  getQuizQuestions(enrollmentId: number, moduleId: number): Observable<QuizStart> {
    return this.http.get<QuizStart>(
      `${API}/enrollments/${enrollmentId}/modules/${moduleId}/quiz`,
      { headers: this._learnerHeaders() }
    );
  }

  submitQuiz(enrollmentId: number, moduleId: number, answers: Record<string, string[]>, durationSeconds: number): Observable<QuizResult> {
    return this.http.post<QuizResult>(
      `${API}/enrollments/${enrollmentId}/modules/${moduleId}/quiz/submit`,
      { answers, duration_seconds: durationSeconds },
      { headers: this._learnerHeaders() }
    );
  }

  // ── Learner : Gamification ────────────────────────────────────────────────

  getMyLevel(): Observable<LearnerLevel> {
    return this.http.get<LearnerLevel>(`${API}/me/level`, { headers: this._learnerHeaders() });
  }

  getMyBadges(): Observable<Badge[]> {
    return this.http.get<Badge[]>(`${API}/me/badges`, { headers: this._learnerHeaders() });
  }

  // ── Learner : Certificate ─────────────────────────────────────────────────

  getCertificate(enrollmentId: number): Observable<AwarenessCertificate> {
    return this.http.get<AwarenessCertificate>(
      `${API}/enrollments/${enrollmentId}/certificate`,
      { headers: this._learnerHeaders() }
    );
  }

  certificateDownloadUrl(enrollmentId: number): string {
    return `${API}/enrollments/${enrollmentId}/certificate/download`;
  }

  // ── Public : Certificate verification ─────────────────────────────────────

  verifyCertificate(publicId: string, token: string): Observable<CertificateVerification> {
    return this.http.get<CertificateVerification>(`/api/v1/verify-certificate/${publicId}`, {
      params: { token },
    });
  }

  // ── Private helpers ───────────────────────────────────────────────────────

  private _learnerHeaders(): HttpHeaders {
    const session = this.learnerSession();
    if (!session) return new HttpHeaders();
    return new HttpHeaders({ Authorization: `Bearer ${session.access_token}` });
  }

  private _saveSession(session: LearnerSession): void {
    localStorage.setItem(LEARNER_TOKEN_KEY, JSON.stringify(session));
    this.learnerSession.set(session);
  }

  private _loadSession(): LearnerSession | null {
    try {
      const raw = localStorage.getItem(LEARNER_TOKEN_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }
}
