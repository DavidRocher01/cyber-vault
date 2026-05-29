"""add_awareness_module_tables

Revision ID: 087da233d9f0
Revises: phish_merge_2026
Create Date: 2026-05-29 07:26:51.314382

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "087da233d9f0"
down_revision: str | None = "phish_merge_2026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "awareness_badges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(length=50), nullable=False),
        sa.Column("xp_bonus", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_awareness_badges_id"), "awareness_badges", ["id"], unique=False)
    op.create_index(op.f("ix_awareness_badges_slug"), "awareness_badges", ["slug"], unique=True)

    op.create_table(
        "awareness_programs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=5), nullable=False),
        sa.Column("estimated_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("passing_score", sa.Integer(), nullable=False),
        sa.Column("certificate_validity_months", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("version", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_awareness_programs_id"), "awareness_programs", ["id"], unique=False)
    op.create_index(op.f("ix_awareness_programs_slug"), "awareness_programs", ["slug"], unique=True)

    op.create_table(
        "awareness_modules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("program_id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=20), nullable=False),
        sa.Column("video_url", sa.String(length=500), nullable=True),
        sa.Column("slides_url", sa.String(length=500), nullable=True),
        sa.Column("content_markdown", sa.Text(), nullable=True),
        sa.Column("estimated_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("xp_points", sa.Integer(), nullable=False),
        sa.Column("has_quiz", sa.Boolean(), nullable=False),
        sa.Column("quiz_yaml", sa.Text(), nullable=True),
        sa.Column("quiz_max_attempts", sa.Integer(), nullable=False),
        sa.Column("quiz_cooldown_minutes", sa.Integer(), nullable=False),
        sa.Column("quiz_passing_score", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["program_id"], ["awareness_programs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_awareness_modules_id"), "awareness_modules", ["id"], unique=False)
    op.create_index(
        op.f("ix_awareness_modules_program_id"), "awareness_modules", ["program_id"], unique=False
    )
    op.create_index(op.f("ix_awareness_modules_slug"), "awareness_modules", ["slug"], unique=False)

    op.create_table(
        "awareness_organizations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("siret", sa.String(length=20), nullable=True),
        sa.Column("sector", sa.String(length=100), nullable=True),
        sa.Column("max_learners", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_awareness_organizations_id"), "awareness_organizations", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_awareness_organizations_owner_user_id"),
        "awareness_organizations",
        ["owner_user_id"],
        unique=False,
    )

    op.create_table(
        "awareness_learners",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("department", sa.String(length=100), nullable=True),
        sa.Column("job_title", sa.String(length=150), nullable=True),
        sa.Column("preferred_language", sa.String(length=5), nullable=False),
        sa.Column("access_token_hash", sa.String(length=128), nullable=True),
        sa.Column("access_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("anonymized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["awareness_organizations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_awareness_learners_email"), "awareness_learners", ["email"], unique=False
    )
    op.create_index(op.f("ix_awareness_learners_id"), "awareness_learners", ["id"], unique=False)
    op.create_index(
        op.f("ix_awareness_learners_organization_id"),
        "awareness_learners",
        ["organization_id"],
        unique=False,
    )

    op.create_table(
        "awareness_enrollments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("learner_id", sa.Integer(), nullable=False),
        sa.Column("program_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("completion_pct", sa.Float(), nullable=False),
        sa.Column("xp_earned", sa.Integer(), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["learner_id"], ["awareness_learners.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["awareness_organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["program_id"], ["awareness_programs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_awareness_enrollments_id"), "awareness_enrollments", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_awareness_enrollments_learner_id"),
        "awareness_enrollments",
        ["learner_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_awareness_enrollments_organization_id"),
        "awareness_enrollments",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_awareness_enrollments_program_id"),
        "awareness_enrollments",
        ["program_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_awareness_enrollments_status"), "awareness_enrollments", ["status"], unique=False
    )

    op.create_table(
        "awareness_learner_badges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("learner_id", sa.Integer(), nullable=False),
        sa.Column("badge_id", sa.Integer(), nullable=False),
        sa.Column("earned_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["badge_id"], ["awareness_badges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["learner_id"], ["awareness_learners.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("learner_id", "badge_id", name="uq_learner_badge"),
    )
    op.create_index(
        op.f("ix_awareness_learner_badges_badge_id"),
        "awareness_learner_badges",
        ["badge_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_awareness_learner_badges_id"), "awareness_learner_badges", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_awareness_learner_badges_learner_id"),
        "awareness_learner_badges",
        ["learner_id"],
        unique=False,
    )

    op.create_table(
        "awareness_quiz_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("learner_id", sa.Integer(), nullable=False),
        sa.Column("module_id", sa.Integer(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("result", sa.String(length=10), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("answers_json", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["learner_id"], ["awareness_learners.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["module_id"], ["awareness_modules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_awareness_quiz_attempts_id"), "awareness_quiz_attempts", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_awareness_quiz_attempts_learner_id"),
        "awareness_quiz_attempts",
        ["learner_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_awareness_quiz_attempts_module_id"),
        "awareness_quiz_attempts",
        ["module_id"],
        unique=False,
    )

    op.create_table(
        "awareness_certificates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enrollment_id", sa.Integer(), nullable=False),
        sa.Column("learner_id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=30), nullable=False),
        sa.Column("verification_token", sa.String(length=64), nullable=False),
        sa.Column("signature_hash", sa.String(length=64), nullable=False),
        sa.Column("frozen_data_json", sa.Text(), nullable=False),
        sa.Column("pdf_s3_key", sa.String(length=500), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_revoked", sa.Boolean(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revocation_reason", sa.String(length=255), nullable=True),
        sa.Column("verification_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["enrollment_id"], ["awareness_enrollments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["learner_id"], ["awareness_learners.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("verification_token"),
    )
    op.create_index(
        op.f("ix_awareness_certificates_enrollment_id"),
        "awareness_certificates",
        ["enrollment_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_awareness_certificates_id"), "awareness_certificates", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_awareness_certificates_learner_id"),
        "awareness_certificates",
        ["learner_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_awareness_certificates_public_id"),
        "awareness_certificates",
        ["public_id"],
        unique=True,
    )

    op.create_table(
        "awareness_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enrollment_id", sa.Integer(), nullable=False),
        sa.Column("module_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("time_spent_seconds", sa.Integer(), nullable=False),
        sa.Column("video_resume_position", sa.Integer(), nullable=False),
        sa.Column("best_quiz_score", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["enrollment_id"], ["awareness_enrollments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["module_id"], ["awareness_modules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_awareness_progress_enrollment_id"),
        "awareness_progress",
        ["enrollment_id"],
        unique=False,
    )
    op.create_index(op.f("ix_awareness_progress_id"), "awareness_progress", ["id"], unique=False)
    op.create_index(
        op.f("ix_awareness_progress_module_id"), "awareness_progress", ["module_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_awareness_progress_module_id"), table_name="awareness_progress")
    op.drop_index(op.f("ix_awareness_progress_id"), table_name="awareness_progress")
    op.drop_index(op.f("ix_awareness_progress_enrollment_id"), table_name="awareness_progress")
    op.drop_table("awareness_progress")

    op.drop_index(op.f("ix_awareness_certificates_public_id"), table_name="awareness_certificates")
    op.drop_index(op.f("ix_awareness_certificates_learner_id"), table_name="awareness_certificates")
    op.drop_index(op.f("ix_awareness_certificates_id"), table_name="awareness_certificates")
    op.drop_index(
        op.f("ix_awareness_certificates_enrollment_id"), table_name="awareness_certificates"
    )
    op.drop_table("awareness_certificates")

    op.drop_index(
        op.f("ix_awareness_quiz_attempts_module_id"), table_name="awareness_quiz_attempts"
    )
    op.drop_index(
        op.f("ix_awareness_quiz_attempts_learner_id"), table_name="awareness_quiz_attempts"
    )
    op.drop_index(op.f("ix_awareness_quiz_attempts_id"), table_name="awareness_quiz_attempts")
    op.drop_table("awareness_quiz_attempts")

    op.drop_index(
        op.f("ix_awareness_learner_badges_learner_id"), table_name="awareness_learner_badges"
    )
    op.drop_index(op.f("ix_awareness_learner_badges_id"), table_name="awareness_learner_badges")
    op.drop_index(
        op.f("ix_awareness_learner_badges_badge_id"), table_name="awareness_learner_badges"
    )
    op.drop_table("awareness_learner_badges")

    op.drop_index(op.f("ix_awareness_enrollments_status"), table_name="awareness_enrollments")
    op.drop_index(op.f("ix_awareness_enrollments_program_id"), table_name="awareness_enrollments")
    op.drop_index(
        op.f("ix_awareness_enrollments_organization_id"), table_name="awareness_enrollments"
    )
    op.drop_index(op.f("ix_awareness_enrollments_learner_id"), table_name="awareness_enrollments")
    op.drop_index(op.f("ix_awareness_enrollments_id"), table_name="awareness_enrollments")
    op.drop_table("awareness_enrollments")

    op.drop_index(op.f("ix_awareness_learners_organization_id"), table_name="awareness_learners")
    op.drop_index(op.f("ix_awareness_learners_id"), table_name="awareness_learners")
    op.drop_index(op.f("ix_awareness_learners_email"), table_name="awareness_learners")
    op.drop_table("awareness_learners")

    op.drop_index(
        op.f("ix_awareness_organizations_owner_user_id"), table_name="awareness_organizations"
    )
    op.drop_index(op.f("ix_awareness_organizations_id"), table_name="awareness_organizations")
    op.drop_table("awareness_organizations")

    op.drop_index(op.f("ix_awareness_modules_slug"), table_name="awareness_modules")
    op.drop_index(op.f("ix_awareness_modules_program_id"), table_name="awareness_modules")
    op.drop_index(op.f("ix_awareness_modules_id"), table_name="awareness_modules")
    op.drop_table("awareness_modules")

    op.drop_index(op.f("ix_awareness_programs_slug"), table_name="awareness_programs")
    op.drop_index(op.f("ix_awareness_programs_id"), table_name="awareness_programs")
    op.drop_table("awareness_programs")

    op.drop_index(op.f("ix_awareness_badges_slug"), table_name="awareness_badges")
    op.drop_index(op.f("ix_awareness_badges_id"), table_name="awareness_badges")
    op.drop_table("awareness_badges")
