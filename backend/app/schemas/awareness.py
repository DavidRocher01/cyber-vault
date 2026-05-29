from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

# ── Organizations ──────────────────────────────────────────────────────────────


class AwarenessOrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    siret: str | None = Field(None, max_length=20)
    sector: str | None = Field(None, max_length=100)
    max_learners: int = Field(10, ge=1, le=10000)


class AwarenessOrganizationUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    siret: str | None = Field(None, max_length=20)
    sector: str | None = Field(None, max_length=100)
    max_learners: int | None = Field(None, ge=1, le=10000)
    is_active: bool | None = None


class AwarenessOrganizationOut(BaseModel):
    id: int
    owner_user_id: int
    name: str
    siret: str | None
    sector: str | None
    max_learners: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AwarenessOrganizationStats(AwarenessOrganizationOut):
    learner_count: int = 0
    active_enrollments: int = 0
    completion_rate: float = 0.0


# ── Learners ───────────────────────────────────────────────────────────────────


class AwarenessLearnerCreate(BaseModel):
    email: EmailStr
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    department: str | None = Field(None, max_length=100)
    job_title: str | None = Field(None, max_length=150)
    preferred_language: str = Field("fr", max_length=5)


class AwarenessLearnerUpdate(BaseModel):
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    department: str | None = Field(None, max_length=100)
    job_title: str | None = Field(None, max_length=150)
    preferred_language: str | None = Field(None, max_length=5)
    is_active: bool | None = None


class AwarenessLearnerOut(BaseModel):
    id: int
    organization_id: int
    email: str
    first_name: str | None
    last_name: str | None
    department: str | None
    job_title: str | None
    preferred_language: str
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── CSV Import ─────────────────────────────────────────────────────────────────


class CsvImportResult(BaseModel):
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = []


# ── Programs ──────────────────────────────────────────────────────────────────


class AwarenessModuleOut(BaseModel):
    id: int
    slug: str
    title: str
    description: str | None
    position: int
    content_type: str
    estimated_duration_minutes: int
    xp_points: int
    has_quiz: bool
    quiz_passing_score: int
    content_markdown: str | None = None

    model_config = {"from_attributes": True}


class AwarenessProgramOut(BaseModel):
    id: int
    slug: str
    title: str
    description: str | None
    language: str
    estimated_duration_minutes: int
    passing_score: int
    certificate_validity_months: int
    version: str
    modules: list[AwarenessModuleOut] = []

    model_config = {"from_attributes": True}


# ── Enrollments ────────────────────────────────────────────────────────────────


class AwarenessEnrollmentOut(BaseModel):
    id: int
    learner_id: int
    program_id: int
    status: str
    completion_pct: float
    xp_earned: int
    enrolled_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    last_activity_at: datetime | None

    model_config = {"from_attributes": True}


# ── Progression ────────────────────────────────────────────────────────────────


class HeartbeatIn(BaseModel):
    elapsed_seconds: int = Field(30, ge=1, le=300)
    video_position: int | None = Field(None, ge=0)


class CompleteModuleIn(BaseModel):
    quiz_score: int | None = Field(None, ge=0, le=100)


class AwarenessProgressOut(BaseModel):
    id: int
    enrollment_id: int
    module_id: int
    status: str
    time_spent_seconds: int
    video_resume_position: int
    best_quiz_score: int | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


# ── Learner dashboard ──────────────────────────────────────────────────────────


class LearnerModuleProgress(BaseModel):
    module_id: int
    slug: str
    title: str
    position: int
    status: str
    time_spent_seconds: int
    video_resume_position: int
    best_quiz_score: int | None


class LearnerDashboard(BaseModel):
    enrollment: AwarenessEnrollmentOut
    program: AwarenessProgramOut
    modules_progress: list[LearnerModuleProgress]


# ── Quiz ──────────────────────────────────────────────────────────────────────


class QuizAnswerOption(BaseModel):
    id: str
    text: str


class QuizQuestion(BaseModel):
    id: str
    type: str
    weight: int
    text: str
    answers: list[QuizAnswerOption]


class QuizStartOut(BaseModel):
    questions: list[QuizQuestion]
    attempt_number: int
    module_id: int
    enrollment_id: int


class QuizSubmitIn(BaseModel):
    answers: dict[str, list[str]]
    duration_seconds: int = Field(0, ge=0)


class QuizAnswerDetail(BaseModel):
    question_id: str
    chosen_answers: list[str]
    correct_answers: list[str]
    is_correct: bool
    points_earned: int
    explanation: str | None


class QuizResultOut(BaseModel):
    score: int
    result: str
    passing_score: int
    attempt_number: int
    details: list[QuizAnswerDetail]
    enrollment_completion_pct: float | None


# ── Certificates ──────────────────────────────────────────────────────────────


class AwarenessCertificateOut(BaseModel):
    id: int
    public_id: str
    verification_token: str
    issued_at: datetime
    expires_at: datetime | None
    is_revoked: bool
    verification_count: int

    model_config = {"from_attributes": True}


class CertificateVerifyOut(BaseModel):
    valid: bool
    public_id: str
    learner_name: str | None
    program_title: str | None
    issued_at: str
    expires_at: str | None
    verification_count: int


# ── Magic-link auth ────────────────────────────────────────────────────────────


class MagicLinkRequest(BaseModel):
    email: EmailStr
    organization_id: int


class MagicLinkVerify(BaseModel):
    token: str


class LearnerSession(BaseModel):
    learner_id: int
    organization_id: int
    email: str
    first_name: str | None
    last_name: str | None
    access_token: str
