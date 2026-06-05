"""Centralised StrEnum definitions for status fields used across models."""

from enum import StrEnum


class ScanStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class CampaignStatus(StrEnum):
    DRAFT = "draft"
    PENDING_VERIFICATION = "pending_verification"
    READY = "ready"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    UNPAID = "unpaid"


class ComplianceStatus(StrEnum):
    COMPLIANT = "compliant"
    PARTIAL = "partial"
    NON_COMPLIANT = "non_compliant"
    NOT_APPLICABLE = "na"


class DossierStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class FindingStatusEnum(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ACCEPTED_RISK = "accepted_risk"


class EnrollmentStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    EXPIRED = "expired"


class ProgressStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class QuoteStatus(StrEnum):
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class CollabStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"


class InvoiceStatus(StrEnum):
    PAID = "paid"
    PENDING = "pending"
    FAILED = "failed"
    REFUNDED = "refunded"
